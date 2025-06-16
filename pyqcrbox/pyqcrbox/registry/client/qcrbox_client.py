import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

from faststream.nats import NatsBroker
from litestar import Litestar

from pyqcrbox import helpers, logger, msg_specs, settings, sql_models
from pyqcrbox.cli.helpers import get_repo_root
from pyqcrbox.debug import eel_logging
from pyqcrbox.helpers import generate_private_routing_key
from pyqcrbox.registry.client.executable_command.base_calculation import BaseCalculation
from pyqcrbox.registry.shared.calculation_status import update_calculation_status_in_nats_kv
from pyqcrbox.services import get_data_file_manager
from pyqcrbox.sql_models import CalculationStatusDetails, CalculationStatusEnum
from pyqcrbox.sql_models.interactive_session_info import InteractiveSessionInfo
from pyqcrbox.sql_models.parameter_spec.base_parameter_spec import parse_parameter_as_its_dtype

from ..shared import QCrBoxServerClientBase, TestQCrBoxServerClientBase, on_qcrbox_startup
from .api_endpoints import create_client_asgi_server
from .client_status import ClientStatus, ClientStatusEnum
from .executable_command import BaseCommand, ExecutableCommand

# from .message_processing.command_invocation_request import handle_command_invocation_request_via_nats

__all__ = ["QCrBoxClient", "TestQCrBoxClient"]


class QCrBoxClient(QCrBoxServerClientBase):
    def __init__(
        self,
        *,
        application_spec: sql_models.ApplicationSpec,
        client_id: str = "anonymous_client",
        private_routing_key: Optional[str] = None,
        work_root_dir: Optional[Path] = None,
        nats_broker: Optional[NatsBroker] = None,
        asgi_server: Optional[Litestar] = None,
    ):
        super().__init__(nats_broker=nats_broker, asgi_server=asgi_server)
        self.application_spec = application_spec
        self.client_id = client_id
        self.private_routing_key = private_routing_key or generate_private_routing_key()
        self.work_root_dir = work_root_dir or self._create_work_root_dir()
        self._calculations: list[BaseCommand] = []
        self.status = ClientStatus(client_id, ClientStatusEnum.IDLE)

    def _create_work_root_dir(self):
        return TemporaryDirectory(prefix=f"work_root_{self.client_id}_")

    @property
    def working_dir(self) -> Path:
        return self.application_spec.yaml_file_dir or Path.cwd()

    @eel_logging
    def _set_up_nats_broker(self) -> None:
        slug_sanitized = helpers.sanitize_for_nats_subject(self.application_spec.slug)
        version_sanitized = helpers.sanitize_for_nats_subject(self.application_spec.version)
        self.nats_broker.subscriber(f"client.cmd.handle_invocation_request.{slug_sanitized}.{version_sanitized}")(
            self.handle_command_invocation_request_from_server
        )
        self.nats_broker.subscriber(f"{self.private_inbox}.cmd.discard")(self.handle_discard_command_invocation)
        self.nats_broker.subscriber(f"{self.private_inbox}.cmd.execute")(self.handle_command_execution)
        self.nats_broker.subscriber(f"{self.private_inbox}.calc.status")(self.get_calculation_status)
        self.nats_broker.subscriber(f"{self.private_inbox}.interactive_session.close")(self.close_interactive_session)

    @eel_logging
    async def handle_command_invocation_request_from_server(self, msg: msg_specs.CommandInvocationRequestNATS):
        logger.info(f"Received command invocation request: {msg!r} (current client status: TODO)")

        response_msg = msg_specs.CommandInvocationClientResponseNATS(
            application_slug=msg.application_slug,
            application_version=msg.application_version,
            client_id=self.client_id,
            client_is_available=self.status.is_available,
            calculation_id=msg.calculation_id,
            private_inbox_prefix=self.private_inbox,
        )

        if self.status.is_available:
            self.status.set_pending()

        return response_msg

    @eel_logging
    async def handle_discard_command_invocation(self, msg: msg_specs.DiscardCommandInvocationNATS):
        logger.info(f"Received request to discard command invocation: {msg!r} (current status: {self.status.status})")
        status_details = CalculationStatusDetails(
            calculation_id=msg.calculation_id,
            status=CalculationStatusEnum.FAILED,
            stdout=None,
            stderr=None,
            extra_info={
                "error_msg": f"Discarded calculation {msg.calculation_id!r} due to client status {self.status.status}",
            },
        )
        await update_calculation_status_in_nats_kv(status_details)

    @eel_logging
    async def handle_command_execution(self, msg: msg_specs.CommandExecutionRequestNATS):
        logger.info(f"Received command execution request: {msg!r} (current status: {self.status.status})")
        self.status.set_busy()

        await self._store_interactive_session(msg)

        try:
            cmd = self.get_executable_command(msg.command_name)
            logger.debug(f"InteractiveSession: Retrieved command {cmd.cmd_spec!r} ")

            # Parse each argument in `msg.arguments` as the correct parameter type
            # Steps:
            #   - get the command spec and look up parameter types for each argument
            #   - parse each argument as the correct type
            parsed_args = {}
            for param_name, value in msg.arguments.items():
                param_dtype_str = cmd.cmd_spec.get_parameter_by_name(param_name).dtype
                parsed_args[param_name] = parse_parameter_as_its_dtype(value, param_dtype_str)

            calc = await cmd.execute_in_background(
                **parsed_args, _calculation_id=msg.calculation_id, _cwd=self.working_dir
            )
            if not isinstance(calc, BaseCalculation):
                raise RuntimeError("Command execution did not return a calculation object.")
            logger.debug("Calculation executing in the background")
        except Exception as exc:
            error_msg = f"Command execution failed: {exc!r}"
            logger.error(error_msg)
            status_details = CalculationStatusDetails(
                calculation_id=msg.calculation_id,
                status=CalculationStatusEnum.FAILED,
                stdout=None,
                stderr=None,
                extra_info={"error_msg": error_msg},
            )
            await update_calculation_status_in_nats_kv(status_details)
            self.status.set_idle()
            return

        self.calculations[msg.calculation_id] = calc
        logger.debug(f"Added calculation id={msg.calculation_id!r} to client calculations")
        await update_calculation_status_in_nats_kv(await calc.get_status_details())

        await calc.wait_until_finished()
        await update_calculation_status_in_nats_kv(await calc.get_status_details())

    @eel_logging
    async def close_interactive_session(
        self, msg: msg_specs.CloseInteractiveSessionNATS
    ) -> msg_specs.CloseInteractiveSessionResponseNATS | None:
        logger.info(f"Received request to close interactive session: {msg!r}")

        session_id = msg.session_id

        if session_id not in self.calculations:
            logger.error(f"No calculation on client found for id={session_id!r}")
            logger.debug(f"Calculations in client: {self.calculations.keys()}")
            response = msg_specs.CloseInteractiveSessionResponseNATS(
                session_id=session_id,
                status=CalculationStatusEnum.FAILED,
                output_dataset_id=None,
            )
            return response

        calc = self.calculations[session_id]

        try:
            await calc.close_interactive_session()
            session_status = calc.status
            output_dataset_id = calc.output_dataset_id
            logger.debug(f"Closed interactive session: id={session_id!r} dataset_id={output_dataset_id!r}")
            self.status.set_idle()
        except AttributeError:
            logger.error(f"Calculation {session_id!r} is not an interactive session")
            session_status = CalculationStatusEnum.FAILED
            output_dataset_id = None

        return msg_specs.CloseInteractiveSessionResponseNATS(
            session_id=session_id,
            status=session_status,
            output_dataset_id=output_dataset_id,
        )

    @eel_logging
    async def get_calculation_status(
        self, msg: msg_specs.GetCalculationStatusNATS
    ) -> msg_specs.CalculationStatusResponseNATS:
        logger.debug(f"Retrieving calculation details for calculation_id={msg.calculation_id!r}")
        status = self.calculations[msg.calculation_id].status
        logger.debug(f"Current calculation status: {status!r}")
        response = msg_specs.CalculationStatusResponseNATS(
            calculation_id=msg.calculation_id,
            status=status,
        )
        return response

    @eel_logging
    def get_executable_command(self, command_name):
        command_spec = self.application_spec.get_command_spec_by_name(command_name)
        return ExecutableCommand(command_spec)

    @eel_logging
    def _set_up_asgi_server(self) -> None:
        self.asgi_server = create_client_asgi_server(self.lifespan_context)

    @eel_logging
    async def _run_custom_shutdown_tasks(self):
        logger.debug("Terminating running calculations...")
        logger.warning("TODO: actually terminate any running calculations...")
        for calc in self._calculations:
            await calc.terminate()

    @eel_logging
    async def _store_interactive_session(self, msg: msg_specs.CommandExecutionRequestNATS):
        if msg.command_name != "interactive_session":
            return
        interactive_session_info = InteractiveSessionInfo(
            session_id=msg.calculation_id,
            client_private_inbox=self.private_inbox,
            cmd_execution_request=msg,
        )
        data_manager = await get_data_file_manager()
        await data_manager.store_interactive_session_info(interactive_session_info)
        logger.debug(
            f"Added interactive session to NATS key-value store: session_id={interactive_session_info.session_id!r}"
            + f" calculation_id={msg.calculation_id}"
        )

    @on_qcrbox_startup
    @eel_logging
    async def send_registration_request_via_nats(self):
        logger.debug("Sending registration request to QCrBox server")
        msg = msg_specs.RegisterApplication(
            action="register_application",
            payload=msg_specs.PayloadForRegisterApplication(
                application_spec=self.application_spec,
                private_routing_key=self.private_routing_key,
            ),
        )

        try:
            resp = await self.nats_broker.publish(
                msg, "register-application", rpc=True, rpc_timeout=settings.nats.rpc_timeout, raise_timeout=True
            )
            logger.debug(f"Received response to registration request: {resp=}")
        except TimeoutError:
            logger.error("Application registration failed (no response from server)")
            self.shutdown()


class TestQCrBoxClient(TestQCrBoxServerClientBase, QCrBoxClient):
    pass


@eel_logging
def main():
    repo_root = get_repo_root(__file__)

    try:
        application_config_file = Path(sys.argv[1])
    except IndexError:
        application_config_file = repo_root.joinpath("services/applications/olex2_linux/config_olex2.yaml")

    application_spec = sql_models.ApplicationSpec.from_yaml_file(application_config_file)

    # Add the directory containing the application config file to PATH so that any scripts
    # present there are available during command execution.
    os.environ["PATH"] = f"{application_config_file.parent.absolute()}:{os.environ['PATH']}"

    qcrbox_client = QCrBoxClient(application_spec=application_spec)
    qcrbox_client.run(host=settings.registry.client.host, port=settings.registry.client.port)


if __name__ == "__main__":
    main()

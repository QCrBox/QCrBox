import argparse
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from faststream.nats import NatsBroker
from litestar import Litestar

from pyqcrbox import helpers, logger, msg_specs, settings, sql_models
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
        private_routing_key: str | None = None,
        work_root_dir: Path | None = None,
        nats_broker: NatsBroker | None = None,
        asgi_server: Litestar | None = None,
    ):
        super().__init__(nats_broker=nats_broker, asgi_server=asgi_server)
        self.application_spec = application_spec
        self.client_id = client_id
        self.private_routing_key = private_routing_key or generate_private_routing_key()
        self.work_root_dir = work_root_dir or self._create_work_root_dir()
        self._calculations: list[BaseCommand] = []
        self.status = ClientStatus(client_id, ClientStatusEnum.IDLE)

    def _create_work_root_dir(self) -> None:
        """Create a directory for storing temporary work files."""
        return TemporaryDirectory(prefix=f"work_root_{self.client_id}_")

    @property
    def working_dir(self) -> Path:
        """Get the working directory for the application client.

        Returns
        -------
        Path
            The working directory, either determined dynamically or from the
            application specification.

        """
        return self.application_spec.yaml_file_dir or Path.cwd()

    def _set_up_nats_broker(self) -> None:
        """Initialise NATS inbox handlers."""
        slug_sanitized = helpers.sanitize_for_nats_subject(self.application_spec.slug)
        version_sanitized = helpers.sanitize_for_nats_subject(self.application_spec.version)
        self.nats_broker.subscriber(f"client.cmd.handle_invocation_request.{slug_sanitized}.{version_sanitized}")(
            self.handle_command_invocation_request_from_server
        )
        self.nats_broker.subscriber(f"{self.private_inbox}.cmd.discard")(self.handle_discard_command_invocation)
        self.nats_broker.subscriber(f"{self.private_inbox}.cmd.execute")(self.handle_command_execution)
        self.nats_broker.subscriber(f"{self.private_inbox}.calc.status")(self.get_calculation_status)
        self.nats_broker.subscriber(f"{self.private_inbox}.interactive_session.close")(self.close_interactive_session)

    async def handle_command_invocation_request_from_server(
        self, msg: msg_specs.CommandInvocationRequestNATS
    ) -> msg_specs.CommandInvocationClientResponseNATS:
        """Handle user command invocation requests.

        Parameters
        ----------
        msg : msg_specs.CommandInvocationRequestsNATS
            A NATS message containing data about the command a user has requested
            to execute.

        Returns
        -------
        msg_specs.CommandInvocationClientResponseNATS
            A response message containing data about if the client and if it can
            execute the request or not.

        """
        logger.info(
            f"Received command invocation request (client status: {self.status.status}): {msg!r}",
        )
        response_msg = msg_specs.CommandInvocationClientResponseNATS(
            application_slug=msg.application_slug,
            application_version=msg.application_version,
            client_id=self.client_id,
            client_is_available=self.status.is_available,
            calculation_id=msg.calculation_id,
            private_inbox_prefix=self.private_inbox,
        )
        if self.status.is_available:
            logger.info("Client is free, able to accept new command request")
            self.status.set_pending()
        else:
            logger.info("Client is busy, unable to accept new command request")

        return response_msg

    async def handle_discard_command_invocation(self, msg: msg_specs.DiscardCommandInvocationNATS) -> None:
        """Handle discard command invocation requests.

        This handler is called when a command invocation is discarded in cases such
        as when the client is not available to execute the requested command.

        Parameters
        ----------
        msg : msg_specs.DiscardCommandInvocationNATS
            A NATS message containing the discard requests.

        """
        logger.info(
            f"Received request to discard command invocation (client status: {self.status.status}): {msg!r}",
        )
        status_details = CalculationStatusDetails(
            calculation_id=msg.calculation_id,
            status=CalculationStatusEnum.FAILED,
            stdout="",
            stderr="",
            extra_info={
                "error_msg": f"Discarded calculation {msg.calculation_id!r} due to client status {self.status.status}",
            },
        )
        await update_calculation_status_in_nats_kv(status_details)

    async def handle_command_execution(self, msg: msg_specs.CommandExecutionRequestNATS) -> None:
        """Handle command execution requests.

        Commands are executed in the background, returning immediately a Calculation
        object. This handler does not return until the entire the entire calculation
        has finished: prepare, run and finalise.

        Parameters
        ----------
        msg : msg_specs.CommandExecutionRequestNATS
            A NATS message containing data about the command to be executed.

        """
        logger.info(f"Received command execution request: {msg!r} (current status: {self.status.status})")

        if self.status.status != ClientStatusEnum.PENDING:
            logger.error(
                f"Trying to execute a command when client is not PENDING. Current status: {self.status.status}"
            )
            return
        self.status.set_busy()

        await self.add_interactive_session_to_database(msg)

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
            logger.debug(f"Executing calculation in the background: {cmd!r}")
            calc = await cmd.execute_in_background(
                **parsed_args, _calculation_id=msg.calculation_id, _cwd=self.working_dir
            )
            if not isinstance(calc, BaseCalculation):
                raise RuntimeError("Command execution did not return a calculation object.")
            logger.debug(f"Executing command has returned calculation: {calc!r}")
        except Exception as exc:
            error_msg = f"Command execution has failed: {exc!r}"
            logger.error(error_msg)
            status_details = CalculationStatusDetails(
                calculation_id=msg.calculation_id,
                status=CalculationStatusEnum.FAILED,
                stdout="",
                stderr="",
                extra_info={"error_msg": error_msg},
            )
            await update_calculation_status_in_nats_kv(status_details)
            self.status.set_idle()  # Should we set it back to idle? There could be a zombie process
            return

        # Keep track of the calculation, which should still be running
        self.calculations[msg.calculation_id] = calc
        await update_calculation_status_in_nats_kv(await calc.get_status_details())

        # Wait until its finished and when finished, updated the details
        await calc.wait_until_finished()
        await update_calculation_status_in_nats_kv(await calc.get_status_details())

    async def close_interactive_session(
        self, msg: msg_specs.CloseInteractiveSessionNATS
    ) -> msg_specs.CloseInteractiveSessionResponseNATS:
        """Close an interactive session.

        Terminates any running calculations and closes the session. If the interactive
        session terminated successfully, the client is marked as either. Otherwise
        the client stays in its original status. If an interactive session can't
        be closed, then something is probably not working so we should not be re-using
        the container for new command requests.

        Parameters
        ----------
        msg : msg_specs.CloseInteractiveSessionNATS
            A NATS message containing data of the session to close.

        Returns
        -------
        msg_specs.CloseInteractiveSessionNATS
            A NATS response containing the status and dataset ID for any output.

        """
        logger.info(f"Received request to close interactive session: {msg!r}")

        session_id = msg.session_id

        if session_id not in self.calculations:
            logger.error(f"No calculations on client found for {session_id!r}")
            logger.debug(f"Calculations in client: {self.calculations.keys()}")
            response = msg_specs.CloseInteractiveSessionResponseNATS(
                session_id=session_id,
                status=CalculationStatusEnum.FAILED,
                output_dataset_id=None,
            )
            return response

        calc = self.calculations[session_id]
        try:
            await calc.terminate()
            self.status.set_idle()  # Set status to idle so container can be re-used
        except AttributeError:
            logger.error(f"Calculation {session_id!r} is not an interactive session")
            response = msg_specs.CloseInteractiveSessionNATS(
                session_id=session_id, status=CalculationStatusEnum.FAILED, output_dataset_id=None
            )
            return response

        msg = msg_specs.CloseInteractiveSessionResponseNATS(
            session_id=session_id,
            status=calc.status,
            output_dataset_id=calc.output_dataset_id,
        )

        return msg

    async def get_calculation_status(
        self, msg: msg_specs.GetCalculationStatusNATS
    ) -> msg_specs.CalculationStatusResponseNATS:
        """Retrieve the status of a calculation.

        Parameters
        ----------
        msg : msg_specs.GetCalculationStatusNATS
            A NATS message containing the calculation ID to query.

        Returns
        -------
        msg_specs.CalculationStatusResponseNATS
            A response message containing the calculation ID and its current status.

        """
        logger.debug(f"Retrieving calculation details for calculation_id={msg.calculation_id!r}")
        status = self.calculations[msg.calculation_id].status
        logger.debug(f"Current calculation status: {status!r}")
        response = msg_specs.CalculationStatusResponseNATS(
            calculation_id=msg.calculation_id,
            status=status,
        )
        return response

    def get_executable_command(self, command_name):
        """Retrieve an executable command object by its name.

        Parameters
        ----------
        command_name : str
            The name of the command to retrieve.

        Returns
        -------
        ExecutableCommand
            An instance of ExecutableCommand for the specified command.

        """
        command_spec = self.application_spec.get_command_spec_by_name(command_name)
        return ExecutableCommand(command_spec)

    def _set_up_asgi_server(self) -> None:
        """Set up the ASGI server for the client."""
        self.asgi_server = create_client_asgi_server(self.lifespan_context)

    async def _run_custom_shutdown_tasks(self) -> None:
        """Perform custom shutdown tasks for the client."""
        logger.debug("Terminating running calculations...")
        logger.warning("TODO: actually terminate any running calculations...")
        for calc in self._calculations:
            await calc.terminate()

    async def add_interactive_session_to_database(self, msg: msg_specs.CommandExecutionRequestNATS) -> None:
        """Add an interactive session to the database if applicable.

        Parameters
        ----------
        msg : msg_specs.CommandExecutionRequestNATS
            The command execution request message.

        """
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
            f"Added interactive session data manager: {interactive_session_info!r}",
        )

    @on_qcrbox_startup
    async def send_registration_request_via_nats(self) -> None:
        """Send a registration request to the registry to register the app."""
        self.application_spec.gui_port = os.getenv("QCRBOX__GUI__PORT", None)
        logger.debug(f"Sending registration request to QCrBox server: {self.application_spec!r}")

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


def main():
    ap = argparse.ArgumentParser(description="Launch a QCrBox compatible application.")
    ap.add_argument("config_file", help="File path to the application specification file")
    args = ap.parse_args()

    application_config_file = Path(args.config_file)
    application_spec = sql_models.ApplicationSpec.from_yaml_file(application_config_file)

    # Add the directory containing the application config file to PATH so that any scripts
    # present there are available during command execution.
    os.environ["PATH"] = f"{application_config_file.parent.absolute()}:{os.environ['PATH']}"

    qcrbox_client = QCrBoxClient(application_spec=application_spec)
    qcrbox_client.run(host=settings.registry.client.host, port=settings.registry.client.port)


if __name__ == "__main__":
    main()

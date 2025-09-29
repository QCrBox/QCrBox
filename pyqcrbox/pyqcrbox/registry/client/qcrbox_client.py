import argparse
import os
import shutil
from pathlib import Path

import anyio
from litestar import Litestar

from pyqcrbox import helpers, logger, msg_specs, settings, sql_models
from pyqcrbox.data_management import DataManager
from pyqcrbox.debug import log_eel
from pyqcrbox.helpers import generate_private_routing_key
from pyqcrbox.registry.client.executable_command.base_calculation import BaseCalculation
from pyqcrbox.registry.client.executable_command.cli_command import CLICommand
from pyqcrbox.registry.client.executable_command.interactive_session import InteractiveSession
from pyqcrbox.registry.client.executable_command.interactive_session_calculation import InteractiveSessionCalculation
from pyqcrbox.registry.client.executable_command.python_callable import PythonCallable
from pyqcrbox.sql_models import CalculationStatusDetails, CalculationStatusEnum

from ..shared import QCrBoxServerClientBase, TestQCrBoxServerClientBase, on_qcrbox_startup
from .api_endpoints import create_client_asgi_server
from .client_status import ClientStatus, ClientStatusEnum
from .executable_command import ExecutableCommand

__all__ = ["QCrBoxClient", "TestQCrBoxClient"]


class QCrBoxClient(QCrBoxServerClientBase):
    def __init__(
        self,
        application_spec: sql_models.ApplicationSpec,
        *,
        client_id: str = "anonymous_client",
        private_routing_key: str | None = None,
        asgi_server: Litestar | None = None,
    ):
        super().__init__(asgi_server=asgi_server)
        self.application_spec = application_spec
        self.client_id = client_id
        self.private_routing_key = private_routing_key or generate_private_routing_key()
        self._calculations: list[BaseCalculation] = []
        self.status = ClientStatus(client_id, ClientStatusEnum.IDLE)

        self._anyio_lock = anyio.Lock()

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

    def _set_up_asgi_server(self) -> None:
        """Set up the ASGI server for the client."""
        self.asgi_server = create_client_asgi_server(self.lifespan_context)

    async def _run_custom_shutdown_tasks(self) -> None:
        """Perform custom shutdown tasks for the client."""
        logger.debug("Terminating running calculations...")
        for calc in self._calculations:
            await calc.terminate()

    def _set_up_nats_broker(self) -> None:
        """Initialise NATS inbox handlers."""
        slug_sanitized = helpers.sanitize_for_nats_subject(self.application_spec.slug)
        version_sanitized = helpers.sanitize_for_nats_subject(self.application_spec.version)
        self.nats_broker.subscriber(f"client.cmd.handle_invocation_request.{slug_sanitized}.{version_sanitized}")(
            self.handle_command_invocation_request_from_server
        )
        self.nats_broker.subscriber(f"{self.private_inbox}.cmd.discard")(self.handle_discard_command_invocation)
        self.nats_broker.subscriber(f"{self.private_inbox}.cmd.execute")(self.handle_command_execution)
        self.nats_broker.subscriber(f"{self.private_inbox}.cmd.stop")(self.handle_stop_running_command)
        self.nats_broker.subscriber(f"{self.private_inbox}.interactive_session.close")(self.close_interactive_session)

    @on_qcrbox_startup
    async def _send_registration_request_via_nats(self) -> None:
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

    async def _create_calculation_work_dir(self, calculation_id: str) -> Path:
        """Create a working directory for the calculation.

        The name of the directory will be the calculation ID, in the working
        directory for the client.

        Parameters
        ----------
        calculation_id : str
            The ID for the calculation.

        Returns
        -------
        Path
            The path to the working directory for the calculation.

        """
        command_working_dir = self.working_dir / f"{calculation_id}"
        logger.debug(f"Creating new directory {command_working_dir} for command execution")

        # This should/could never happen, but you never know...
        if command_working_dir.exists():
            shutil.rmtree(command_working_dir)

        command_working_dir.mkdir(parents=True)

        return command_working_dir

    @log_eel
    def _remove_calculation_work_dir(self, path: Path) -> None:
        """Remove the directory containing calculation output.

        Parameters
        ----------
        path : Path
            The path to the command/calculation's directory.

        """
        logger.debug(f"Removing directory {path} with contents: {os.listdir(path)}")
        shutil.rmtree(
            path, ignore_errors=True
        )  # No need to worry about errors, it will be cleaned up later if it matters
        logger.debug(f"Removed {path}")

    @log_eel
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

        # Use an anyio lock to avoid a race condition in checking if the client
        # is available to accept a new command
        async with self._anyio_lock:
            is_available = self.status.is_available
            if self.status.is_available:
                self.status.set_pending()
                logger.info(f"Client ({self.private_inbox}) is available, accepting new command request")
            else:
                logger.error(f"Client ({self.private_inbox}) is not available, rejecting new command request")

        new_msg = msg_specs.CommandInvocationClientResponseNATS(
            application_slug=msg.application_slug,
            application_version=msg.application_version,
            client_id=self.client_id,
            client_is_available=is_available,
            calculation_id=msg.calculation_id,
            private_inbox_prefix=self.private_inbox,
        )

        logger.debug(f"Sending message back to server {new_msg}")

        return new_msg

    @log_eel
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
        data_file_manager = await self.svcs_container.aget(DataManager)
        await data_file_manager.update_calculation_status(
            CalculationStatusDetails(
                calculation_id=msg.calculation_id,
                status=CalculationStatusEnum.FAILED,
                extra_info={
                    "error_msg": f"Discarded {msg.calculation_id!r} due to client status {self.status.status}",
                },
            ),
        )

    @log_eel
    async def handle_command_execution(self, execute_request: msg_specs.CommandExecutionRequestNATS) -> None:
        """Handle command execution requests.

        This method handles both interactive sessions and non-interactive commands
        (python_callable and cli_command). When a command is executed in the background,
        a calculation object is returned which we wait for to finish. This handler
        does not return until the whole calculation has finished. For an interactive
        session, this means the prepare, run and finalise steps have to have run.

        Parameters
        ----------
        execute_request : msg_specs.CommandExecutionRequestNATS
            A NATS message containing data about the command to be executed.

        """
        logger.info(f"Received command execution request: {execute_request!r} (current status: {self.status.status})")
        if self.status.status != ClientStatusEnum.PENDING:
            logger.error(
                f"Trying to execute a command when client is not PENDING (current status: {self.status.status})"
            )
            return
        self.status.set_busy()

        calc = None
        data_file_manager = await self.svcs_container.aget(DataManager)
        cmd_work_dir = await self._create_calculation_work_dir(execute_request.calculation_id)

        try:
            command = ExecutableCommand(self.application_spec.get_command_spec_by_name(execute_request.command_name))
            logger.debug(f"Command to execute: {command}")
            if isinstance(command, InteractiveSession):
                await command.add_to_interactive_session_database(
                    data_file_manager, execute_request, self.private_inbox
                )
            parameters = await command.prepare_params(cmd_work_dir, execute_request.command_arguments)
            logger.debug(f"Executing command {command!r} in the background with arguments {parameters!r}")
            calc = await command.execute_in_background(
                **parameters, _calculation_id=execute_request.calculation_id, _cwd=cmd_work_dir
            )
            if not isinstance(calc, BaseCalculation):
                raise RuntimeError("Command execution did not return a calculation object.")
        except Exception as exc:
            # If calc is not set, then the calculation failed to start in the background
            # which is easier to deal with. If the calculation actually started, then we need
            # to do some other stuff
            if calc and isinstance(calc, BaseCalculation):
                await self.handle_calculation_failure(calc, exc)
            else:
                await self.handle_command_launch_failure(execute_request.calculation_id, exc)
            return

        # Keep track of the calculation, which should still be running in the background
        self.calculations[execute_request.calculation_id] = calc
        await data_file_manager.update_calculation_status(await calc.get_status_details())

        # Wait until its finished and when finished, update the details. The calculation can
        # will raise an exception if (one of the interactive) commands failed
        logger.debug("Waiting for calculation to finish after launching in the background")
        try:
            await calc.wait_until_finished()
        except Exception as exc:
            logger.error(f"Calculation failed in background task with exception: {exc!r}")
            await self.handle_calculation_failure(calc, exc)
            return

        logger.debug(f"Exited from calc.wait_until_finished(): {command.type}")
        logger.debug(f"Calculation: {calc}")

        # For non-interactive commands, we need to reset the client to being idle here and
        # save the output to the DataManager. For interactive sessions, that is done
        # instead in `close_interactive_session`
        if command.type != "interactive_session":
            logger.debug("Adding non-interactive output to DataManager")
            try:
                await calc.save_to_data_file_manager(await self.svcs_container.aget(DataManager))
            except (RuntimeError, FileNotFoundError) as exc:
                logger.exception(
                    f"Failed to add output for calculation {calc.calculation_id} to DataManager due to {exc}"
                )
            self._remove_calculation_work_dir(cmd_work_dir)
            self.status.set_idle()

        logger.debug("Updating calculation status after calculation has finished")
        await data_file_manager.update_calculation_status(await calc.get_status_details())

    @log_eel
    async def handle_command_launch_failure(self, calculation_id: str, exception: Exception) -> None:
        """Handle when launching a command fails.

        This method differs from `handle_calculation_failure` as it is used for
        handling failures when a command fails during configuration or when attempting
        to launch it as a background async task.

        Parameters
        ----------
        calculation_id : str
            The calculation ID of the command which failed to launch.
        exception : Exception
            The raised exception causing the failure mode.

        """
        logger.error(f"Failed to launch command with exception: {exception!r}")
        data_file_manager = await self.svcs_container.aget(DataManager)
        await data_file_manager.update_calculation_status(
            CalculationStatusDetails(
                calculation_id=calculation_id,
                status=CalculationStatusEnum.FAILED,
                extra_info={"error_msg": f"Exception raised in background task: {exception!r}"},
            ),
        )
        self._remove_calculation_work_dir(self.working_dir / f"{calculation_id}")
        self.status.set_idle()

    @log_eel
    async def handle_calculation_failure(self, calculation: BaseCalculation, exception: Exception) -> None:
        """Handle when the calculation execution fails, usually due to a raised exception.

        This updates the calculation status to FAILED and sets the client back to
        being idle. You therefore need to return from ASAP `handle_command_execution`
        after calling this function.

        Parameters
        ----------
        calculation: BaseCalculation
            The calculation which failed.
        exception : Exception
            The exception raised by the command.

        """
        logger.error(f"Command calculation failed in background task with exception: {exception!r}")
        data_file_manager = await self.svcs_container.aget(DataManager)
        await data_file_manager.update_calculation_status(
            CalculationStatusDetails(
                calculation_id=calculation.calculation_id,
                status=CalculationStatusEnum.FAILED,
                extra_info={"error_msg": f"Exception raised in background task: {exception!r}"},
            ),
        )

        # Handle any special cases where something extra needs to be done to close
        # off the command/calculation
        match calculation:
            case InteractiveSessionCalculation():
                calculation.is_closed = True
                calculation.session_closed_event.set()
            case PythonCallable():
                pass
            case CLICommand():
                pass

        self._remove_calculation_work_dir(self.working_dir / f"{calculation.calculation_id}")

        # Set client back to being idle, otherwise it won't accept new requests
        self.status.set_idle()

    @log_eel
    async def handle_stop_running_command(
        self, msg: msg_specs.StopRunningCalculationMsg
    ) -> msg_specs.StoppedCalculationResponse:
        """Handle when a long running command is requested to be ended.

        Parameters
        ----------
        msg : msg_specs.EndCommandRequestNATS
            A NATS message containing data about which command/calculation
            should be ended.

        Returns
        -------
        msg_specs.EndCommandResponseNATS
            A NATS message to send back to the API containing data about the
            ended command.

        """
        logger.debug(f"Received request to end command: {msg!r}")
        calculation_id = msg.calculation_id

        # If the client is not busy, then a command isn't running.
        if self.status.status != ClientStatusEnum.BUSY:
            error_msg = f"Client is not busy, there is no command to terminate (client status {self.status.status})"
            logger.error(error_msg)
            return msg_specs.StoppedCalculationResponse(
                calculation_id=calculation_id,
                status=CalculationStatusEnum.UNKNOWN,
                output_dataset_id=None,
                error_msg=error_msg,
            )

        try:
            calc = self.calculations[calculation_id]
        except KeyError:
            error_msg = f"Calculation {calculation_id!r} was not found in client"
            logger.error(error_msg)
            return msg_specs.StoppedCalculationResponse(
                calculation_id=calculation_id,
                status=CalculationStatusEnum.UNKNOWN,
                output_dataset_id=None,
                error_msg=error_msg,
            )

        # If the calculation isn't running, then we can't terminate it (there is
        # nothing to terminate...)
        if calc.status != CalculationStatusEnum.RUNNING:
            error_msg = f"Trying to end calculation {calculation_id} which is not running on the client"
            logger.error(error_msg)
            return msg_specs.StoppedCalculationResponse(
                calculation_id=calculation_id,
                status=calc.status,
                output_dataset_id=calc.output_dataset_id,
                error_msg=error_msg,
            )

        logger.debug(f"Terminating running calculation {calc!r}")
        logger.debug(f"{calc.calculation_id=} {calc.calc_finished_event=} {calc.return_value=}")

        try:
            await calc.terminate()
            calc.calc_finished_event.set()
        except AttributeError:
            exc_msg = f"Calculation {calculation_id} does not have a terminate method, something very bad has happened"
            logger.exception(exc_msg)
            return msg_specs.StoppedCalculationResponse(
                calculation_id=calculation_id,
                status=CalculationStatusEnum.FAILED,
                output_dataset_id=None,
                error_msg=exc_msg,
            )

        # Mark the client as being idle now that the calculation has been terminated
        # and update the status of the calculation. If we don't update the status here,
        # it'll still be be marked as RUNNING in the calculation database
        logger.debug("Setting container to idle and updating calculation status after forced termination")
        self._remove_calculation_work_dir(self.working_dir / f"{calc.calculation_id}")
        data_file_manager = await self.svcs_container.aget(DataManager)
        await data_file_manager.update_calculation_status(await calc.get_status_details())
        self.status.set_idle()

        return msg_specs.StoppedCalculationResponse(
            calculation_id=calculation_id,
            status=calc.status,
            output_dataset_id=calc.output_dataset_id,
            error_msg=calc.get_error_message(),
        )

    @log_eel
    async def close_interactive_session(
        self, msg: msg_specs.CloseInteractiveSessionNATS
    ) -> msg_specs.CloseInteractiveSessionResponse:
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
        session_id = msg.session_id
        logger.info(f"Received request to close interactive session: {msg!r}")

        if session_id not in self.calculations:
            logger.error(f"Calculation not found in client for {session_id!r}")
            response = msg_specs.CloseInteractiveSessionResponse(
                session_id=session_id,
                status=CalculationStatusEnum.UNKNOWN,
                output_dataset_id=None,
            )
            return response

        calc = self.calculations[session_id]
        logger.debug(f"Attempting to close interactive session: {calc}")
        try:
            await calc.terminate()
        except AttributeError:
            logger.exception(f"Unable to terminate interactive session: {calc!r}")
            response = msg_specs.CloseInteractiveSessionResponse(
                session_id=session_id, status=CalculationStatusEnum.FAILED, output_dataset_id=None
            )
            return response
        self._remove_calculation_work_dir(self.working_dir / f"{calc.calculation_id}")
        self.status.set_idle()
        logger.debug("Interactive session has been closed and client set to idle")

        response = msg_specs.CloseInteractiveSessionResponse(
            session_id=session_id,
            status=calc.status,
            output_dataset_id=calc.output_dataset_id,
            error_msg=calc.get_error_message(),
        )

        return response


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

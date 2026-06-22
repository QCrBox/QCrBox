import argparse
import os
import shutil
from pathlib import Path

import anyio
from litestar import Litestar

from pyqcrbox import helpers, logger, msg_specs, settings, sql_models
from pyqcrbox.debug import log_eel
from pyqcrbox.helpers import generate_private_routing_key
from pyqcrbox.registry.client.executable_command.base_calculation import BaseCalculation
from pyqcrbox.registry.client.executable_command.base_command import BaseCommand
from pyqcrbox.registry.client.executable_command.cli_command import CLICommand
from pyqcrbox.registry.client.executable_command.interactive_session import InteractiveSession
from pyqcrbox.registry.client.executable_command.interactive_session_calculation import InteractiveSessionCalculation
from pyqcrbox.registry.client.executable_command.python_callable import PythonCallable
from pyqcrbox.sql_models import CalculationStatusDetails, CalculationStatusEnum
from pyqcrbox.sql_models.parameter_spec.base_parameter_spec import (
    BaseParameter,
    Cif2CifOptions,
    get_cif_merge_parameter,
)

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
        self._cmd_work_dir = self.working_dir

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
        # TODO: Remove this once the API has been updated to remove the requirement for a GUI port
        self.application_spec.gui_port = "-9999"
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

    async def _create_calculation_work_dir(self, calculation_id: str) -> None:
        """Create a working directory for the calculation.

        The name of the directory will be the calculation ID, in the working
        directory for the client.

        Parameters
        ----------
        calculation_id : str
            The ID for the calculation.

        """
        command_working_dir = self.working_dir / f"{calculation_id}"
        logger.debug(f"Creating new directory {command_working_dir} for command execution")

        # This should/could never happen, but you never know...
        if command_working_dir.exists():
            shutil.rmtree(command_working_dir, ignore_errors=True)

        command_working_dir.mkdir(parents=True)
        self._cmd_work_dir = command_working_dir

    @log_eel
    def _remove_calculation_work_dir(self) -> None:
        """Remove the directory containing calculation output."""
        if settings.registry.client.keep_calc_work_dir:
            logger.info(f"Keeping calculation directory due to setting configuration: {self._cmd_work_dir}")
            return
        logger.debug(f"Removing directory {self._cmd_work_dir} with contents: {os.listdir(self._cmd_work_dir)}")
        shutil.rmtree(
            self._cmd_work_dir, ignore_errors=True
        )  # No need to worry about errors, it will be cleaned up later if it matters
        logger.debug(f"Removed calculation directory: {self._cmd_work_dir}")
        self._cmd_work_dir = self.working_dir

    async def _can_execute_command(self) -> bool:
        """Check if the client can execute a requested command or not.

        Returns
        -------
        bool
            Returns False if the client is busy, indicating that a the client
            cannot execute the command.

        """
        if self.status.status != ClientStatusEnum.PENDING:
            logger.error(f"Cannot execute command, client not PENDING (status: {self.status})")
            return False

        self.status.set_busy()

        return True

    @log_eel
    async def _prepare_and_launch_command(
        self, execute_request: msg_specs.CommandExecutionRequestNATS
    ) -> tuple[BaseCommand, dict[str, BaseParameter], BaseCalculation]:
        """Launch the requested command.

        Parameters
        ----------
        execute_request : msg_specs.CommandExecutionRequestNATS
            The execution request message for the command, as sent via the NATS
            broker.

        Returns
        -------
        BaseCommand
            A BaseCommand class for command which was launched successfully.
        dict[str, BaseParameter]
            A dict mapping of the parameter name and the QCrBox class
            representations of the value of that parameter. This is a collection
            of the parameters used by the command.
        BaseCalculation
            A BaseCalculation class used for tracking the command executing in
            the background.

        """
        command = ExecutableCommand(self.application_spec.get_command_spec_by_name(execute_request.command_name))
        parsed_parameters, prepared_parameters = await command.prepare_params(
            self.application_spec, execute_request.command_arguments, self._cmd_work_dir
        )
        if isinstance(command, InteractiveSession):
            await command.store_interactive_session_details(self.data_manager, execute_request, self.private_inbox)

        logger.debug(f"Executing command {command!r} with arguments: {prepared_parameters!r}")
        calc = await command.execute_in_background(
            **prepared_parameters, _calculation_id=execute_request.calculation_id, _cwd=self._cmd_work_dir
        )

        return command, parsed_parameters, calc

    @log_eel
    async def _handle_non_interactive_output(
        self,
        command: BaseCommand,
        calc: BaseCalculation,
        command_parameters: dict[str, BaseParameter],
    ) -> None:
        """Handle saving the output from non-interactive commands/calculations.

        Parameters
        ----------
        command_name : BaseCommand
            The BaseCommand object used to launch the command.
        calc : BaseCalculation
            The BaseCalculation object used to track the execution of the
            non-interactive command.
        command_parameters : dict[str, BaseParameter]
            The parameters which were used to execute the command. These will be
            parsed as QCrBox data types.

        """
        logger.debug(f"Adding output from non-interactive command {command.name} into data manager")

        try:
            parameter_name, cif_parameter, output_path = await get_cif_merge_parameter(command, command_parameters)

            # If we found a QCrBox.cif_data_file or QCrBox.output_cif in the above
            # function call, then we will attempt to created a merged CIF
            if cif_parameter and parameter_name:
                merge_options = Cif2CifOptions(
                    application_yaml=self.application_spec.yaml_file_path,  # type: ignore
                    command_name=command.name,
                    parameter_name=parameter_name,
                    output_path=output_path,
                )
                dataset_id = await calc.save_output_to_data_manager(
                    self.data_manager, merge_options=merge_options, input_cif=cif_parameter
                )
            else:
                dataset_id = await calc.save_output_to_data_manager(self.data_manager)
        except Exception as exc:
            logger.error(f"Failed to store output calculation {calc.calculation_id} in data manager: {exc}")
        else:
            logger.debug(f"Output for non-interactive has been added to the data manager into dataset {dataset_id}")

        self._remove_calculation_work_dir()
        self.status.set_idle()

    @log_eel
    async def _handle_interactive_output(
        self,
        command: BaseCommand,
        calc: InteractiveSessionCalculation,
        command_parameters: dict[str, BaseParameter],
    ) -> None:
        """Handle saving the output from interactive commands/calculations.

        Parameters
        ----------
        command_name : BaseCommand
            The BaseCommand object used to launch the command.
        calc : BaseCalculation
            The BaseCalculation object used to track the execution of the
            non-interactive command.
        command_parameters : dict[str, BaseParameter]
            The parameters which were used to execute the command. These will be
            parsed as QCrBox data types.

        """
        from pyqcrbox.registry.client.executable_command.error import FinaliseCommandFailure, error_dialog_box

        if not calc.finalise_calc:
            logger.info(f"Interactive session {calc.calculation_id} has no finalise method, so cannot get output")
            calc.is_closed = True
            calc.session_closed_event.set()
            return

        logger.debug("Waiting for finalise command to finish running to get output")
        await calc.finalise_calc.wait_until_finished()

        if calc.finalise_calc.exception_raised:
            calc_status = calc.finalise_calc.status
            logger.error(f"Exception raised by finalise_cmd ({calc_status}): {calc.finalise_calc.exception_raised!r}")
            calc._error_dialog_process = error_dialog_box(
                f"An error occurred in the finalise command: {calc.finalise_calc.exception_raised}"
            )
            calc.exception = FinaliseCommandFailure("Finalise command failed", calc.finalise_calc.exception_raised)
            raise calc.exception from calc.finalise_calc.exception_raised

        logger.debug("Finalise command has finished")
        logger.debug(f"Adding output from interactive command {command.name} into data manager")
        try:
            parameter_name, cif_parameter, output_path = await get_cif_merge_parameter(command, command_parameters)

            # If we found a QCrBox.cif_data_file or QCrBox.output_cif in the above
            # function call, then we will attempt to created a merged CIF
            if cif_parameter and parameter_name:
                merge_options = Cif2CifOptions(
                    application_yaml=self.application_spec.yaml_file_path,  # type: ignore
                    command_name=command.name,
                    parameter_name=parameter_name,
                    output_path=output_path,
                )
                dataset_id = await calc.save_output_to_data_manager(
                    self.data_manager, merge_options=merge_options, input_cif=cif_parameter
                )
            else:
                dataset_id = await calc.save_output_to_data_manager(self.data_manager)
        except Exception as exc:
            logger.error(f"Failed to store output calculation {calc.calculation_id} in data manager: {exc}")
        else:
            logger.debug(f"Output for non-interactive has been added to the data manager into dataset {dataset_id}")

        calc.is_closed = True
        calc.session_closed_event.set()

    @log_eel
    async def _handle_command_launch_failure(self, calculation_id: str, exception: Exception) -> None:
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
        await self.data_manager.update_calculation_status(
            CalculationStatusDetails(
                calculation_id=calculation_id,
                status=CalculationStatusEnum.FAILED,
                extra_info={"error_msg": f"Exception raised in background task: {exception!r}"},
            ),
        )
        self._remove_calculation_work_dir()
        self.status.set_idle()

    @log_eel
    async def _handle_calculation_failure(self, calculation: BaseCalculation, exception: Exception) -> None:
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
        await self.data_manager.update_calculation_status(
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

        self._remove_calculation_work_dir()

        # Set client back to being idle, otherwise it won't accept new requests
        self.status.set_idle()

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
        await self.data_manager.update_calculation_status(
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
        """Handle when a command execution is requested.

        Parameters
        ----------
        execute_request : msg_specs.CommandExecutionRequestNATS
            A command execution request.

        """
        logger.info(f"Received command execution request: {execute_request!r} (current status: {self.status.status})")
        if not await self._can_execute_command():
            return

        await self._create_calculation_work_dir(execute_request.calculation_id)

        try:
            command, parameters, calc = await self._prepare_and_launch_command(execute_request)
        except Exception as exc:
            logger.error(f"Exception raised during command launch: {exc}")
            await self._handle_command_launch_failure(execute_request.calculation_id, exc)
            return

        self.calculations[execute_request.calculation_id] = calc
        await self.data_manager.update_calculation_status(await calc.get_status_details())

        logger.debug(f"Waiting for calculation {calc.calculation_id} to finish")
        try:
            await calc.wait_until_finished()
        except Exception as exc:
            await self._handle_calculation_failure(calc, exc)
            return
        logger.debug(f"Calculation {calc.calculation_id} has finished")

        try:
            if command.type != "interactive_session":
                # Note that this method will also remove the calculation directory
                await self._handle_non_interactive_output(command, calc, parameters)
            else:
                await self._handle_interactive_output(command, calc, parameters)
        except Exception as exc:
            await self._handle_calculation_failure(calc, exc)
            return

        logger.debug("Updating calculation status after calculation has finished")
        await self.data_manager.update_calculation_status(await calc.get_status_details())

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
        self._remove_calculation_work_dir()
        await self.data_manager.update_calculation_status(await calc.get_status_details())
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
        await calc.terminate()

        self._remove_calculation_work_dir()
        await self.data_manager.update_calculation_status(await calc.get_status_details())
        self.status.set_idle()
        logger.debug("Interactive session has been closed and client set to idle")

        response = msg_specs.CloseInteractiveSessionResponse(
            session_id=session_id,
            status=calc.status,
            output_dataset_id=calc.output_dataset_id,
            error_msg=calc.get_error_message(),
        )

        return response


class TestQCrBoxClient(TestQCrBoxServerClientBase, QCrBoxClient):  # type: ignore
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

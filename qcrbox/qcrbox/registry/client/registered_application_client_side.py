import asyncio
from typing import Optional

from loguru import logger
from propan import PropanApp

from .. import msg_specs
from .external_command import ExternalCommand
from .python_callable import PythonCallable


class RegisteredApplicationClientSide:
    def __init__(
        self,
        name: str,
        *,
        version: str,
        description: Optional[str] = None,
        url: Optional[str] = None,
        client: "QCrBoxRegistryClient",
        propan_app: PropanApp,
        routing_key__registry_to_application: str,
    ):
        self.app_name = name
        self.version = version
        self.description = description
        self.url = url
        self.client = client
        self.propan_app = propan_app
        self.assigned_app_id = (
            None  # will be assigned by the registry client and sent as part of the registration handshake
        )
        self.assigned_container_id = (
            None  # will be assigned by the registry client and sent as part of the registration handshake
        )
        self._command_callbacks = {}
        self._calculations = {}

        self.routing_key__registry_to_application = routing_key__registry_to_application
        logger.debug(f"Name of anonymous callback queue: {self.routing_key__registry_to_application!r}")

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.app_name!r} (id: {self.assigned_app_id!r})>"

    async def _send_register_command_message_to_server(self, *, cmd_name, parameters, on_command_invoked):
        if self.assigned_app_id is None:
            logger.debug(
                "Assigned app id is still None, waiting for response from registry server"
                "before sending register_command message."
            )
            for i in range(100):
                # logger.debug(f"   [Step {i:2d}/100]")
                await asyncio.sleep(0.01)
                if self.assigned_app_id is not None:
                    break
            else:
                raise RuntimeError("Never received a response to the register_application message. :( Aborting.")

        if not isinstance(on_command_invoked, (ExternalCommand, PythonCallable)):
            raise NotImplementedError(
                f"The 'on_command_invoked' argument must be an instance of ExternalCommand."
                f"Other callback types are not supported yet."
            )

        msg = msg_specs.RegisterCommand(
            action="register_command",
            payload=msg_specs.QCrBoxCommandCreate(
                name=cmd_name,
                parameters=parameters,
                application_id=self.assigned_app_id,
                container_id=self.assigned_container_id,
            ),
        )

        logger.info(f"Sending register_command message for cmd_name={cmd_name!r}")
        response = await self.propan_app.broker.publish(
            msg, queue="qcrbox_registry", callback=True, callback_timeout=None
        )
        response = msg_specs.QCrBoxGenericResponse(**response)
        logger.info(f"Received response: {response!r}")
        if response.status == "success":
            self._command_callbacks[response.payload["command_id"]] = on_command_invoked
            logger.info(f"Successfully registered command {cmd_name!r}")
        elif response.status == "error":
            raise Exception(response.msg)
        else:
            raise RuntimeError(f"Unexpected response status: {response.status}")

    def register_external_command(self, cmd_name: str, external_cmd: ExternalCommand):
        if not isinstance(external_cmd, ExternalCommand):
            raise TypeError(
                f"The argument 'external_cmd' must be an instance of ExternalCommand. "
                f"Got: {type(external_cmd).__name__}"
            )

        self.client.schedule_startup_task(
            self._send_register_command_message_to_server(
                cmd_name=cmd_name,
                parameters={param_name: "str" for param_name in external_cmd.parameter_names},
                on_command_invoked=external_cmd,
            ),
            name=f"register_command__{cmd_name}",
        )

    def register_python_callable(self, cmd_name: str, python_callable: PythonCallable):
        if not isinstance(python_callable, PythonCallable):
            raise TypeError(
                f"The argument 'python_callable' must be an instance of PythonCallable. "
                f"Got: {type(python_callable).__name__}"
            )

        self.client.schedule_startup_task(
            self._send_register_command_message_to_server(
                cmd_name=cmd_name,
                parameters={param_name: "str" for param_name in python_callable.parameter_names},
                on_command_invoked=python_callable,
            ),
            name=f"register_command__{cmd_name}",
        )

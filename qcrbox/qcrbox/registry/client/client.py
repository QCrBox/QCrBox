import asyncio
import os
from pathlib import Path
from signal import SIGINT, SIGTERM
from typing import Optional

import pydantic
from propan import RabbitBroker, PropanApp
from propan.brokers.rabbit import RabbitQueue

from ...logging import logger
from qcrbox.common import msg_specs, get_rabbitmq_connection_url, get_qcrbox_registry_api_connection_url
from ..helpers import schedule_asyncio_task
from .messaging import process_message_sync_or_async
from .helpers import create_new_private_routing_key, create_new_container_qcrbox_id
from .registered_application_client_side import RegisteredApplicationClientSide


class QCrBoxRegistryClient:
    def __init__(
        self,
        *,
        rabbitmq_host: Optional[str] = None,
        rabbitmq_port: Optional[int] = None,
        qcrbox_registry_api_host: Optional[str] = None,
        qcrbox_registry_api_port: Optional[int] = None,
    ):
        rabbitmq_url = get_rabbitmq_connection_url(host=rabbitmq_host, port=rabbitmq_port)
        self.qcrbox_registry_api_url = get_qcrbox_registry_api_connection_url(
            host=qcrbox_registry_api_host, port=qcrbox_registry_api_port
        )
        self.broker = RabbitBroker(url=rabbitmq_url)
        self.propan_app = PropanApp(self.broker)
        self.event_loop = asyncio.get_event_loop()
        self._scheduled_startup_tasks = []

    @property
    def is_within_interactive_python_session(self):
        return self.event_loop.is_running()

    def __repr__(self):
        return f"<{self.__class__.__name__}>"

    def schedule_startup_task(self, coro, *, name):
        task = schedule_asyncio_task(coro, loop=self.event_loop)
        self._scheduled_startup_tasks.append((name, task))

    async def _send_register_application_message_and_assign_application_id_when_successful(
        self, *, msg, registered_app_client_side, callback_timeout
    ):
        await self.broker.start()  # ensure broker is started
        response = await self.broker.publish(
            msg,
            queue="qcrbox_registry",
            callback=True,
            callback_timeout=callback_timeout,
            raise_timeout=True,
        )
        logger.info(f"Received response: {response} (type: {type(response).__name__})")
        response = msg_specs.QCrBoxGenericResponse(**response)
        if response.status == "success":
            registered_app_client_side.assigned_app_id = response.payload["application_id"]
            registered_app_client_side.assigned_container_id = response.payload["container_id"]
            logger.debug(f"Assigned application_id: {registered_app_client_side.assigned_app_id}")
            logger.debug(f"Assigned container_id: {registered_app_client_side.assigned_container_id}")
        elif response.status == "error":
            raise Exception(response.msg)
        else:
            raise RuntimeError(f"Unexpected response status: {response.status}")
        return response

    def register_application(self, name, *, version, description=None, url=None, timeout=5.0):
        routing_key__registry_to_application = create_new_private_routing_key()
        container_qcrbox_id = create_new_container_qcrbox_id()

        application = RegisteredApplicationClientSide(
            name=name,
            version=version,
            description=description,
            url=url,
            client=self,
            propan_app=self.propan_app,
            routing_key__registry_to_application=routing_key__registry_to_application,
        )

        msg = msg_specs.RegisterApplication(
            action="register_application",
            payload=msg_specs.QCrBoxApplicationCreate(
                name=name,
                version=version,
                description=description,
                url=url,
                routing_key__registry_to_application=routing_key__registry_to_application,
                container_qcrbox_id=container_qcrbox_id,
            ),
        )

        self.schedule_startup_task(
            self._send_register_application_message_and_assign_application_id_when_successful(
                msg=msg,
                registered_app_client_side=application,
                callback_timeout=timeout,
            ),
            name="register_app",
        )

        queue = RabbitQueue(routing_key__registry_to_application, auto_delete=True)

        async def register_handler_for_incoming_messages_from_registry_server():
            # Temporarily suspend the broker in case it is running (otherwise
            # registering a new handler won't take effect until a restart).
            await self.propan_app.broker.close()

            @self.propan_app.broker.handle(queue, retry=False)
            async def handle_incoming_messages_from_registry_server(msg_dict):
                for cls in msg_specs.VALID_QCRBOX_MESSAGES:
                    try:
                        msg_obj = cls(**msg_dict)
                        break
                    except pydantic.ValidationError as exc:
                        pass
                else:
                    error_msg = f"Incoming message is not a valid QCrBox message: {msg_dict}"
                    logger.error(error_msg)
                    return msg_specs.QCrBoxGenericResponse(
                        response_to="incoming_message", status="error", msg=error_msg
                    )

                # logger.debug(f"Incoming message: {msg_obj} (app_id: {self.assigned_app_id})")
                if application.assigned_app_id is None or application.assigned_container_id is None:
                    if not isinstance(msg_obj, msg_specs.RegisterApplication):
                        # We should never reach this branch, but let's be safe and throw an error if we do.
                        raise RuntimeError(
                            "Ignoring message as app has not fully started up yet "
                            "(missing `assigned_app_id` or `assigned_container_id`)."
                        )
                    else:
                        logger.debug(f"Received 'register_application' message: {msg_obj}")

                logger.debug(f"[DDD] Calling 'process_message_sync_or_async()' ...")
                res = await process_message_sync_or_async(msg_obj, application)
                logger.debug(f"[DDD] Received result from 'process_message_sync_or_async()': {res}")
                return res

            # Resume broker now that the new hander has been registered.
            await self.propan_app.broker.start()

        self.schedule_startup_task(
            register_handler_for_incoming_messages_from_registry_server(),
            name="add_incoming_message_handler",
        )

        async def save_container_qcrbox_id_to_file():
            qcrbox_home_dir = Path(os.environ.get("QCRBOX_HOME", "/opt/qcrbox/"))
            with qcrbox_home_dir.joinpath("container_qcrbox_id.txt").open("w") as f:
                f.write(f"{container_qcrbox_id}\n")

        self.schedule_startup_task(save_container_qcrbox_id_to_file(), name="save_container_qcrbox_id_to_file")

        # logger.info(f"Result of running the coroutine: {task}")
        return application

    async def wait_for_startup_tasks(self):
        def ensure_exceptions_are_raised(task):
            exc = task.exception()
            if exc is not None:
                raise exc

        for name, task in self._scheduled_startup_tasks:
            if task is None:
                continue
            await task
            assert task.done()
            ensure_exceptions_are_raised(task)

        # TODO: only write this if we're inside a container
        logger.debug("Writing sentinel file /tmp/SENTINEL_QCRBOX_CLIENT_STARTUP_SUCCESSFUL.txt")
        with open("/tmp/SENTINEL_QCRBOX_CLIENT_STARTUP_SUCCESSFUL.txt", "w") as f:
            f.write("QCrBox client successfully started up.")

        logger.debug(f"All startup tasks completed successfully.")

    async def run_async(self):
        try:
            await self.wait_for_startup_tasks()
            await self.propan_app.run()
        except asyncio.CancelledError:
            logger.info("Server terminated by user, shutting down.")

    def run(self):
        if self.is_within_interactive_python_session:
            logger.warning(
                "Cannot call client.run() from within an interactive Python session "
                "because it has an already running asyncio event loop.\n"
                "Please call 'await client.run_async()' instead."
            )
            return

        main_task = asyncio.ensure_future(self.run_async())

        for signal in [SIGINT, SIGTERM]:
            self.event_loop.add_signal_handler(signal, main_task.cancel)

        self.event_loop.run_until_complete(main_task)
        self.event_loop.close()

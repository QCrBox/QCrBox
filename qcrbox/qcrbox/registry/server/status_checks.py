
import sqlalchemy.exc
from loguru import logger
from propan import RabbitBroker
from sqlmodel import Session
from qcrbox.common import get_rabbitmq_connection_url, msg_specs
from .database import engine, retrieve_container, retrieve_containers


async def get_container_status_response(container_id: int, callback_timeout: float = 1.0):
    logger.debug(f"Retrieving status of container with id={container_id}")
    try:
        container = retrieve_container(container_id)
    except sqlalchemy.exc.NoResultFound:
        response = msg_specs.GetContainerStatusResponse(
            response_to="get_container_status",
            status="error",
            msg=f"No container exists with {container_id=}",
            payload=msg_specs.GetContainerStatusResponsePayload(
                container_status="not_found",
                container_id=container_id,
            )
        ).dict()
        return response

    broker = RabbitBroker(get_rabbitmq_connection_url())
    await broker.start()

    msg = msg_specs.GetContainerStatus(
        action="get_container_status",
        payload=msg_specs.GetContainerStatusPayload(container_id=container_id),
    )

    queue = container.routing_key__registry_to_application
    logger.debug(f"Sending message 'get_container_status' to queue {queue!r}")

    try:
        response = await broker.publish(
            msg,
            queue=container.routing_key__registry_to_application,
            callback=True,
            callback_timeout=callback_timeout,
            raise_timeout=True,
        )
    except TimeoutError:
        response = msg_specs.GetContainerStatusResponse(
            response_to="get_container_status",
            status="error",
            msg=f"Container did not respond within timeout ({callback_timeout})",
            payload=msg_specs.GetContainerStatusResponsePayload(
                container_status="unreachable",
                container_id=container_id,
            )
        ).dict()
    logger.debug(f"Container status: {response}")

    return response


async def get_container_status(container_id: int, callback_timeout: float = 1.0):
    response = await get_container_status_response(container_id, callback_timeout=callback_timeout)
    return response["payload"]["container_status"]


async def update_status_of_all_containers(callback_timeout: float = 1.0):
    logger.info("Updating status of all containers in the registry database...")
    for container in retrieve_containers():
        updated_status = await get_container_status(container.id, callback_timeout=callback_timeout)
        logger.debug(f"   {updated_status=}")

        with Session(engine) as session:
            container.status = updated_status
            session.add(container)
            session.commit()
            session.refresh(container)
            logger.debug(f"Updated container status in registry database (qcrbox_id={container.qcrbox_id!r}).")

    logger.info("Status of all containers has been updated")

import sqlalchemy.exc
from propan import RabbitBroker
from qcrbox.common import get_rabbitmq_connection_url, msg_specs, sql_models
from .database import retrieve_container


async def get_container_status(container_id, callback_timeout=1.0):
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
        )
        return response

    broker = RabbitBroker(get_rabbitmq_connection_url())
    await broker.start()

    msg = msg_specs.GetContainerStatus(
        action="get_container_status",
        payload=msg_specs.GetContainerStatusPayload(container_id=container_id),
    )

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
        )

    return response

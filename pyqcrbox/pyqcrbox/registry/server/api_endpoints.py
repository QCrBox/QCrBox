from pathlib import Path

import jinjax
from litestar import MediaType, Response, get

from pyqcrbox.data_management.data_file import QCrBoxDataFile

__all__ = []

here = Path(__file__).parent

catalog = jinjax.Catalog()
catalog.add_folder(here / "components")


def render(*args, **kwargs) -> Response:
    rendered_content = catalog.render(*args, **kwargs)
    return Response(content=rendered_content, media_type=MediaType.HTML)


@get(path="/data_files_page")
async def data_files_page() -> Response:
    # return render("DataFilesPage", data_files=await _get_data_files())
    return render(
        "DataFilesPage",
        data_files=[
            QCrBoxDataFile(qcrbox_file_id="123", filename="test1.txt", contents=b"Hello, world!"),
            QCrBoxDataFile(qcrbox_file_id="456", filename="test2.txt", contents=b""),
        ],
    )


# async def _invoke_command_impl_via_nats(cmd: sql_models.CommandInvocationCreate, nats_broker: NatsBroker):
#     msg = msg_specs.InvokeCommand(payload=cmd)
#
#     try:
#         # send command invocation request to any available clients
#         await nats_broker.publish(
#             msg,
#             f"cmd-invocation.request.{msg.payload.nats_subject}",
#             rpc=True,
#             raise_timeout=True,
#             rpc_timeout=settings.nats.rpc_timeout,
#         )
#     except TimeoutError:
#         raise ServiceUnavailableException("No clients available to execute command.")


# @post(path="/commands/invoke_OLD", media_type=MediaType.JSON)
# async def commands_invoke_OLD(data: sql_models.CommandInvocationCreate) -> dict:
#     logger.info(f"[DDD] Received {data=}")
#
#     with svcs.Container(QCRBOX_SVCS_REGISTRY) as con:
#         # broker = await con.aget(RabbitBroker)
#         nats_broker = await con.aget(NatsBroker)
#
#     # await _invoke_command_impl(data, broker)
#     # await _invoke_command_impl_via_nats(data, broker)
#     msg = msg_specs.CommandInvocationRequest(payload=data)
#
#     client_response_event = anyio.Event()
#     reply_subject = f"cmd-invocation.response.{msg.payload.correlation_id}"
#
#     await nats_broker.close()
#
#     @nats_broker.subscriber(reply_subject, filter=lambda msg: msg.content_type == "")
#     async def discard_spurious_empty_messages(msg: bytes):
#         logger.warning(
#             f"Discarding spurious empty message: {msg} (this seems to be "
#             f"a FastStream bug, but it should not cause any issues)."
#         )
#
#     @nats_broker.subscriber(reply_subject, filter=lambda msg: msg.content_type != "")
#     async def handle_client_response(response_msg: dict):
#         logger.debug(f"Received response from client: {response_msg}")
#         if not client_response_event.is_set():
#             client_response_event.set()
#             return "All systems go!"
#         else:
#             return "Better luck next time."
#
#     await nats_broker.start()
#
#     # send command invocation request to any available clients
#
#     my_publish_func = functools.partial(
#         nats_broker.publish,
#         subject=f"cmd-invocation.request.{msg.payload.nats_subject}",
#         reply_to=reply_subject,
#     )
#
#     async with anyio.create_task_group() as tg:
#         with anyio.move_on_after(settings.nats.rpc_timeout):
#             tg.start_soon(my_publish_func, msg)
#             # tg.start_soon(client_response_event.wait)
#             await client_response_event.wait()
#
#     if not client_response_event.is_set():
#         logger.debug("No client responded within the timeout.")
#         raise ServiceUnavailableException("No client available to execute command.")
#
#     return dict(
#         msg="Accepted command invocation request",
#         status="ok",
#         payload={
#             "correlation_id": data.correlation_id,
#         },
#     )

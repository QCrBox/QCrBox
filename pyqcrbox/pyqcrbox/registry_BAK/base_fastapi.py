import uvicorn
from fastapi import Depends, FastAPI
from faststream.rabbit.fastapi import Logger, RabbitRouter
from loguru import logger
from pydantic import BaseModel

from pyqcrbox import settings


# class QCrBoxFastStream:
#     pass
#
#
# class QCrBoxFastStreamWithFastAPI(FastAPI, QCrBoxFastStream):
#     def __init__(self, router: RabbitRouter):
#         super().__init__(lifespan=router.lifespan_context)
#         self.include_router(router)


router = RabbitRouter(settings.rabbitmq.url)
qcrbox_app = QCrBoxFastStreamWithFastAPI(router)


def main():
    class Incoming(BaseModel):
        m: dict

    def call():
        logger.debug("We got called!")
        return True

    @router.subscriber("test")
    @router.publisher("response")
    async def hello(m: Incoming, logger: Logger, d=Depends(call)):
        logger.info(m)
        return {"response": "Hello, Rabbit!"}

    @router.get("/")
    async def hello_http():
        return "Hello, HTTP!"

    logger.info("Starting QCrBox registry server")
    try:
        uvicorn.run("pyqcrbox.registry.base_fastapi:qcrbox_app", host="0.0.0.0", port=8001, reload=True)
    except Exception as exc:
        logger.error(f"[DDD] {exc=}")
        raise


if __name__ == "__main__":
    main()

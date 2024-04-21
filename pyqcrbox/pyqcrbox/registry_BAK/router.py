from faststream.rabbit.fastapi import RabbitRouter

from pyqcrbox import settings

from .msg_counter import MsgCounter


class QCrBoxRabbitRouter(RabbitRouter):
    def __init__(self, url, *args, **kwargs):
        super().__init__(url, *args, **kwargs)
        self._msg_counter = MsgCounter()

    def increment_processed_message_counter(self):
        # Forward to the internal MsgCounter instance
        self._msg_counter.increment_processed_message_counter()


router = QCrBoxRabbitRouter(url=settings.rabbitmq.url)

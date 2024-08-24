import math

import anyio
from loguru import logger


class MsgCounter:
    def __init__(self):
        self._shutdown_event = anyio.Event()
        self._max_messages = math.inf
        self.msg_counter = 0
        self.logger = logger

    @property
    def max_messages(self):
        return self._max_messages

    def increment_processed_message_counter(self):
        self.msg_counter += 1
        self.logger.debug(f"Current message count: {self.msg_counter}")
        if self.msg_counter >= self._max_messages:
            self.logger.info(f"Reached maximum number of messages ({self._max_messages}), shutting down.")
            self.request_shutdown()

    def request_shutdown(self):
        self._shutdown_event.set()

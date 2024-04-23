from contextlib import asynccontextmanager

from .qcrbox_server import QCrBoxServer


class TestQCrBoxServer(QCrBoxServer):
    @asynccontextmanager
    async def run(self):
        self._set_up_uvicorn_server()
        yield self
        self.shutdown()

    def get_mock_handler(self, queue_name):
        subscr = self._get_subscriber(queue_name)
        assert len(subscr.calls) == 1
        handler = subscr.calls[0].handler
        return handler.mock

    def _get_subscriber(self, queue_name):
        cands = []
        for s in self.broker._subscribers.values():
            if s.queue.name == queue_name:
                cands.append(s)

        match len(cands):
            case 1:
                return cands[0]
            case 0:
                raise ValueError(f"No subscriber found for queue {queue_name!r}")
            case _:
                raise ValueError(f"More than one subscriber found for queue {queue_name!r}")

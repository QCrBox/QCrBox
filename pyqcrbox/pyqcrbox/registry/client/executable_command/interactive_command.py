from pyqcrbox.registry.client.executable_command import BaseCommand

__all__ = ["InteractiveCommand"]


class InteractiveCommand(BaseCommand):
    def terminate(self):
        raise NotImplementedError("TODO: implement terminate() for interactive commands")

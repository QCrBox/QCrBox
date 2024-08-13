from pyqcrbox.registry.client.executable_command import BaseCommand

__all__ = ["InteractiveCommand"]


class InteractiveCmdCalculation:
    pass


class InteractiveCommand(BaseCommand):
    async def execute_in_background(
        self,
        _calculation_id: str,
        _stdin=None,
        _stdout=None,
        _stderr=None,
        **kwargs,
    ) -> InteractiveCmdCalculation:
        pass

    def terminate(self):
        raise NotImplementedError("TODO: implement terminate() for interactive commands")

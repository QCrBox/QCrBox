import anyio

from pyqcrbox import helpers, logger
from pyqcrbox.registry.client.executable_command import BaseCommand
from pyqcrbox.registry.client.executable_command.calculation import BaseCalculation
from pyqcrbox.sql_models_NEW_v2 import CalculationStatusEnum, CommandSpecDiscriminatedUnion, InteractiveCommandSpec

__all__ = ["InteractiveCommand"]


class InteractiveCmdCalculation(BaseCalculation):
    def __init__(
        self,
        *,
        calculation_id: str,
        calc_finished_event: anyio.Event,
        run_calc: BaseCalculation,
    ):
        super().__init__(calculation_id=calculation_id, calc_finished_event=calc_finished_event)
        self.run_calc = run_calc

    @property
    def status(self) -> CalculationStatusEnum:
        return CalculationStatusEnum.RUNNING

    @property
    async def stdout(self) -> None:
        return None

    @property
    async def stderr(self) -> None:
        return None

    async def wait_until_finished(self):
        logger.debug("TODO: implement wait_until_finished() for interactive commands!")
        await self.run_calc.wait_until_finished()
        logger.debug("[DDD] run_calculation finished!")
        # await anyio.sleep(15)


class InteractiveCommand(BaseCommand):
    def __init__(self, cmd_spec: InteractiveCommandSpec):
        assert cmd_spec.implemented_as == "interactive"
        super().__init__(cmd_spec)
        self.run_cmd_spec = cmd_spec.interactive_lifecycle.run

    async def execute_in_background(
        self,
        _calculation_id: str,
        _stdin=None,
        _stdout=None,
        _stderr=None,
        _cwd=None,
        **kwargs,
    ) -> InteractiveCmdCalculation:
        from .executable_command import ExecutableCommand

        calc_finished_event = anyio.Event()
        run_cmd = ExecutableCommand(self.run_cmd_spec)
        run_calc_id = helpers.generate_calculation_id()
        breakpoint()
        run_calc = await run_cmd.execute_in_background(_calculation_id=run_calc_id, _cwd=_cwd, **kwargs)

        return InteractiveCmdCalculation(
            calculation_id=_calculation_id,
            calc_finished_event=calc_finished_event,
            run_calc=run_calc,
        )

    def terminate(self):
        raise NotImplementedError("TODO: implement terminate() for interactive commands")

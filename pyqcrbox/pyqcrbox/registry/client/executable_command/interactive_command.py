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
        prepare_calc: BaseCalculation | None,
        run_calc: BaseCalculation,
        finalise_calc: BaseCalculation | None,
    ):
        super().__init__(calculation_id=calculation_id, calc_finished_event=calc_finished_event)
        self.prepare_calc = prepare_calc
        self.run_calc = run_calc
        self.finalise_calc = finalise_calc

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
        if self.prepare_calc:
            logger.debug("Running 'prepare' command")
            await self.prepare_calc.wait_until_finished()

        logger.debug("Running the main interactive command")
        await self.run_calc.wait_until_finished()

        if self.finalise_calc:
            logger.debug("Running the 'finalise' command")
            await self.finalise_calc.wait_until_finished()


class InteractiveCommand(BaseCommand):
    def __init__(self, cmd_spec: InteractiveCommandSpec):
        assert cmd_spec.implemented_as == "interactive"
        super().__init__(cmd_spec)
        self.prepare_cmd_spec = cmd_spec.interactive_lifecycle.prepare
        self.run_cmd_spec = cmd_spec.interactive_lifecycle.run
        self.finalise_cmd_spec = cmd_spec.interactive_lifecycle.finalise

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

        if self.prepare_cmd_spec:
            prepare_cmd = ExecutableCommand(self.prepare_cmd_spec)
            prepare_calc_id = helpers.generate_calculation_id()
            prepare_calc = await prepare_cmd.execute_in_background(_calculation_id=prepare_calc_id, _cwd=_cwd, **kwargs)
        else:
            prepare_calc = None

        run_cmd = ExecutableCommand(self.run_cmd_spec)
        run_calc_id = helpers.generate_calculation_id()
        run_calc = await run_cmd.execute_in_background(_calculation_id=run_calc_id, _cwd=_cwd, **kwargs)

        if self.finalise_cmd_spec:
            finalise_cmd = ExecutableCommand(self.finalise_cmd_spec)
            finalise_calc_id = helpers.generate_calculation_id()
            finalise_calc = await finalise_cmd.execute_in_background(_calculation_id=finalise_calc_id, _cwd=_cwd, **kwargs)
        else:
            finalise_calc = None

        return InteractiveCmdCalculation(
            calculation_id=_calculation_id,
            calc_finished_event=calc_finished_event,
            prepare_calc=prepare_calc,
            run_calc=run_calc,
            finalise_calc=finalise_calc,
        )

    def terminate(self):
        raise NotImplementedError("TODO: implement terminate() for interactive commands")

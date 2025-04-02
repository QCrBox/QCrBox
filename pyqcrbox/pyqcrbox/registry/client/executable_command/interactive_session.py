import os

import anyio

from pyqcrbox import helpers, logger
from pyqcrbox.registry.client.executable_command import BaseCommand
from pyqcrbox.sql_models import InteractiveSessionSpec

from .interactive_session_calculation import InteractiveSessionCalculation

__all__ = ["InteractiveSession"]


class InteractiveSession(BaseCommand):
    def __init__(self, cmd_spec: InteractiveSessionSpec):
        assert cmd_spec.implemented_as == "interactive_session"
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
    ) -> InteractiveSessionCalculation:
        from .executable_command import ExecutableCommand

        working_dir = _cwd or os.getcwd()

        # It is mandatory to have a run command defined, but optional to have a prepare or finalise command. So
        # we have to be careful here and add their parameters if they are defined.
        param_values = self.run_cmd_spec.parameter_default_values
        if self.prepare_cmd_spec:
            param_values = param_values | self.prepare_cmd_spec.parameter_default_values
        if self.finalise_cmd_spec:
            param_values = param_values | self.finalise_cmd_spec.parameter_default_values
        param_values = param_values | kwargs
        param_values = {
            name: await param.prepare_for_execution(target_dir=working_dir) for name, param in param_values.items()
        }
        logger.debug("InteractiveSession.execute_in_background: prepared parameters %s", param_values)

        calc_finished_event = anyio.Event()

        # TODO: we should also pass **kwargs. But let's pass the param_values, for now, and worry about it later.
        #       It probably requires us to pop any of the keys from kwargs that are also in param_values

        if self.prepare_cmd_spec:
            prepare_cmd = ExecutableCommand(self.prepare_cmd_spec)
            prepare_calc_id = helpers.generate_calculation_id()
            prepare_calc = await prepare_cmd.execute_in_background(
                _calculation_id=prepare_calc_id, _cwd=_cwd, **param_values
            )
            await prepare_calc.wait_until_finished()
        else:
            prepare_calc = None

        run_cmd = ExecutableCommand(self.run_cmd_spec)
        run_calc_id = helpers.generate_calculation_id()
        run_calc = await run_cmd.execute_in_background(_calculation_id=run_calc_id, _cwd=_cwd, **param_values)
        await run_calc.wait_until_finished()

        if self.finalise_cmd_spec:
            finalise_cmd = ExecutableCommand(self.finalise_cmd_spec)
            finalise_calc_id = helpers.generate_calculation_id()
            finalise_calc = await finalise_cmd.execute_in_background(
                _calculation_id=finalise_calc_id, _cwd=_cwd, **param_values
            )
        else:
            finalise_calc = None

        return InteractiveSessionCalculation(
            calculation_id=_calculation_id,
            calc_finished_event=calc_finished_event,
            prepare_calc=prepare_calc,
            run_calc=run_calc,
            finalise_calc=finalise_calc,
        )

    def terminate(self):
        raise NotImplementedError("TODO: implement terminate() for interactive commands")

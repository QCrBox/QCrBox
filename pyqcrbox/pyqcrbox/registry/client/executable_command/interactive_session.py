import os

import anyio

from pyqcrbox import helpers, logger
from pyqcrbox.registry.client.executable_command import BaseCommand
from pyqcrbox.registry.client.executable_command.python_callable import PythonCallable
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

        logger.debug("InteractiveSession: entered execute_in_background()")
        working_dir = _cwd or os.getcwd()
        calc_finished_event = anyio.Event()

        # It is mandatory to have a run command defined, but optional to have a prepare or finalise command. So
        # we have to be careful here and add their parameters only if they are defined.
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

        if self.prepare_cmd_spec:
            prepare_cmd = ExecutableCommand(self.prepare_cmd_spec)
            assert isinstance(
                prepare_cmd, PythonCallable
            ), "Only Python callables are supported for 'prepare_command' at the moment"
            prepare_calc_id = helpers.generate_calculation_id()
            logger.debug("Running 'prepare' command")
            prepare_calc = await prepare_cmd.execute_in_background(
                _calculation_id=prepare_calc_id, _cwd=_cwd, **param_values
            )
            await prepare_calc.wait_until_finished()
        else:
            prepare_calc = None

        run_cmd = ExecutableCommand(self.run_cmd_spec)
        run_calc_id = helpers.generate_calculation_id()
        logger.debug("Running the main interactive command")
        run_calc = await run_cmd.execute_in_background(_calculation_id=run_calc_id, _cwd=_cwd, **param_values)
        await run_calc.wait_until_finished()

        if self.finalise_cmd_spec:
            finalise_cmd = ExecutableCommand(self.finalise_cmd_spec)
            assert isinstance(
                finalise_cmd, PythonCallable
            ), "Only Python callables are supported for 'finalise_command' at the moment"
            finalise_calc_id = helpers.generate_calculation_id()
            logger.debug("Running the 'finalise' command")
            finalise_calc = await finalise_cmd.execute_in_background(
                _calculation_id=finalise_calc_id, _cwd=_cwd, **param_values
            )
        else:
            finalise_calc = None

        logger.debug("InteractiveSession: exiting execute_in_background() and returning calculation object")

        return InteractiveSessionCalculation(
            calculation_id=_calculation_id,
            calc_finished_event=calc_finished_event,
            prepare_calc=prepare_calc,
            run_calc=run_calc,
            finalise_calc=finalise_calc,
        )

    def terminate(self):
        raise NotImplementedError("TODO: implement terminate() for interactive commands")

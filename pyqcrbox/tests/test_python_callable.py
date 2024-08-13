import pytest

from pyqcrbox.registry.client.executable_command import PythonCallable
from pyqcrbox.registry.client.executable_command.calculation import CalculationStatusEnum


@pytest.mark.anyio
@pytest.mark.xfail
async def test_python_callable(sample_application_spec):
    app_spec = sample_application_spec
    cmd_spec = app_spec.commands[0]

    cmd = PythonCallable(cmd_spec)
    calc = await cmd.execute_in_background(name="Alice", duration="0.0", _calculation_id="qcrbox_calc_dummy")
    assert calc.status == CalculationStatusEnum.SUCCESSFUL

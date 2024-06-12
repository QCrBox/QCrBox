import pytest

from pyqcrbox.registry.client.executable_command import PythonCallable
from pyqcrbox.registry.client.executable_command.calculation import CalculationStatus


@pytest.mark.anyio
@pytest.mark.xfail
async def test_python_callable(sample_application_spec):
    app_spec = sample_application_spec
    cmd_spec = app_spec.commands[0]

    cmd = PythonCallable.from_command_spec(cmd_spec)
    calc = await cmd.execute_in_background(name="Alice", duration="0.0")
    assert calc.status == CalculationStatus.COMPLETED

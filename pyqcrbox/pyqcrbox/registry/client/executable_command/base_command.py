from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pyqcrbox.registry.client.executable_command.base_calculation import BaseCalculation

if TYPE_CHECKING:
    from pyqcrbox.sql_models import CommandSpecDiscriminatedUnion

__all__ = ["BaseCommand"]


class BaseCommand(metaclass=ABCMeta):
    def __init__(self, cmd_spec: "CommandSpecDiscriminatedUnion"):
        self.cmd_spec = cmd_spec

    def __repr__(self):
        clsname = self.__class__.__name__
        return f"<{clsname}: {self.cmd_spec.name!r}>"

    @abstractmethod
    async def execute_in_background(
        self,
        _calculation_id: str,
        _stdin: Any = None,
        _stdout: Any = None,
        _stderr: Any = None,
        _cwd: str | Path = None,
        **kwargs,
    ) -> BaseCalculation:
        pass

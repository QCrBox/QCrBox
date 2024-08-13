from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyqcrbox.sql_models_NEW_v2 import CommandSpecDiscriminatedUnion

__all__ = ["BaseCommand"]


class BaseCommand(metaclass=ABCMeta):
    def __init__(self, cmd_spec: "CommandSpecDiscriminatedUnion"):
        self.cmd_spec = cmd_spec

    def __repr__(self):
        clsname = self.__class__.__name__
        return f"<{clsname}: {self.cmd_spec.name!r}>"

    @abstractmethod
    async def terminate(self):
        pass

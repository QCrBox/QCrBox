from doit.cmd_base import TaskLoader2
from doit.doit_cmd import DoitMain
from doit.task import dict_to_task

__all__ = ["make_task", "run_tasks"]


def make_task(task_dict_func):
    """
    Wrapper to decorate functions returning pydoit `Task` dictionaries
    and have them return pydoit `Task` objects.
    """

    def d_to_t(*args, **kwargs):
        ret_dict = task_dict_func(*args, **kwargs)
        return dict_to_task(ret_dict)

    return d_to_t


class Loader(TaskLoader2):
    def __init__(self, tasks):
        super().__init__()
        if not isinstance(tasks, list):
            raise TypeError("tasks must be of type list.")
        self.tasks = tasks

    def load_doit_config(self):
        return {
            "verbosity": 2,
            "backend": "sqlite3",
            "reporter": "zero",
        }

    def load_tasks(self, cmd, pos_args):
        return self.tasks


def run_tasks(tasks):
    """
    Given a list of `Task` objects and a list of arguments, execute the tasks.
    """
    doitmain = DoitMain(Loader(tasks))
    res = doitmain.run(["run"])
    return res

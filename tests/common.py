import random
import shutil
import string

from qcrbox_wrapper import QCrBoxPathHelper


def with_temp_path_helper(func):
    """
    Decorator to create a temporary folder in the shared_folder of QCrBox and deleting
    the test subfolder after the test function has been run. Should enable the easy
    building and execution of tests using the QCrBox Wrapper.
    """

    def inner(*args, **kwargs):
        try:
            random_name = "".join(random.choice(string.ascii_lowercase) for _ in range(7))
            test_folder_relative = f"tests_qcrbox/{random_name}"
            path_helper = QCrBoxPathHelper.from_dotenv(".env.dev", test_folder_relative)
            func(path_helper, *args, **kwargs)
        except Exception as exc:
            raise exc
        finally:
            shutil.rmtree(path_helper.local_path)

    return inner

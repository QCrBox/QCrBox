import shutil
import os
from dotenv import load_dotenv
from pathlib import Path, PurePosixPath
import pytest
from .qcrbox_wrapper import QCrBoxWrapper
import random
import string


load_dotenv(Path(__file__).parents[1] / '.env.dev')
FILEPATH = Path(__file__).parent / 'test_files_olex'

def with_temp_shared_folder(func):
    def inner(*args, **kwargs):
        try:
            shared_folder = Path(os.environ['QCRBOX_SHARED_FILES_DIR_HOST_PATH'])
            if not shared_folder.is_absolute():
                shared_folder = Path(__file__).parents[1] / shared_folder
            random_name = ''.join(random.choice(string.ascii_lowercase) for _ in range(5))
            test_folder = shared_folder / 'tests_qcrbox' / random_name
            test_folder.mkdir(parents=True)
            func(test_folder, *args, **kwargs)
        except Exception as exc:
            raise exc
        finally:
            pass
            #shutil.rmtree(test_folder)
    return inner

@pytest.mark.serial
@with_temp_shared_folder
def test_refine_iam(tmp_shared_folder):
    input_cif_path = tmp_shared_folder / 'input.cif'
    internal_shared_folder = PurePosixPath('/mnt/qcrbox/shared_files/tests_qcrbox/') / tmp_shared_folder.name
    shutil.copy(FILEPATH / 'refine_nonconv_allaniso.cif', input_cif_path)

    port_dict = {'Olex2 (Linux)': 12004}
    gui_commands = [('Olex2 (Linux)', 'interactive')]
    qcrbox = QCrBoxWrapper('localhost', 11000, port_dict, gui_commands)
    olex2 = qcrbox.application_dict['Olex2 (Linux)']

    calc = olex2.refine_iam(
        cif_path=internal_shared_folder / 'input.cif',
        ls_cycles='20',
        weight_cycles='5'
    )

    calc.wait_while_running(1.0)

    assert calc.status.status == 'completed'

@pytest.mark.serial
@with_temp_shared_folder
def test_refine_tsc(tmp_shared_folder):
    shutil.copy(FILEPATH / 'refine_nonconv_nonHaniso.cif', tmp_shared_folder / 'input.cif')
    shutil.copy(FILEPATH / 'refine_allaniso.tscb',  tmp_shared_folder / 'input.tscb')

    internal_shared_folder = PurePosixPath('/mnt/qcrbox/shared_files/tests_qcrbox/') / tmp_shared_folder.name

    port_dict = {'Olex2 (Linux)': 12004}
    gui_commands = [('Olex2 (Linux)', 'interactive')]
    qcrbox = QCrBoxWrapper('localhost', 11000, port_dict, gui_commands)
    olex2 = qcrbox.application_dict['Olex2 (Linux)']

    calc = olex2.refine_tsc(
        cif_path=internal_shared_folder / 'input.cif',
        tsc_path=internal_shared_folder / 'input.tscb',
        ls_cycles='20',
        weight_cycles='5'
    )

    calc.wait_while_running(1.0)

    assert calc.status.status == 'completed'

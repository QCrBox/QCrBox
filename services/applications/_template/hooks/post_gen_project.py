import os
import shutil


def remove_dummy_gui_for_non_interactive():
    app_type = "{{ cookiecutter.application_type }}"
    if not app_type.startswith("Interactive GUI"):
        path = "dummy_gui.py"
        if os.path.exists(path):
            os.remove(path)
        idesktop_path = '.idesktop'
        if os.path.exists(idesktop_path):
            shutil.rmtree(idesktop_path)


if __name__ == "__main__":
    remove_dummy_gui_for_non_interactive()

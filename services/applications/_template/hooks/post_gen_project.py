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


def create_private_build_sentinel():
    if "{{ cookiecutter.requires_private_installer }}" != "yes":
        return
    slug = "{{ cookiecutter.application_slug }}"
    content = f"""\
# Marks this app as requiring a private installer that cannot be distributed.
# Place the file(s) listed below in this directory before building.
# See docs/how_to_guides/obtain_licenced_components.md for the general pattern.
requires:
  - filename: REPLACE_WITH_INSTALLER_FILENAME
    description: "REPLACE_WITH_DESCRIPTION — obtain from REPLACE_WITH_SOURCE (licence required)"
"""
    with open("private_build.yml", "w") as f:
        f.write(content)
    print(f"Created private_build.yml for {slug} — remember to:")
    print("  1. Fill in the filename and description in private_build.yml")
    print("  2. Add the installer filename to the root .gitignore to avoid committing it")


if __name__ == "__main__":
    remove_dummy_gui_for_non_interactive()
    create_private_build_sentinel()

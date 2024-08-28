import pathlib
import shutil
import urllib.request
import webbrowser
import zipfile
from pathlib import Path
from textwrap import dedent

from nicegui import ui
from qcrbox_wrapper import QCrBoxPathHelper, QCrBoxWrapper


class QCrBoxInteractiveHelper:
    started_run = False
    finalised_run = False
    current_arguments = None

    def __init__(
        self, wrapper: QCrBoxWrapper, application_name: str, helper: QCrBoxPathHelper, application_dir: pathlib.Path
    ):
        print(f"Application: {application_name}")
        self.wrapper = wrapper
        self.application = wrapper.application_dict[application_name]
        #self.command = application.interactive
        self.pathhelper = helper
        self.application_dir = application_dir
        print(f"Application: {self.application}")
        self.session = None


    @property
    def local_app_dir(self):
        return self.pathhelper.local_path / self.application_dir

    @property
    def qcrbox_app_dir(self):
        return self.pathhelper.qcrbox_path / self.application_dir

    def start_interactive(self, *args, **kwargs):
        self.finalised_run = False
        #arguments = self.command.args_to_kwargs(*args, **kwargs)

        try:
            self.session = self.application.interactive_session(*args, **kwargs)
        except Exception as e:
            ui.notify(f"Error: {e}")
            return None
        try:
            self.session.start()
        except Exception as e:
            ui.notify(f"Error: {e}")
            return None
        self.started_run = True
        #webbrowser.open(self.command.gui_url)

    def finalise(self):
        try:
            self.session.close()
        except Exception as e:
            ui.notify(f"Error: {e}")
            return None
        self.finalised_run = True


pathhelper = QCrBoxPathHelper.from_dotenv(".env.dev", "gui_folder/prototype1")

#pathhelper.local_path.mkdir(exist_ok=True, parents=True)

qcrbox = QCrBoxWrapper.from_server_addr("127.0.0.1", 11000)

cryspro = QCrBoxInteractiveHelper(qcrbox, "CrysalisPro", pathhelper, "step1_cryspro")

olex2 = QCrBoxInteractiveHelper(qcrbox, "Olex2 (Linux)", pathhelper, "step2_olex2")

crystal_explorer = QCrBoxInteractiveHelper(qcrbox, "Crystal Explorer", pathhelper, "step3_crystal_explorer")


def click_btn_cap_start():
    cryspro.start_interactive(
        par_path=cryspro.qcrbox_app_dir / "Ylid_Mo_RT" / "Ylid_Mo_RT.run",
        work_folder=cryspro.qcrbox_app_dir / "Ylid_Mo_RT",
        output_cif_path=cryspro.qcrbox_app_dir / "output.cif",
    )


def click_btn_cap_finalise():
    cryspro.finalise()


def click_btn_olex2_start():
    if not olex2.local_app_dir.exists():
        olex2.local_app_dir.mkdir()
    shutil.copy(cryspro.local_app_dir / "output.cif", olex2.local_app_dir / "input.cif")
    olex2.start_interactive(
        input_cif_path=olex2.qcrbox_app_dir / "input.cif",
        work_cif_path=olex2.qcrbox_app_dir / "work.cif",
        output_cif_path=olex2.qcrbox_app_dir / "output.cif",
    )


def click_btn_olex2_finalise():
    olex2.finalise()


def click_btn_cryst_exp_start():
    if not crystal_explorer.local_app_dir.exists():
        crystal_explorer.local_app_dir.mkdir()
    shutil.copy(olex2.local_app_dir / "output.cif", crystal_explorer.local_app_dir / "input.cif")
    crystal_explorer.start_interactive(
        input_cif_path=crystal_explorer.qcrbox_app_dir / "input.cif",
        work_cif_path=crystal_explorer.qcrbox_app_dir / "work.cif",
    )


def click_btn_setup():
    for application in [cryspro, olex2, crystal_explorer]:
        application.started_run = False
        application.finalised_run = False

    btn_cap_start.enabled = False
    qcrbox_basedir = Path(__file__).parents[1]
    frames_zip = qcrbox_basedir / "docs/tutorials/examples/input_files/Ylid_Mo_RT.zip"
    if not frames_zip.exists():
        url = f"https://github.com/QCrBox/QCrBoxExamples/raw/main/CrysAlisPro/{frames_zip.name}"
        urllib.request.urlretrieve(url, frames_zip)

    work_folder_empty = not any(pathhelper.local_path.iterdir())

    if not work_folder_empty:
        shutil.rmtree(pathhelper.local_path)
        pathhelper.local_path.mkdir()

    cryspro_dir = pathhelper.local_path / "step1_cryspro"
    cryspro_dir.mkdir()

    with zipfile.ZipFile(frames_zip, "r") as zip_ref:
        zip_ref.extractall(cryspro_dir)

    btn_cap_start.enabled = True


btn_setup = ui.button("Delete data in and freshly setup work folder", on_click=click_btn_setup)

ui.markdown(
    dedent(
        f"""
        # QCrBox GUI Prototype 1

        This is a prototype for developing the interaction of QCrBox with a GUI.

        The work directory is `{pathhelper.local_path}`
    """
    ).strip()
)
with ui.grid(columns=2):
    btn_cap_start = ui.button("Start interactive CrysAlisPro", on_click=click_btn_cap_start)
    btn_cap_finalise = ui.button("Collect data from interactive session", on_click=click_btn_cap_finalise)
    btn_cap_finalise.bind_enabled_from(cryspro, "started_run")

    btn_olex2_start = ui.button("Start interactive Olex2", on_click=click_btn_olex2_start)
    btn_olex2_start.bind_enabled_from(cryspro, "finalised_run")

    btn_olex2_finalise = ui.button("Collect data from interactive session", on_click=click_btn_olex2_finalise)
    btn_olex2_finalise.bind_enabled_from(olex2, "started_run")

    btn_cryst_exp_start = ui.button("Start interactive CrystalExplorer", on_click=click_btn_cryst_exp_start)
    btn_cryst_exp_start.bind_enabled_from(olex2, "finalised_run")
print("blablabla")
ui.run(port=9191)

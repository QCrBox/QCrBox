import pathlib
import shutil
import webbrowser
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
        self.wrapper = wrapper
        application = wrapper.application_dict[application_name]
        self.command = application.interactive
        self.pathhelper = helper
        self.application_dir = application_dir

    @property
    def local_app_dir(self):
        return self.pathhelper.local_path / self.application_dir

    @property
    def qcrbox_app_dir(self):
        return self.pathhelper.qcrbox_path / self.application_dir

    def start_interactive(self, *args, **kwargs):
        self.finalised_run = False
        arguments = self.command.args_to_kwargs(*args, **kwargs)

        arguments = self.command.execute_prepare(arguments)
        _, arguments = self.command.execute_run(arguments)
        self.current_arguments = arguments
        self.started_run = True
        webbrowser.open(self.command.gui_url)

    def finalise(self):
        self.command.execute_finalise(self.current_arguments)
        self.finalised_run = True


pathhelper = QCrBoxPathHelper.from_dotenv(".env.dev", "gui_folder")

qcrbox = QCrBoxWrapper("127.0.0.1", 11000)

cryspro = QCrBoxInteractiveHelper(qcrbox, "CrysalisPro", pathhelper, "step1_cryspro")

olex2 = QCrBoxInteractiveHelper(qcrbox, "Olex2 (Linux)", pathhelper, "step2_olex2")

crystal_explorer = QCrBoxInteractiveHelper(qcrbox, "CrystalExplorer", pathhelper, "step3_crystal_explorer")


def click_btn_cap_start():
    cryspro.start_interactive(
        par_path=cryspro.qcrbox_app_dir / "Ylid_Mo_RT" / "Ylid_Mo_RT.run",
        work_folder=cryspro.qcrbox_app_dir / "Ylid_Mo_RT",
        output_cif_path=cryspro.qcrbox_app_dir / "output.cif",
    )


def click_btn_cap_finalise():
    cryspro.finalise()
    if not olex2.local_app_dir.exists():
        olex2.local_app_dir.mkdir()
    shutil.copy(cryspro.local_app_dir / "output.cif", olex2.local_app_dir / "input.cif")


def click_btn_olex2_start():
    olex2.start_interactive(
        input_cif_path=olex2.qcrbox_app_dir / "input.cif",
        output_cif_path=olex2.qcrbox_app_dir / "output.cif",
    )


def click_btn_olex2_finalise():
    olex2.finalise()
    if not crystal_explorer.local_app_dir.exists():
        crystal_explorer.local_app_dir.mkdir()
    shutil.copy(olex2.local_app_dir / "output.cif", crystal_explorer.local_app_dir / "input.cif")


def click_btn_cryst_exp_start():
    crystal_explorer.start_interactive(
        input_cif_path=crystal_explorer.qcrbox_app_dir / "input.cif",
    )


ui.markdown(
    dedent(
        """
        # QCrBox GUI Prototype 1

        This is a prototype for developing the interaction of QCrBox with a GUI. Task 1: Three interactive tasks.
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

ui.run()

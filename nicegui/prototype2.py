import shutil
from pathlib import Path
from textwrap import dedent

from nicegui import ui
from qcrbox_wrapper import QCrBoxPathHelper, QCrBoxWrapper


class QCrBoxHelper:
    executed = False

    def __init__(self, wrapper, application_name, command_name, helper, application_dir):
        self.wrapper = wrapper
        application = wrapper.application_dict[application_name]
        self.command = getattr(application, command_name)
        self.pathhelper = helper
        self.application_dir = application_dir

    @property
    def local_app_dir(self):
        return self.pathhelper.local_path / self.application_dir

    @property
    def qcrbox_app_dir(self):
        return self.pathhelper.qcrbox_path / self.application_dir

    def execute(self, *args, **kwargs):
        try:
            calculation = self.command(*args, **kwargs)
            calculation.wait_while_running(0.5)
        except Exception as e:
            ui.notify(f"Error: {e}")
            return None
        self.executed = True


# class QCrBoxCommandUI:
#    def __init__(self, command, type_dict):
#        self.command = command
#        self.type_dict = type_dict

pathhelper = QCrBoxPathHelper.from_dotenv(".env.dev", "gui_folder/prototype2")

qcrbox = QCrBoxWrapper("127.0.0.1", 11000)

cod_merge_structure = QCrBoxHelper(
    qcrbox, "COD Check", "merge_closest_cod_entry", pathhelper, "step1_cod_merge_structure"
)

olex2_refine_iam = QCrBoxHelper(qcrbox, "Olex2 (Linux)", "refine_iam", pathhelper, "step2_olex2_refine_iam")


def click_btn_setup():
    for command in [cod_merge_structure, olex2_refine_iam]:
        command.executed = False

    btn_cod_merge.enabled = False

    work_folder_empty = not any(pathhelper.local_path.iterdir())

    if not work_folder_empty:
        shutil.rmtree(pathhelper.local_path)
        pathhelper.local_path.mkdir()

    qcrbox_basedir = Path(__file__).parents[1]
    example_cif = qcrbox_basedir / "docs/tutorials/examples/input_files/cap_result.cif"

    cod_dir = pathhelper.local_path / "step1_cod_merge_structure"
    cod_dir.mkdir()

    shutil.copy(example_cif, cod_dir / "input.cif")

    btn_cod_merge.enabled = True


def click_btn_cod_merge():
    cod_merge_structure.execute(
        input_cif_path=cod_merge_structure.qcrbox_app_dir / "input.cif",
        output_cif_path=cod_merge_structure.qcrbox_app_dir / "output.cif",
        listed_elements_only=not tgl_cod_additional_elements.value,
        cellpar_deviation_perc=sdr_cod_cell_deviation.value,
    )


def click_btn_olex2_refine():
    if not olex2_refine_iam.local_app_dir.exists():
        olex2_refine_iam.local_app_dir.mkdir()
    shutil.copy(cod_merge_structure.local_app_dir / "output.cif", olex2_refine_iam.local_app_dir / "input.cif")
    olex2_refine_iam.execute(
        input_cif_path=olex2_refine_iam.qcrbox_app_dir / "input.cif",
        output_cif_path=olex2_refine_iam.qcrbox_app_dir / "output.cif",
        ls_cycles=sdr_olex2_refine_cycles.value,
        weight_cycles=sdr_olex2_weight_cycles.value,
    )


btn_setup = ui.button("Delete data in and freshly setup work folder", on_click=click_btn_setup)

ui.markdown(
    dedent(
        f"""
        # QCrBox GUI Prototype 2

        This is a prototype for developing the interaction of QCrBox with a non-GUI components.

        The work directory is `{pathhelper.local_path}`

        ## Step 1: Merge structure with closest from the Crystallographic Open Database (COD)
    """
    ).strip()
)

with ui.grid(columns=3):
    ui.label("Additional elements to the one in CIF file possible:")
    with ui.row():
        tgl_cod_additional_elements = ui.toggle({True: "Yes", False: "No"}, value=False)
        ui.space()
    ui.space()
    ui.label("Maximum cell parameter deviation (%):")
    sdr_cod_cell_deviation = ui.slider(min=0, max=30, value=5)
    ui.label().bind_text_from(sdr_cod_cell_deviation, "value")


btn_cod_merge = ui.button("Merge structure", on_click=click_btn_cod_merge)


ui.markdown("## Step 2: Refine structure with Olex2")

with ui.grid(columns=3):
    ui.label("Number of refinement cycles:")
    sdr_olex2_refine_cycles = ui.slider(min=1, max=40, value=10)
    ui.label().bind_text_from(sdr_olex2_refine_cycles, "value")

    ui.label("Number of weight cycles (each with N refinement cycles):")
    sdr_olex2_weight_cycles = ui.slider(min=1, max=10, value=1)
    ui.label().bind_text_from(sdr_olex2_weight_cycles, "value")

btn_olex2_refine = ui.button("Refine structure", on_click=click_btn_olex2_refine)
btn_olex2_refine.bind_enabled_from(cod_merge_structure, "executed")

ui.run()

import json
import shutil
import webbrowser
from textwrap import dedent

from mock_can_run_wrapper import MockWrapper as QCrBoxWrapper

from nicegui import ui
from qcrbox_wrapper import QCrBoxPathHelper

# import time


def load_textbox_values(command):
    try:
        other_arguments = json.loads(textarea_settings.value)
    except json.JSONDecodeError:
        ui.notify("Invalid JSON")
        return None
    handled = set(("input_cif_path", "output_cif_path", "work_cif_path"))
    present = set(other_arguments.keys())

    needed = set(command.par_name_list) - handled - present

    if len(needed) > 0:
        ui.notify(f"Missing arguments: {needed}")
        return None

    return other_arguments


def create_cif_paths(input_cif_path, command):
    # raw_path = pathhelper.path_to_qcrbox(f"{input_cif_path}")
    blank_path = input_cif_path.with_suffix("")
    arguments = {}
    if "input_cif_path" in command.par_name_list:
        arguments["input_cif_path"] = input_cif_path
    if "output_cif_path" in command.par_name_list:
        arguments["output_cif_path"] = input_cif_path.with_name(blank_path.name + "_output.cif")
    if "work_cif_path" in command.par_name_list:
        arguments["work_cif_path"] = input_cif_path.with_name(blank_path.name + "_work.cif")
    return arguments


class BaseCommandGuiRepresentation:
    def __init__(self, command):
        self.command = command
        self.name_label = ui.label(self.command.name)
        self.application_label = ui.label(self.command.application_name)
        self.settings_template_button = ui.button("Settings Template", on_click=self.settings_template_on_click)
        self.execute_button = ui.button("Execute", on_click=self.execute_on_click)

    def settings_template_on_click(self):
        template = "{\n"
        for parameter in self.command.parameters:
            if parameter.name not in ("input_cif_path", "output_cif_path", "work_cif_path"):
                template += f'  "{parameter.name}" : ,\n'
        template += "}"
        textarea_settings.value = template

    def execute_on_click(self): ...


class CommandGuiRepresentation(BaseCommandGuiRepresentation):
    def execute_on_click(self):
        arguments = create_cif_paths(path_storage["qcrbox_path"], self.command)

        other_arguments = load_textbox_values(self.command)

        if other_arguments is None:
            return

        arguments.update(other_arguments)
        try:
            calculation = self.command(**arguments)
            calculation.wait_while_running(0.5)
        except Exception as e:
            ui.notify(f"Error: {e}")
            return
        ui.notify("Calculation finished")
        load_cif_file()


class InteractiveCommandGuiRepresentation(BaseCommandGuiRepresentation):
    started_run = False
    finalised_run = False
    current_arguments = None

    def execute_on_click(self):
        if not self.started_run or self.finalised_run:
            self.run()
            self.execute_button.set_text("Get Results")
        else:
            self.finalise()
            self.execute_button.set_text("Execute")

    def run(self):
        arguments = create_cif_paths(path_storage["qcrbox_path"], self.command)

        other_arguments = load_textbox_values(self.command)

        if other_arguments is None:
            return

        try:
            self.command.execute_prepare(arguments)
        except Exception as e:
            ui.notify(f"Error: {e}")
            return None
        try:
            _ = self.command.execute_run(arguments)
        except Exception as e:
            ui.notify(f"Error: {e}")
            return None
        self.current_arguments = arguments
        self.started_run = True
        webbrowser.open(self.command.gui_url)

    def finalise(self):
        try:
            self.command.execute_finalise(self.current_arguments)
        except Exception as e:
            ui.notify(f"Error: {e}")
            return None
        self.finalised_run = True
        load_cif_file()


def repopulate_grid():
    grid.clear()
    steering_commands = ("finalise__", "prepare__", "run__", "redo__", "toparams__")
    with grid:
        for command in qcrbox.commands:
            if any(command.name.startswith(val) for val in steering_commands):
                continue
            if not command.can_run(path_storage["local_path"]):
                continue
            if hasattr(command, "gui_url"):
                _ = InteractiveCommandGuiRepresentation(command)
            else:
                _ = CommandGuiRepresentation(command)


def load_cif_file():
    original_input = path_storage["local_path"]
    blank_path = original_input.with_suffix("")
    copy_cif_path = original_input.with_name(blank_path.name + "_output.cif")
    local_folder_path, qcrbox_folder_path = pathhelper.create_next_step_folder()
    local_path = local_folder_path / "input.cif"
    qcrbox_path = qcrbox_folder_path / "input.cif"

    shutil.copy(copy_cif_path, local_path)

    path_storage["local_path"] = local_path
    path_storage["qcrbox_path"] = qcrbox_path

    repopulate_grid()

    location_label.set_text(f"The current input cif is at `{local_path}` from previous calculation")


def upload_cif_file(uploader_event):
    local_folder_path, qcrbox_folder_path = pathhelper.create_next_step_folder()
    local_path = local_folder_path / "input.cif"
    qcrbox_path = qcrbox_folder_path / "input.cif"

    local_path.write_bytes(uploader_event.content.read())

    path_storage["local_path"] = local_path
    path_storage["qcrbox_path"] = qcrbox_path

    repopulate_grid()

    location_label.set_text(f"The current input cif is at `{local_path}` from file upload")


pathhelper = QCrBoxPathHelper.from_dotenv(".env.dev", "gui_folder/prototype3")

# pathhelper = QCrBoxPathHelper(Path(__file__).parents[1] / "shared_files", base_dir="gui_folder/prototype3")

path_storage = {"local_path": None, "qcrbox_path": None}
qcrbox = QCrBoxWrapper("127.0.0.1", 11000)

cif_names = ["01_reduced.cif", "02_converged.cif", "03_notconverged.cif"]

ui.markdown(
    dedent(
        """
        # QCrBox GUI Prototype 3

        This is a prototype for developing the interaction of QCrBox with a non-GUI components.
        """
    ).strip()
)
location_label = ui.label("Currently no cif file is loaded")

ui.markdown("## Upload a dataset")

ui.upload(on_upload=upload_cif_file, auto_upload=True)

ui.markdown("## Input settings in JSON format")

textarea_settings = ui.textarea()

ui.markdown("## Available commands")

grid = ui.grid(columns=4)

ui.run()

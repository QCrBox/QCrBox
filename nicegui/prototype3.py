from mock_can_run_wrapper import MockWrapper as QCrBoxWrapper
from qcrbox_wrapper import QCrBoxPathHelper
from nicegui import ui
from textwrap import dedent
import json
import webbrowser

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
    raw_path = pathhelper.path_to_qcrbox(f"{input_cif_path}")
    arguments = {}
    if "input_cif_path" in command.par_name_list:
        arguments["input_cif_path"] = pathhelper.path_to_qcrbox(raw_path)
    if "output_cif_path" in command.par_name_list:
        arguments["output_cif_path"] = raw_path.with_name(raw_path.name + "_output.cif")
    if "work_cif_path" in command.par_name_list:
        arguments["work_cif_path"] = raw_path.with_name(raw_path.name + "_work.cif")
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

    def execute_on_click(self):
        ...

class CommandGuiRepresentation(BaseCommandGuiRepresentation):
    def execute_on_click(self):
        arguments = create_cif_paths(select_dataset.value, self.command)

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
        arguments = create_cif_paths(select_dataset.value, self.command)

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

def select_dataset_changed(input_cif):
    local_path = pathhelper.path_to_local(input_cif.value)
    grid.clear()
    steering_commands = ("finalise__", "prepare__", "run__", "redo__", "toparams__")
    with grid:
        for command in qcrbox.commands:
            if any(command.name.startswith(val) for val in steering_commands):
                continue
            if not command.can_run(local_path):
                continue
            if hasattr(command, "gui_url"):
                representation = InteractiveCommandGuiRepresentation(command)
            else:
                representation = CommandGuiRepresentation(command)
            representation.name_label
            representation.application_label
            representation.settings_template_button
            representation.execute_button


pathhelper = QCrBoxPathHelper.from_dotenv(".env.dev", "gui_folder/prototype3")

qcrbox = QCrBoxWrapper("127.0.0.1", 11000)

cif_names = ["01_reduced.cif", "02_converged.cif", "03_notconverged.cif"]

ui.markdown(
    dedent(
        f"""
        # QCrBox GUI Prototype 3

        This is a prototype for developing the interaction of QCrBox with a non-GUI components.

        The work directory is `{pathhelper.local_path}`

        ## Select a dataset
    """
    ).strip()
)
select_dataset = ui.select(cif_names, on_change=select_dataset_changed, value=cif_names[0])

ui.markdown("## Input settings in JSON format")

textarea_settings = ui.textarea()

ui.markdown("## Available commands")

grid = ui.grid(columns=4)

select_dataset_changed(select_dataset)

ui.run()
import json
import os
import shutil
import stat
import webbrowser
from pathlib import Path, PurePosixPath
from textwrap import dedent
from zipfile import ZipFile

from mock_can_run_wrapper import MockCommand as QCrBoxCommand
from mock_can_run_wrapper import MockWrapper as QCrBoxWrapper

from nicegui import events, run, ui
from qcrbox_wrapper import QCrBoxPathHelper

# import time


def upload_cif(event_fobj, local_folder_path, base_name="input.cif"):
    local_path = local_folder_path / base_name
    local_path.write_bytes(event_fobj.read())


def upload_zip(event_fobj, local_folder_path):
    with ZipFile(event_fobj) as zip_file:
        zip_file.extractall(local_folder_path)


class GuiState:
    local_output_cif_path = None

    def __init__(self, local_save_path: Path, qcrbox_save_path: PurePosixPath): ...

    def populate_parameters(self, command: QCrBoxCommand): ...


#####            GUI states for different types of loaded files            #####


class CifLoadedGuiState(GuiState):
    def __init__(self, local_save_path: Path, qcrbox_save_path: PurePosixPath):
        self.local_save_path = local_save_path
        self.qcrbox_save_path = qcrbox_save_path
        self.local_output_cif_path = self.local_save_path.with_name("output.cif")

    def populate_parameters(self, command: QCrBoxCommand):
        parameters = command.par_name_list

        filled_values = {}

        if "input_cif_path" in parameters:
            filled_values["input_cif_path"] = self.qcrbox_save_path
        if "output_cif_path" in parameters:
            filled_values["output_cif_path"] = self.qcrbox_save_path.with_name("output.cif")
        if "work_cif_path" in parameters:
            filled_values["work_cif_path"] = self.qcrbox_save_path.with_name("work.cif")

        remaining_parameters = set(parameters) - set(filled_values.keys())

        return filled_values, tuple(remaining_parameters)

    def description(self):
        return f"Current input cif is at {self.local_save_path}"


class CAPNoParException(Exception):
    pass


class CAPLoadedGuiState(GuiState):
    def __init__(self, local_save_path: Path, qcrbox_save_path: PurePosixPath):
        self.local_save_path = Path(local_save_path)
        self.qcrbox_save_path = qcrbox_save_path

        self.par_file = self._find_par_file()
        self.work_folder = self.par_file.parent

        self.local_output_cif_path = self.local_save_path / "output.cif"

    def _find_par_file(self):
        par_files = list(self.local_save_path.glob("**/*.par"))
        if len(par_files) == 0:
            raise CAPNoParException("No .par file found in the folder")

        # backups might be in subfolders so we need to find the shortest path
        min_depth = min(par_files, key=lambda x: len(x.parts))
        candidates = (par_file for par_file in par_files if len(par_file.parts) == len(min_depth.parts))

        # routines will attach names so we use the shortest name
        local_path = min(candidates, key=lambda x: len(x.name))
        return self.qcrbox_save_path / local_path.relative_to(self.local_save_path)

    def populate_parameters(self, command: QCrBoxCommand):
        parameters = command.par_name_list

        filled_values = {}

        if "work_folder" in parameters:
            filled_values["work_folder"] = self.work_folder
        if "par_path" in parameters:
            filled_values["par_path"] = self.par_file
        if "output_cif_path" in parameters:
            filled_values["output_cif_path"] = self.qcrbox_save_path / "output.cif"

        remaining_parameters = set(parameters) - set(filled_values.keys())
        return filled_values, tuple(remaining_parameters)

    def description(self):
        return f"Current input is a CrysalisPro folder at {self.local_save_path}"


class GenericFolderGuiState(GuiState):
    def __init__(self, local_save_path: Path, qcrbox_save_path: PurePosixPath):
        self.local_save_path = local_save_path
        self.qcrbox_save_path = qcrbox_save_path
        self.local_output_cif_path = self.local_save_path / "output.cif"

    def populate_parameters(self, command: QCrBoxCommand):
        parameters = command.par_name_list

        filled_values = {}

        if "work_folder" in parameters:
            filled_values["work_folder"] = self.qcrbox_save_path
        if "output_cif_path" in parameters:
            filled_values["output_cif_path"] = self.qcrbox_save_path / "output.cif"

        return filled_values, tuple(parameters)

    def description(self):
        return f"Current input is a folder at {self.local_save_path}"


class StartGuiState(GuiState):
    def __init__(self):
        self.local_save_path = None
        self.qcrbox_save_path = None
        self.local_output_cif_path = None

    def populate_parameters(self, command: QCrBoxCommand):
        return {}, command.par_name_list

    def description(self):
        return "No file loaded"


def load_textbox_values(command):
    try:
        other_arguments = json.loads(textarea_settings.value)
    except json.JSONDecodeError:
        ui.notify("Invalid JSON")
        return None
    handled = set(states[-1].populate_parameters(command)[0].keys())
    present = set(other_arguments.keys())

    needed = set(command.par_name_list) - handled - present

    if len(needed) > 0:
        ui.notify(f"Missing arguments: {needed}")
        return None

    return other_arguments


class BaseCommandGuiRepresentation:
    def __init__(self, command):
        self.command = command
        self.name_label = ui.label(self.command.name)
        self.application_label = ui.label(self.command.application_name)
        self.settings_template_button = ui.button("Settings Template", on_click=self.settings_template_on_click)
        self.execute_button = ui.button("Execute", on_click=self.execute_on_click)

    def settings_template_on_click(self):
        template = "{\n"
        _, remaining_parameters = states[-1].populate_parameters(self.command)
        template += ",\n".join(remaining_parameters)
        template += "\n}"
        textarea_settings.value = template

    def execute_on_click(self): ...


class CommandGuiRepresentation(BaseCommandGuiRepresentation):
    def execute_on_click(self):
        arguments, _ = states[-1].populate_parameters(self.command)

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
        arguments, _ = states[-1].populate_parameters(self.command)

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
            if isinstance(states[-1], CifLoadedGuiState):
                ## TODO later this cannot be a local path
                if not command.can_run(states[-1].local_save_path):
                    continue
            else:
                if "input_cif_path" in command.par_name_list:
                    continue
            if hasattr(command, "gui_url"):
                _ = InteractiveCommandGuiRepresentation(command)
            else:
                _ = CommandGuiRepresentation(command)


def load_cif_file():
    last_state = states[-1]
    local_folder_path, qcrbox_folder_path = pathhelper.create_next_step_folder()
    local_path = local_folder_path / "input.cif"
    qcrbox_path = qcrbox_folder_path / "input.cif"

    shutil.copy(last_state.local_output_cif_path, local_path)

    states.append(CifLoadedGuiState(local_path, qcrbox_path))

    repopulate_grid()

    location_label.set_text(states[-1].description())


async def upload_file(uploader_event_args: events.UploadEventArguments):
    local_folder_path, qcrbox_folder_path = pathhelper.create_next_step_folder()
    local_path = local_folder_path / uploader_event_args.name
    qcrbox_path = qcrbox_folder_path / uploader_event_args.name

    if uploader_event_args.name.lower().endswith(".cif"):
        upload_cif(uploader_event_args.content, local_folder_path, "input.cif")
        local_path = local_folder_path / "input.cif"
        qcrbox_path = qcrbox_folder_path / "input.cif"
        states.append(CifLoadedGuiState(local_path, qcrbox_path))

    elif uploader_event_args.name.lower().endswith(".zip"):
        unzip_overlay = Overlay("Unzipping the file")
        unzip_overlay.show()
        await run.io_bound(upload_zip, uploader_event_args.content, local_folder_path)
        try:
            states.append(CAPLoadedGuiState(local_folder_path, qcrbox_folder_path))
        except CAPNoParException:
            states.append(GenericFolderGuiState(local_folder_path, qcrbox_folder_path))
        unzip_overlay.hide()

    repopulate_grid()

    location_label.set_text(states[-1].description())


def delete_workfolder_data():
    work_folder_empty = not any(pathhelper.local_path.iterdir())
    if not work_folder_empty:

        def remove_readonly(func, path, _):
            "Clear the readonly bit and reattempt the removal"
            os.chmod(path, stat.S_IWRITE)
            func(path)

        try:
            shutil.rmtree(pathhelper.local_path, onerror=remove_readonly)
        except TypeError:
            shutil.rmtree(pathhelper.local_path, onerror=remove_readonly)
        pathhelper.local_path.mkdir()


async def click_btn_setup():
    workfolder_overlay = Overlay("Mercilessly deleting all data in the work folder")
    workfolder_overlay.show()
    await run.io_bound(delete_workfolder_data)
    states.clear()
    states.append(StartGuiState())
    workfolder_overlay.hide()
    repopulate_grid()
    location_label.set_text(states[-1].description())


class Overlay(ui.element):
    """Copied from https://github.com/zauberzeug/nicegui/discussions/2994"""

    def __init__(self, message, bg_color=(0, 0, 0, 0.5)):
        super().__init__(tag="div")
        self.message = message
        self.style(
            "position: fixed; display: block; width: 100%; height: 100%;"
            "top: 0; left: 0; right: 0; bottom: 0; z-index: 2; cursor: pointer;"
            "background-color:" + f"rgba{bg_color};"
        )
        with self:
            with ui.element("div").classes("h-screen flex items-center justify-center"):
                ui.label(self.message).style("font-size: 50px; color: white;")
        self.hide()

    def show(self):
        self.set_visibility(True)

    def hide(self):
        self.set_visibility(False)


pathhelper = QCrBoxPathHelper.from_dotenv(".env.dev", "gui_folder/prototype3")

states = [StartGuiState()]

qcrbox = QCrBoxWrapper("127.0.0.1", 11000)

ui.markdown(
    dedent(
        """
        # QCrBox GUI Prototype 3

        This is a prototype for developing the interaction of QCrBox with a non-GUI components.
        """
    ).strip()
)

btn_setup = ui.button("Delete data in and freshly setup work folder", on_click=click_btn_setup)

location_label = ui.label("Currently no cif file is loaded")

ui.markdown("## Upload a dataset")

ui.upload(on_upload=upload_file, auto_upload=True)

ui.markdown("## Input settings in JSON format")

textarea_settings = ui.textarea()
textarea_settings.style("width: min(95ch, 100%)")

ui.markdown("## Available commands")

grid = ui.grid(columns=4)

repopulate_grid()

ui.run()

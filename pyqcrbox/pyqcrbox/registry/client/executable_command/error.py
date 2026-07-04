import multiprocessing


class CommandFailure(Exception):
    def __init__(self, message: str, original_exception: Exception | None = None) -> None:
        super().__init__(message)
        self.original_exception = original_exception


class PrepareCommandFailure(CommandFailure):
    pass


class RunCommandFailure(CommandFailure):
    pass


class FinaliseCommandFailure(CommandFailure):
    pass


def error_dialog_box(message: str) -> multiprocessing.Process:
    """Display an error dialog with the given message using tkinter messagebox.

    The dialog box is launched in a separate process.

    Parameters
    ----------
    message : str
        The error message to display in the dialog box.

    Returns
    -------
    multiprocessing.Process
        The process containing the dialog box.

    """

    def _error_box():
        # Imported lazily so that merely importing this module does not
        # require tkinter (which is only available inside the app containers).
        import tkinter
        import tkinter.messagebox

        window = tkinter.Tk()
        window.withdraw()
        tkinter.messagebox.showinfo("Error!", message)
        window.destroy()

    process = multiprocessing.Process(target=_error_box)
    process.start()

    return process

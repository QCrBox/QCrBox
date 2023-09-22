import webbrowser

from doit.tools import LongRunning


DOIT_CONFIG = {
    "default_tasks": ["show_usage"],
    "verbosity": 2,
    "backend": "sqlite3",
}


def task_docs_build():
    """
    Build the documentation
    """
    return {
        "basename": "docs-build",
        "actions": ["mkdocs build"],
    }


def task_docs_serve():
    """
    Serve the documentation using the local development server and open it in a web browser.
    """
    def open_url(url):
        webbrowser.open(url, new=2)

    return {
        "basename": "docs-serve",
        "actions": [
            (open_url, ["http://127.0.0.1:8000/"]),
            LongRunning("mkdocs serve"),
        ],
    }


def task_show_usage():
    """
    Display usage information.
    """

    def show_usage():
        print()
        print("  doit list                   Show all available commands.")
        print("  doit help <command>         Show usage of a specific command.")
        print("  doit help                   Display help on how to use `doit` itself.")

    return {
        "actions": [show_usage],
    }


if __name__ == "__main__":
    pass

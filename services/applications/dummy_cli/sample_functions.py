import shutil
import time
from pathlib import Path


def print_cif(input_cif: str, print_times: int):
    """A short running command which prints the input_cif and returns it back."""

    for _ in range(print_times):
        print(input_cif)

    return input_cif


def infinite_loop(dummy: str):
    """A command which runs forever and takes no parameters."""

    count = 0

    while True:
        count += 1
        print(f"{count = }")
        time.sleep(2)


def change_cif_name(input_cif: str, output_cif_name: str):
    """Change the name of the output CIF."""

    input_cif_path = Path(input_cif)
    output_cif_path = input_cif_path.parent / output_cif_name
    output_cif_path = output_cif_path.with_suffix(".cif")
    shutil.copy(input_cif_path, output_cif_path)

    return output_cif_path


def print_two_cif(cif1: str, cif2: str):
    """A command to print the contents of cif1 and cif2."""

    def _print(fp):
        print(fp)
        with open(fp, "r") as file:
            print(file.readlines())

    _print(cif1)
    _print(cif2)

    return cif2


def test_cif_to_specific(input_cif: str, output_cif_dummy: str) -> str:
    """Returns the input_cif, which has been transformed to a specific format."""
    print("Input cif file:", input_cif)
    with open(input_cif, "r") as file_in:
        print(file_in.read())

    return input_cif


def test_to_unified_cif(input_cif: str, to_merge_cif: str, output_cif: str) -> str:
    """Returns the input_cif, which will be merged with the original."""
    print("Input cif file:", input_cif)
    with open(input_cif, "r") as file_in:
        print(file_in.read())

    print("To merge cif file:", to_merge_cif)
    with open(to_merge_cif, "r") as file_in:
        print(file_in.read())

    return to_merge_cif


def test_merged_cifs(input_cif: str, output_cif: str) -> Path:
    """Returns the output cif."""
    print("Input cif file:", input_cif)
    with open(input_cif, "r") as file_in:
        lines = file_in.readlines()

    original = str(lines[1])
    lines[1] = "_test_value.with_su 5.67\n"
    print("Replaced", original, "with", lines[1])

    with open(output_cif, "w") as file_out:
        file_out.writelines(lines)

    return Path(output_cif).absolute()


def _demo_plotly_figure_json() -> str:
    """A small Plotly figure as JSON (a Plotly figure is just a dict)."""
    import json

    return json.dumps(
        {
            "data": [
                {"x": [1, 2, 3, 4, 5], "y": [1.2, 2.3, 1.8, 3.1, 2.4], "type": "scatter", "name": "demo series"},
            ],
            "layout": {"title": {"text": "Demo interactive graph"}, "xaxis": {"title": {"text": "step"}}},
        }
    )


_DEMO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="240" height="120">
  <rect width="240" height="120" fill="#eef"/>
  <circle cx="60" cy="60" r="40" fill="#46a"/>
  <text x="120" y="66" font-size="16">demo image</text>
</svg>
"""

_DEMO_HTML = """<!DOCTYPE html>
<html><head><title>Demo report</title></head>
<body>
<h1>Demo HTML report</h1>
<p>This page is self-contained and runs in a sandboxed iframe.</p>
<p id="counter">JavaScript did not run.</p>
<script>document.getElementById("counter").textContent = "JavaScript ran: 1 + 1 = " + (1 + 1);</script>
</body></html>
"""


def _write_demo_artifacts(work_dir: Path, input_cif: str, filenames: dict[str, str]) -> None:
    """Write one demo artifact per requested kind into the work directory."""
    if "text" in filenames:
        n_lines = len(Path(input_cif).read_text(encoding="utf-8").splitlines())
        (work_dir / filenames["text"]).write_text(
            f"Demo text report for {Path(input_cif).name}\nThe input CIF has {n_lines} lines.\n", encoding="utf-8"
        )
    if "image" in filenames:
        (work_dir / filenames["image"]).write_text(_DEMO_SVG, encoding="utf-8")
    if "html" in filenames:
        (work_dir / filenames["html"]).write_text(_DEMO_HTML, encoding="utf-8")
    if "structure" in filenames:
        shutil.copy(input_cif, work_dir / filenames["structure"])
    if "graph" in filenames:
        (work_dir / filenames["graph"]).write_text(_demo_plotly_figure_json(), encoding="utf-8")


def generate_report_artifacts(
    input_cif: str,
    output_cif: str,
    report_text: str,
    report_image: str,
    report_html: str,
    report_structure: str,
    report_graph: str,
):
    """Produce an output CIF plus one artifact of every kind."""
    work_dir = Path(input_cif).parent
    _write_demo_artifacts(
        work_dir,
        input_cif,
        {
            "text": report_text,
            "image": report_image,
            "html": report_html,
            "structure": report_structure,
            "graph": report_graph,
        },
    )
    output_cif_path = work_dir / output_cif
    shutil.copy(input_cif, output_cif_path)
    return output_cif_path


def generate_report_only(input_cif: str, report_text: str, report_graph: str, optional_extra: str):
    """Produce only typed artifacts and deliberately skip the optional one."""
    work_dir = Path(input_cif).parent
    _write_demo_artifacts(work_dir, input_cif, {"text": report_text, "graph": report_graph})
    # `optional_extra` is declared with required_output: false and deliberately
    # not written, to exercise the optional-output semantics.
    return None


def generate_report_broken(input_cif: str, report_text: str):
    """Deliberately violate the output contract: the declared required
    `report_text` output is never written, so the calculation must fail."""
    return None

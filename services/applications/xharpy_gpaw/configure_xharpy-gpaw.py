import os
import shutil
import subprocess
from pathlib import Path

from qcrboxtools.cif.cif2cif import cif_file_unified_yml_instr, cif_file_unify_split
from qcrboxtools.cif.file_converter.hkl import cif2hkl4

from qcrbox.registry.client import QCrBoxRegistryClient

YAML_PATH = "/opt/qcrbox/config_xharpy-gpaw.yaml"

client = QCrBoxRegistryClient()
application = client.register_application(
    "XHARPy-GPAW",
    version="0.2.0",
)


def atom_form_fact_gpaw(
    input_cif_path,
    output_tsc_path,
    functional,
    gridspacing
):
    work_cif_path = Path(input_cif_path).parent / "work.cif"
    cif_file_unified_yml_instr(input_cif_path, work_cif_path, YAML_PATH, "atom_form_fact_gpaw")
    subprocess.check_call([
        "python", "-m", "xharpy.cli_tsc",
        "--cif_name", str(work_cif_path),
        "--tsc_name", str(output_tsc_path),
        "--xc", str(functional),
        #"--kpoints", Param("kpoints"),
        "--gridspacing", str(gridspacing),
        "--auto_default",
    ])


application.register_python_callable("atom_form_fact_gpaw", atom_form_fact_gpaw)


def ha_refine(
    input_cif_path: str,
    output_cif_path: str,
    functional: str,
    gridspacing: float
):
    input_cif_path = Path(input_cif_path)
    output_dir = Path("./xharpy_output")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir()

    cif2hkl4(input_cif_path, 0, output_dir / "shelx.hkl")

    work_cif_path = output_dir / "work.cif"

    cif_text = input_cif_path.read_text(encoding="UTF-8")
    extinction_method = "none"
    if "refine_ls.extinction_coef" in cif_text:
        entry = cif_text.split("refine_ls.extinction_coef")[1].strip()[:2]
        if entry.strip() != ".":
            extinction_method = "shelxl"
    cif_file_unified_yml_instr(input_cif_path, work_cif_path, YAML_PATH, "ha_refine")

    subprocess.check_call([
        "python", "-m", "xharpy.cli_refine",
        "--cif_name", work_cif_path,
        "--cif_index", "0",
        "--hkl_name", output_dir / "shelx.hkl",
        "--lst_name", "./dummy.lst",
        "--extinction", extinction_method,
        "--xc", functional,
        "--gridspacing", gridspacing,
        "--kpoints", "1", "1", "1",
        "--mpi_cores", "auto",
        "--output_folder", output_dir
    ])

    cif_file_unify_split(output_dir / "xharpy.cif", output_cif_path, custom_categories=["iucr, shelx"])
    shutil.rmtree(output_dir)
    os.remove("shelx.hkl")


application.register_python_callable("ha_refine", ha_refine)

client.run()

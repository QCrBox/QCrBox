import os
import shutil
import subprocess
from pathlib import Path

from qcrboxtools.cif.cif2cif import cif_file_merge_to_unified_by_yml, cif_file_to_specific_by_yml
from qcrboxtools.cif.file_converter.hkl import cif2hkl4

from pyqcrbox import sql_models_NEW_v2
from pyqcrbox.registry.client import QCrBoxClient

YAML_PATH = "/opt/qcrbox/config_xharpy_gpaw.yaml"


def atom_form_fact_gpaw(input_cif_path, output_tsc_path, functional, gridspacing):
    work_cif_path = Path(input_cif_path).parent / "work.cif"
    cif_file_to_specific_by_yml(input_cif_path, work_cif_path, YAML_PATH, "atom_form_fact_gpaw", "input_cif_path")
    subprocess.check_call(
        [
            "python",
            "-m",
            "xharpy.cli_tsc",
            "--cif_name",
            str(work_cif_path),
            "--tsc_name",
            str(output_tsc_path),
            "--xc",
            str(functional),
            # "--kpoints", Param("kpoints"),
            "--gridspacing",
            str(gridspacing),
            "--auto_default",
        ]
    )


def ha_refine(input_cif_path, output_cif_path, functional, gridspacing):
    input_cif_path = Path(input_cif_path)
    output_dir = Path("./xharpy_output")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir()

    cif2hkl4(input_cif_path, 0, output_dir / "shelx.hkl")

    work_cif_path = output_dir / "qcrbox_work.cif"

    cif_text = input_cif_path.read_text(encoding="UTF-8")
    extinction_method = "none"
    if "refine_ls.extinction_coef" in cif_text:
        entry = cif_text.split("refine_ls.extinction_coef")[1].strip()[:2]
        if entry.strip() != ".":
            extinction_method = "shelxl"
    cif_file_to_specific_by_yml(input_cif_path, work_cif_path, YAML_PATH, "ha_refine", "input_cif_path")

    subprocess.check_call(
        [
            "python",
            "-m",
            "xharpy.cli_refine",
            "--cif_name",
            work_cif_path,
            "--cif_index",
            "0",
            "--hkl_name",
            output_dir / "shelx.hkl",
            "--lst_name",
            "./dummy.lst",
            "--extinction",
            extinction_method,
            "--xc",
            functional,
            "--gridspacing",
            gridspacing,
            "--kpoints",
            "1",
            "1",
            "1",
            "--mpi_cores",
            "auto",
            "--output_folder",
            output_dir,
        ]
    )

    cif_file_merge_to_unified_by_yml(
        work_cif_path, output_cif_path, input_cif_path, YAML_PATH, "ha_refine", "output_cif_path"
    )

    shutil.rmtree(output_dir)

if __name__ == "__main__":
    application_spec = sql_models_NEW_v2.ApplicationSpec.from_yaml_file(YAML_PATH)

    client = QCrBoxClient(application_spec=application_spec)
    client.run()

import shutil
import subprocess
from pathlib import Path

from qcrboxtools.cif.cif2cif import cif_file_merge_to_unified_by_yml, cif_file_to_specific_by_yml
from qcrboxtools.cif.read import read_cif_as_unified
from qcrboxtools.cif.file_converter.hkl import cif2hkl4
from qcrboxtools.cif.file_converter.tsc import read_tsc_file
from pyqcrbox import sql_models
from pyqcrbox.registry.client import QCrBoxClient

from iotbx.cif.model import cif, block

YAML_PATH = "/opt/qcrbox/config_xharpy_gpaw.yaml"


def atom_form_fact_gpaw(input_cif, output_cif_name, functional, gridspacing):
    work_cif_path = Path(input_cif).parent / "work.cif"
    cif_file_to_specific_by_yml(input_cif, work_cif_path, YAML_PATH, "atom_form_fact_gpaw", "input_cif")

    output_tsc_name = Path(input_cif).parent / "output.tsc"
    output_tsc_cif_name = Path(input_cif).parent / "output_with_tsc.cif"
    subprocess.check_call(
        [
            "python",
            "-m",
            "xharpy.cli_tsc",
            "--cif_name",
            str(work_cif_path),
            "--tsc_name",
            str(output_tsc_name),
            "--xc",
            str(functional),
            # "--kpoints", Param("kpoints"),
            "--gridspacing",
            str(gridspacing),
            "--auto_default",
        ]
    )

    tsc_obj = read_tsc_file(output_tsc_name)
    structure_cif_block = read_cif_as_unified(input_cif, 0)
    aff_source = "partitioned finite grid density"
    aff_partitioning_name = "hirshfeld"
    aff_partitioning_software = "XHARPy"
    new_block = tsc_obj.to_cif(structure_cif_block, aff_source, aff_partitioning_name, aff_partitioning_software)
    new_block.add_data_item("_wfns.software", "GPAW")
    new_block.add_data_item("_wfns.type", "FD/PAW")
    new_block.add_data_item("_wfns.method", functional)

    new_cif = cif()
    new_cif['tscblock'] = new_block
    with open(output_tsc_cif_name, 'w', encoding='UTF-8') as output_tsc_cif:
        output_tsc_cif.write(str(new_cif))

    cif_file_merge_to_unified_by_yml(
        output_tsc_cif_name, output_cif_name, input_cif, YAML_PATH, "atom_form_fact_gpaw", "output_cif_name"
    )

    return str(output_cif_name)


def ha_refine(input_cif, output_cif_name, functional, gridspacing):
    input_cif = Path(input_cif)
    output_dir = Path("./xharpy_output")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir()

    cif2hkl4(input_cif, 0, output_dir / "shelx.hkl")

    work_cif_path = output_dir / "qcrbox_work.cif"

    cif_text = input_cif.read_text(encoding="UTF-8")
    extinction_method = "none"
    if "refine_ls.extinction_coef" in cif_text:
        entry = cif_text.split("refine_ls.extinction_coef")[1].strip()[:2]
        if entry.strip() != ".":
            extinction_method = "shelxl"
    cif_file_to_specific_by_yml(input_cif, work_cif_path, YAML_PATH, "ha_refine", "input_cif")

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

    output_cif_path = work_cif_path.parent / output_cif_name
    cif_file_merge_to_unified_by_yml(
        work_cif_path, output_cif_path, input_cif, YAML_PATH, "ha_refine", "output_cif_name"
    )

    #shutil.rmtree(output_dir)

    return str(output_cif_path)


if __name__ == "__main__":
    application_spec = sql_models.ApplicationSpec.from_yaml_file(YAML_PATH)

    client = QCrBoxClient(application_spec=application_spec)
    client.run()

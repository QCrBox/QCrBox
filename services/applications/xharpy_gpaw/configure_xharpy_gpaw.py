import subprocess
from pathlib import Path

from iotbx.cif.model import cif
from pyqcrbox import sql_models
from pyqcrbox.registry.client import QCrBoxClient
from qcrboxtools.cif.file_converter.hkl import cif2hkl4
from qcrboxtools.cif.file_converter.tsc import read_tsc_file
from qcrboxtools.cif.read import read_cif_as_unified

YAML_PATH = "/opt/qcrbox/config_xharpy_gpaw.yaml"


def atom_form_fact_gpaw(input_cif, output_cif_name, functional, gridspacing):
    input_cif_path = Path(input_cif)
    output_tsc_name = input_cif_path.parent / "output.tsc"
    output_cif_path = input_cif_path.parent / output_cif_name
    subprocess.check_call(
        [
            "python",
            "-m",
            "xharpy.cli_tsc",
            "--cif_name",
            str(input_cif_path),
            "--cif_index",
            "0",
            "--output_folder",
            str(input_cif_path.parent.absolute()),
            "--tsc_name",
            str(output_tsc_name),
            "--xc",
            str(functional),
            # "--kpoints", Param("kpoints"),
            "--gridspacing",
            str(gridspacing),
            "--resolution",
            "cif",
            "--auto_default",
        ]
    )

    tsc_obj = read_tsc_file(output_tsc_name)
    structure_cif_block = read_cif_as_unified(input_cif_path, 0)
    aff_source = "partitioned finite grid density"
    aff_partitioning_name = "hirshfeld"
    aff_partitioning_software = "XHARPy"
    new_block = tsc_obj.to_cif(structure_cif_block, aff_source, aff_partitioning_name, aff_partitioning_software)
    new_block.add_data_item("_wfns.software", "GPAW")
    new_block.add_data_item("_wfns.type", "FD/PAW")
    new_block.add_data_item("_wfns.method", functional)

    new_cif = cif()
    new_cif["tscblock"] = new_block
    with open(output_cif_path, "w", encoding="UTF-8") as output_tsc_cif:
        output_tsc_cif.write(str(new_cif))

    return str(output_cif_path)


def ha_refine(input_cif, output_cif_name, functional, gridspacing):
    input_cif_path = Path(input_cif)

    cif2hkl4(input_cif, 0, input_cif_path.parent / "shelx.hkl")

    output_cif_path = input_cif_path.parent / output_cif_name
    dummy_path = Path(__file__).parent / "dummy.lst"

    cif_text = input_cif_path.read_text(encoding="UTF-8")
    extinction_method = "none"
    if "refine_ls.extinction_coef" in cif_text:
        entry = cif_text.split("refine_ls.extinction_coef")[1].strip()[:2]
        if entry.strip() != ".":
            extinction_method = "shelxl"

    subprocess.check_call(
        [
            "python",
            "-m",
            "xharpy.cli_refine",
            "--cif_name",
            str(input_cif_path),
            "--cif_index",
            "0",
            "--hkl_name",
            str(input_cif_path.parent / "shelx.hkl"),
            "--lst_name",
            str(dummy_path),
            "--extinction",
            extinction_method,
            "--xc",
            functional,
            "--gridspacing",
            str(gridspacing),
            "--kpoints",
            "1",
            "1",
            "1",
            "--mpi_cores",
            "auto",
            "--output_folder",
            str(input_cif_path.parent.absolute()),
        ]
    )

    return str(output_cif_path)


if __name__ == "__main__":
    application_spec = sql_models.ApplicationSpec.from_yaml_file(YAML_PATH)

    client = QCrBoxClient(application_spec=application_spec)
    client.run()

import re
import subprocess
from pathlib import Path

from loguru import logger

from qcrbox.registry.client import QCrBoxRegistryClient


def replace_acta_with_acta_anis(contents):
    return re.sub(
        "^(.*(\r?\n))acta(\r?\n.*)$",
        "\g<1>acta\g<2>anis\g<3>",
        contents,
        flags=re.DOTALL,
    )


def get_ins_file_path(input_cif_path: Path):
    input_cif_contents = input_cif_path.open().read()
    m = re.search(r"\b(?P<res_filename>.+?\.res)\b", input_cif_contents)
    if m is None:
        raise RuntimeError(f"Could not determine filename of .res file from {input_cif_path.as_posix()}")

    res_filename = m.group("res_filename")
    return input_cif_path.parent.joinpath(res_filename).with_suffix(".ins")


def func_test_iso_to_aniso(input_cif_file, insert_anis_directive=True):
    msg = f"Running TEST: iso -> aniso ({input_cif_file!r}, insert_anis_directive={insert_anis_directive!r})"
    logger.debug(msg)

    # input_cif_path = Path(input_cif_file).resolve()
    input_cif_path = Path(input_cif_file)
    workdir = input_cif_path.parent
    cmd = ["shredcif", input_cif_path.name]
    logger.debug(f"Calling command: {cmd}")
    proc = subprocess.run(cmd, cwd=workdir, capture_output=True, check=True)
    logger.debug(f"Command completed with exit code {proc.returncode}")

    ins_file_path = get_ins_file_path(input_cif_path)

    if insert_anis_directive:
        ins_file_contents = ins_file_path.open().read()
        ins_file_contents_augmented = replace_acta_with_acta_anis(ins_file_contents)
        ins_file_path.open("w").write(ins_file_contents_augmented)

    cmd = ["shelxl", ins_file_path.stem]
    logger.debug(f"Calling command: {cmd}")
    proc = subprocess.run(cmd, cwd=workdir, capture_output=True, check=True)
    logger.debug(f"Command completed with exit code {proc.returncode}")

    output_file = workdir.joinpath(ins_file_path.with_suffix(".cif"))
    return {"output_file": output_file}


client = QCrBoxRegistryClient()
application = client.register_application("SHELX", version="git_d0d0f82")
application.register_python_callable("test__iso_to_aniso", func_test_iso_to_aniso)
client.run()

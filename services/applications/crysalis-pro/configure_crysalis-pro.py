import os
import tempfile
from pathlib import Path
from textwrap import dedent

from qcrboxtools.cif.cif2cif import cif_file_to_unified

from qcrbox.registry.client import ExternalCommand, Param, QCrBoxRegistryClient

client = QCrBoxRegistryClient()
application = client.register_application(
    "CrysalisPro",
    version="171.43.48a",
)


def split_hkl_line(line: str):
    if len(line) < 30:
        return line[:4], line[4:8], line[8:12], line[12:20], line[20:28]
    return line[:4], line[4:8], line[8:12], line[12:20], line[20:28], line[28:]


def interactive__finalise(work_folder: str, output_cif_path: str):
    work_folder = Path(work_folder)

    newest_cif_path = next(
        reversed(
            sorted(
                (file_path for file_path in work_folder.glob("*.cif") if file_path.name != "output.cif"),
                key=os.path.getmtime,
            )
        )
    )

    cif_content = newest_cif_path.read_text(encoding="UTF-8")

    if "_diffrn_refln_index_h" not in cif_content:
        # add diffraction data from newest hkl file
        newest_hkl_path = next(
            reversed(
                sorted(
                    (file_path for file_path in work_folder.glob("*.hkl")),
                    key=os.path.getmtime,
                )
            )
        )

        with newest_hkl_path.open("r") as fobj:
            hkl_content = fobj.read()
        cut = hkl_content.split("\n   0   0   0")[0]
        cut = cut.strip().split("\n\n")[0]
        hkl_values = [split_hkl_line(line) for line in cut.split("\n")]
        loop_base = dedent(
            """
            loop_
            _diffrn_refln_index_h
            _diffrn_refln_index_k
            _diffrn_refln_index_l
            _diffrn_refln_intensity_net
            _diffrn_refln_intensity_u
            """
        )
        if len(hkl_values[0]) == 6:
            loop_base += "  _diffrn_refln_scale_group_code\n"

        hkl_string = "\n".join(" ".join(value) for value in hkl_values)
        cif_content += "\n" + loop_base + "\n" + hkl_string + "\n\n"

        with tempfile.NamedTemporaryFile(mode="w+", encoding="UTF-8", delete_on_close=False) as fobj:
            fobj.write(cif_content)
            fobj.close()
            cif_file_to_unified(fobj.name, output_cif_path, custom_categories=["iucr", "olex2"])
    else:
        cif_file_to_unified(newest_cif_path, output_cif_path, custom_categories=["iucr", "olex2"])


external_cmd_open_folder_in_crysalis_pro = ExternalCommand(
    "wine", "/opt/wine_installations/wine_win64/drive_c/Xcalibur/CrysAlisPro171.43.48a/pro.exe", Param("par_path")
)

application.register_external_command(
    "interactive",
    external_cmd_open_folder_in_crysalis_pro,
)

client.run()

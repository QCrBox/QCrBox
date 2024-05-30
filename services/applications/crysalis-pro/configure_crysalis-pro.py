import os
from pathlib import Path
from textwrap import dedent

from qcrboxtools.cif.cif2cif import cif_file_merge_to_unified_by_yml
from qcrboxtools.cif.file_converter.shelxt import ins2symop_loop

from qcrbox.registry.client import ExternalCommand, Param, QCrBoxRegistryClient

YAML_PATH = "./config_crysalis-pro.yaml"

client = QCrBoxRegistryClient()
application = client.register_application(
    "CrysalisPro",
    version="171.44.48a",
)


def split_hkl_line(line: str):
    if len(line) < 30:
        return line[:4], line[4:8], line[8:12], line[12:20], line[20:28]
    return line[:4], line[4:8], line[8:12], line[12:20], line[20:28], line[28:]


def finalise__interactive(work_folder: str, output_cif_path: str):
    work_folder = Path(work_folder)
    output_cif_path = Path(output_cif_path)

    newest_cif_path = next(
        reversed(
            sorted(
                (file_path for file_path in work_folder.glob("*.cif") if file_path.name != "output.cif"),
                key=os.path.getmtime,
            )
        )
    )

    rewrite = False
    newest_cif_text = newest_cif_path.read_text(encoding="UTF-8")

    if "_diffrn_refln_index_h" not in newest_cif_text:
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
        cut = cut.rstrip().split("\n\n")[0]
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

        hkl_string = "\n  ".join(" ".join(value) for value in hkl_values)
        newest_cif_text += "\n" + loop_base + "\n  " + hkl_string + "\n\n"

        rewrite = True

    if "_space_group_symop_id" not in newest_cif_text:
        newest_ins_path = next(
            reversed(
                sorted(
                    (file_path for file_path in work_folder.glob("*.ins")),
                    key=os.path.getmtime,
                )
            )
        )

        symop_loop_str = ins2symop_loop(newest_ins_path)
        cif2old = ['_space_group_symop.id', '_space_group_symop.operation_xyz']
        for entry in cif2old:
            symop_loop_str = symop_loop_str.replace(entry, entry.replace(".", "_"))

        newest_cif_text += "\n\n" + symop_loop_str
        rewrite = True

    if "_chemical_formula_sum" not in newest_cif_text and "_chemical_oxdiff_formula" in newest_cif_text:
        oxdiff_formula_line = next(
            line for line in newest_cif_text.split("\n") if "_chemical_oxdiff_formula" in line
        )
        new_line = oxdiff_formula_line.replace("_chemical_oxdiff_formula", "_chemical_formula_sum")
        newest_cif_text += "\n\n" + new_line
        rewrite = True

    if rewrite:
        merged_cif_path = work_folder / "qcrbox_merged.cif"
        merged_cif_path.write_text(newest_cif_text, encoding="UTF-8")
        cif_file_merge_to_unified_by_yml(
            merged_cif_path, output_cif_path, None, YAML_PATH, "interactive", "output_cif_path"
        )
    else:
        cif_file_merge_to_unified_by_yml(
            newest_cif_path, output_cif_path, None, YAML_PATH, "interactive", "output_cif_path"
        )


application.register_python_callable(
    "finalise__interactive",
    finalise__interactive,
)


def get_crysalis_path():
    xcalibur_dir = Path("/opt/wine_installations/wine_win64/drive_c/Xcalibur")
    crysalis_install_dir = next(d for d in xcalibur_dir.glob("CrysAlisPro*.*.*") if d.is_dir())
    return str(crysalis_install_dir / "pro.exe")


external_cmd_open_folder_in_crysalis_pro = ExternalCommand("wine", get_crysalis_path(), Param("par_path"))

application.register_external_command(
    "interactive",
    external_cmd_open_folder_in_crysalis_pro,
)

client.run()

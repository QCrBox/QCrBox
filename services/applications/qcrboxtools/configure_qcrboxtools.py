from qcrbox.registry.client import ExternalCommand, Param, QCrBoxRegistryClient

client = QCrBoxRegistryClient()
qcrboxtools_obj = client.register_application("QCrBoxTools", version="0.0.5")

external_cmd_replace = ExternalCommand(
    "python",
    "/opt/qcrbox/qcrbtls_replace_structure_glue.py",
    Param("input_cif_path"),
    "0",
    Param("structure_cif_path"),
    "0",
    "--output_cif_path",
    Param("output_cif_path"),
)

qcrboxtools_obj.register_external_command("replace_structure_from_cif", external_cmd_replace)

external_cmd_check_converged = ExternalCommand(
    "python",
    "/opt/qcrbox/qcrbtls_check_convergence_glue.py",
    Param("cif1_path"),
    "0",
    Param("cif2_path"),
    "0",
    "--max_abs_position",
    Param("max_abs_position"),
    "--max_position_su",
    Param("max_position_su"),
    "--max_abs_uij",
    Param("max_abs_uij"),
    "--max_uij_su",
    Param("max_uij_su"),
    "--output",
    Param("output_json"),
)


qcrboxtools_obj.register_external_command("check_structure_convergence", external_cmd_check_converged)

external_cmd_cif_iso2aniso = ExternalCommand(
    "python",
    "/opt/qcrbox/qcrbtls_iso2aniso_glue.py",
    Param("input_cif_path"),
    Param("output_cif_path"),
    "--select_names",
    Param("select_names"),
    "--select_elements",
    Param("select_elements"),
    "--select_regexes",
    Param("select_regexes"),
)

qcrboxtools_obj.register_external_command("iso2aniso", external_cmd_cif_iso2aniso)

external_cmd_to_unified_cif = ExternalCommand(
    "python",
    "/opt/qcrbox/qcrbtls_to_unified_cif_glue.py",
    Param("input_cif_path"),
    Param("output_cif_path"),
    "--custom_categories",
    Param("custom_category_list"),
)

qcrboxtools_obj.register_external_command("to_unified_cif", external_cmd_to_unified_cif)

client.run()

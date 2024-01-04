from qcrbox.registry.client import QCrBoxRegistryClient, ExternalCommand, Param

client = QCrBoxRegistryClient()
application = client.register_application("Olex2 (Linux)", version="1.5")
application.register_external_command(
    "open_file",
    ExternalCommand("/bin/bash", "/opt/olex2/start", Param("filepath")),
)

external_cmd_refine_iam = ExternalCommand(
    "python", "/opt/qcrbox/olex2_glue_cli.py",
    "--structure_path", Param("cif_file"),
    "--n_cycles", Param("ls_cycles"),
    "--weight_cycles", Param("weight_cycles")
)

application.register_external_command("refine_iam", external_cmd_refine_iam)

external_cmd_refine_tsc = ExternalCommand(
    "python", "/opt/qcrbox/olex2_glue_cli.py",
    "--structure_path", Param("cif_file"),
    "--tsc_path", Param("tsc_file"),
    "--n_cycles", Param("ls_cycles"),
    "--weight_cycles", Param("weight_cycles")
)

application.register_external_command("refine_tsc", external_cmd_refine_tsc)

client.run()

from qcrbox.registry.client import ExternalCommand, Param, QCrBoxRegistryClient

client = QCrBoxRegistryClient()
application = client.register_application(
    "CrysalisPro",
    version="171.43.48a",
)

external_cmd_open_folder_in_crysalis_pro = ExternalCommand(
    "wine",
    "/opt/wine_installations/wine_win64/drive_c/Xcalibur/CrysAlisPro171.43.48a/pro.exe",
    Param("work_folder")
)

application.register_external_command(
    "interactive",
    external_cmd_open_folder_in_crysalis_pro,
)

client.run()

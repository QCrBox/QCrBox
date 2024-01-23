from qcrbox.registry.client import ExternalCommand, Param, QCrBoxRegistryClient

cmd_open_file_in_crystal_explorer = ExternalCommand("/usr/bin/CrystalExplorer", "--open", Param("filename"))

client = QCrBoxRegistryClient()
application = client.register_application("CrystalExplorer", version="21.5")
application.register_external_command("open_file", cmd_open_file_in_crystal_explorer)
client.run()

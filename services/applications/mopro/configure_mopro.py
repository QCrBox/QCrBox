from qcrbox.registry.client import ExternalCommand, QCrBoxRegistryClient

client = QCrBoxRegistryClient()
application = client.register_application(
    "MoProSuite",
    version="2022.06",
)

cmd_run_sample_script = ExternalCommand(
    "/bin/bash",
    "/opt/mopro/sample_cmd.sh",
)
application.register_external_command(
    "sample_cmd",
    cmd_run_sample_script,
)

client.run()

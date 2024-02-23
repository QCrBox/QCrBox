from qcrbox.registry.client import ExternalCommand, QCrBoxRegistryClient

client = QCrBoxRegistryClient()
application = client.register_application(
    "{{ cookiecutter.application_name }}",
    version="{{ cookiecutter.application_version }}",
)

cmd_run_sample_script = ExternalCommand(
    "/bin/bash",
    "/opt/{{ cookiecutter.application_slug }}/sample_cmd.sh",
)
application.register_external_command(
    "sample_cmd",
    cmd_run_sample_script,
)

client.run()

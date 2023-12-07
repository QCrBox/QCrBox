import textwrap
from qcrbox.registry.client import QCrBoxRegistryClient, ExternalCommand


def get_bash_script_for_counting_to(num):
    return textwrap.dedent(
        f"""
        x=1
        while [ $x -le {num} ]
        do
          echo "Welcome $x times"
          sleep 0.5
          x=$(( $x + 1 ))
        done
        """
    )


cmd_count_to_10 = ExternalCommand("bash", "-c", get_bash_script_for_counting_to(10))
cmd_count_to_20 = ExternalCommand("bash", "-c", get_bash_script_for_counting_to(20))
cmd_count_to_100 = ExternalCommand("bash", "-c", get_bash_script_for_counting_to(100))


client = QCrBoxRegistryClient()
application = client.register_application("Dummy Application", version="x.y.z")
application.register_external_command("count_to_10", cmd_count_to_10)
application.register_external_command("count_to_20", cmd_count_to_20)
application.register_external_command("count_to_100", cmd_count_to_100)
client.run()

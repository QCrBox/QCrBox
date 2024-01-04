import re
import textwrap
from datetime import datetime
from itertools import islice
from loguru import logger
from qcrbox.registry.client import QCrBoxRegistryClient, ExternalCommand


def concat_files(input_files: list[str], output_file: str, head=10):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    logger.debug(f"Concatenating files: {input_files}")
    with open(output_file, "w") as f_out:
        f_out.write(f"Timestamp: {timestamp}\n==============================\n\n")
        for input_file in input_files:
            logger.debug(f"  Reading file: {input_file!r}")
            with open(input_file, "r") as f_in:
                header_line = f"Input file: {input_file}\n"
                f_out.write(header_line)
                f_out.write(re.sub(".", "-", header_line))
                for line in islice(f_in.readlines(), head):
                    f_out.write(line)
                f_out.write("\n\n")
        logger.debug(f"Output written to file: {output_file!r}")


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
application.register_python_callable("concat_files", concat_files)
client.run()

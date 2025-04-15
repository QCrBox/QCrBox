import json
from pathlib import Path
from subprocess import run

from loguru import logger


class Application:
    """Application to aggregate logs across the QCrBox containers."""

    CONTAINERS = (
        "qcrbox-qcrbox-registry-1",
        "qcrbox-olex2-1",
        "qcrbox-crystal-explorer-1",
    )

    def __init__(self, log_dir: Path = Path("logs")):
        self.log_dir = Path(log_dir).resolve()
        self.log_files = []

    @staticmethod
    def _copy_from_docker(container_name: str, source: str, destination: str) -> None:
        command = ["docker", "cp", f"{container_name}:{source}", f"{destination}"]
        logger.debug(f"Executing command: {' '.join(command)}")
        run(command, check=True)

    def _setup_log_dir(self) -> None:
        """Create the log directory if it doesn't exist."""
        if not self.log_dir.exists():
            logger.debug(f"Creating log directory: {self.log_dir}")
            self.log_dir.mkdir(parents=True, exist_ok=True)

    def _get_logs_from_containers(self):
        for container in self.CONTAINERS:
            logger.info(f"Copying logs from container: {container}")
            destination = self.log_dir / f"{container}.log"
            self._copy_from_docker(container, "/opt/qcrbox/app.log", str(destination))
            self.log_files.append(destination)

    def _process_log_file(self, log_file: Path) -> list[str]:
        """Process a single log file."""
        logger.debug(f"Processing log file: {log_file}")

        with open(log_file, "rt") as infile:
            lines = infile.readlines()

        processed_lines = []
        for line in lines:
            event_dict = json.loads(line)
            processed_lines.append(
                f"{event_dict['timestamp']} | {event_dict['level']:>8} | {event_dict['event']} {event_dict['extra']}\n"
            )

        return processed_lines

    def _aggregate_logs(self) -> None:
        output_path = self.log_dir / "aggregated_log.log"
        processed_output = []
        for log_file in self.log_files:
            processed_output += self._process_log_file(log_file)

        sorted_output = sorted(processed_output, key=lambda x: x.split(" | ")[0])

        with open(output_path, "wt") as outfile:
            outfile.writelines(sorted_output)

        logger.info(f"Aggregated logs saved to: {output_path}")

    def run(self) -> None:
        self._setup_log_dir()
        self._get_logs_from_containers()
        self._aggregate_logs()


if __name__ == "__main__":
    app = Application()
    app.run()

"""Hermetic tests for the VM provisioner's mode and secret wiring."""

import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]
PROVISIONER = REPO_ROOT / "scripts" / "deployment" / "provision_qcrbox.sh"


def _write_executable(path: Path, contents: str) -> None:
    path.write_text(contents)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _make_source_tree(tmp_path: Path) -> tuple[Path, Path, Path]:
    source = tmp_path / "source"
    backend = source / "QCrBox"
    frontend = source / "QCrBoxFrontend"
    backend.mkdir(parents=True)
    frontend.mkdir()
    shutil.copy(REPO_ROOT / ".env.prod", backend / ".env.prod")
    (backend / "docker-compose.prebuilt.yml").write_text("services: {}\n")
    (frontend / "docker-compose.yml").write_text("services: {}\n")

    quality = backend / "services" / "applications" / "qcrbox_quality"
    quality.mkdir(parents=True)
    (quality / "docker-compose.qcrbox_quality.prebuilt.yml").write_text(
        "services:\n"
        "  qcrbox_quality:\n"
        "    x-qcrbox-lifecycle: always-on\n"
        "    image: ghcr.io/qcrbox/qcrbox_quality:test\n"
    )

    mopro = backend / "services" / "applications" / "mopro"
    mopro.mkdir(parents=True)
    (mopro / "docker-compose.mopro.prebuilt.yml").write_text(
        "services:\n  mopro:\n    image: ghcr.io/qcrbox/mopro:test\n"
    )
    (mopro / "config_mopro.yaml").write_text("name: MoPro\nslug: mopro\nversion: test\ncommands: []\n")
    return source, backend, frontend


def _make_fake_commands(tmp_path: Path) -> tuple[Path, Path]:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    docker_log = tmp_path / "docker.log"
    _write_executable(
        fake_bin / "id",
        "#!/usr/bin/env bash\n"
        "if [ \"${1:-}\" = -u ]; then echo 0; else /usr/bin/id \"$@\"; fi\n",
    )
    _write_executable(
        fake_bin / "docker",
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' \"$*\" >> \"$DOCKER_LOG\"\n"
        "if [[ \" $* \" == *' config --images '* ]]; then\n"
        "  printf '%s\\n' ghcr.io/qcrbox/registry:test ghcr.io/qcrbox/qcrbox_quality:test ghcr.io/qcrbox/mopro:test\n"
        "fi\n",
    )
    return fake_bin, docker_log


def _run_provisioner(source: Path, fake_bin: Path, docker_log: Path, credentials: Path, *args: str):
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{fake_bin}:{env['PATH']}",
            "DOCKER_LOG": str(docker_log),
            "QCRBOX_CREDENTIALS_FILE": str(credentials),
        }
    )
    return subprocess.run(
        [
            "bash",
            str(PROVISIONER),
            "--domain",
            "stakeholders.example.org",
            "--source",
            str(source),
            "--apps",
            "qcrbox_quality mopro",
            "--version",
            "test",
            *args,
        ],
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def _env_value(path: Path, key: str) -> str:
    line = next(line for line in path.read_text().splitlines() if line.startswith(f"{key}="))
    return line.split("=", 1)[1].strip("'\"")


def test_fresh_and_update_on_demand_provisioning(tmp_path):
    source, backend, frontend = _make_source_tree(tmp_path)
    fake_bin, docker_log = _make_fake_commands(tmp_path)
    credentials = tmp_path / "credentials.txt"

    result = _run_provisioner(source, fake_bin, docker_log, credentials)
    assert result.returncode == 0, result.stderr

    service_token = _env_value(backend / ".env.vm", "QCRBOX_SERVICE_TOKEN")
    gateway_token = _env_value(backend / ".env.vm", "QCRBOX_GATEWAY_TOKEN")
    assert re.fullmatch(r"[0-9a-f]{64}", service_token)
    assert re.fullmatch(r"[0-9a-f]{64}", gateway_token)
    assert service_token != gateway_token
    assert _env_value(frontend / "environment.env", "QCRBOX_SERVICE_TOKEN") == service_token
    assert stat.S_IMODE((backend / ".env.vm").stat().st_mode) == 0o600
    assert stat.S_IMODE((frontend / "environment.env").stat().st_mode) == 0o600
    assert stat.S_IMODE(credentials.stat().st_mode) == 0o600

    calls = docker_log.read_text().splitlines()
    assert any(line.endswith("up -d --no-build qcrbox_quality") for line in calls)
    assert not any(line.endswith("up -d --no-build mopro") for line in calls)
    registration = "register --prebuilt-images /workspace/services/applications/mopro/config_mopro.yaml"
    assert any(registration in line for line in calls)

    original_secrets = {
        key: _env_value(backend / ".env.vm", key)
        for key in (
            "AUTHELIA_JWT_SECRET",
            "AUTHELIA_SESSION_SECRET",
            "LLDAP_JWT_SECRET",
            "QCRBOX_SERVICE_TOKEN",
            "QCRBOX_GATEWAY_TOKEN",
        )
    }
    result = _run_provisioner(source, fake_bin, docker_log, credentials, "--update")
    assert result.returncode == 0, result.stderr
    assert {key: _env_value(backend / ".env.vm", key) for key in original_secrets} == original_secrets

    backend_env = backend / ".env.vm"
    backend_env.write_text(
        backend_env.read_text()
        .replace(f"QCRBOX_SERVICE_TOKEN={service_token}", "QCRBOX_SERVICE_TOKEN=CHANGEME")
        .replace(f"QCRBOX_GATEWAY_TOKEN={gateway_token}", "QCRBOX_GATEWAY_TOKEN=")
    )
    frontend_env = frontend / "environment.env"
    frontend_env.write_text(
        "\n".join(
            line for line in frontend_env.read_text().splitlines() if not line.startswith("QCRBOX_SERVICE_TOKEN=")
        )
        + "\n"
    )

    result = _run_provisioner(source, fake_bin, docker_log, credentials, "--update")
    assert result.returncode == 0, result.stderr
    repaired_service_token = _env_value(backend_env, "QCRBOX_SERVICE_TOKEN")
    repaired_gateway_token = _env_value(backend_env, "QCRBOX_GATEWAY_TOKEN")
    assert re.fullmatch(r"[0-9a-f]{64}", repaired_service_token)
    assert re.fullmatch(r"[0-9a-f]{64}", repaired_gateway_token)
    assert repaired_service_token != service_token
    assert repaired_gateway_token != gateway_token
    assert _env_value(frontend_env, "QCRBOX_SERVICE_TOKEN") == repaired_service_token


def test_no_on_demand_starts_classic_pool_services(tmp_path):
    source, _, _ = _make_source_tree(tmp_path)
    fake_bin, docker_log = _make_fake_commands(tmp_path)

    result = _run_provisioner(source, fake_bin, docker_log, tmp_path / "credentials.txt", "--no-on-demand")
    assert result.returncode == 0, result.stderr

    calls = docker_log.read_text().splitlines()
    backend_up = [line for line in calls if "--env-file" in line and " up -d --no-build" in line]
    assert any(line.endswith("up -d --no-build") for line in backend_up)
    assert not any("register --prebuilt-images" in line for line in calls)

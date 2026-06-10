# Deploying QCrBox to a VM

`scripts/deployment/` contains two scripts that install the complete stack —
backend (Traefik, Authelia, registry, applications) and the web frontend —
onto a virtual machine, **rerolling every secret** in the process: the three
Authelia secrets, the admin password (argon2id-hashed into
`users_database.yml`), the Django secret key, the frontend's Postgres password
and the Django superuser. The generated credentials are written to
`/root/qcrbox-credentials.txt` inside the VM.

The same provisioner is intended as the installer for a real (internet-facing)
server later — the local VM run is a deployment rehearsal.

## The scripts

**`provision_qcrbox.sh`** runs *inside* a fresh Ubuntu 24.04 VM or server.
It installs docker, generates all secrets, writes the environment files for
both stacks, and starts everything:

```bash
sudo bash provision_qcrbox.sh --domain qcrbox.example.org \
    [--source /opt/qcrbox-src] [--apps "olex2_linux dummy_gui"] \
    [--acme-email you@example.org | --tls-cert cert.pem --tls-key key.pem]
```

**`launch_qcrbox_vm.sh`** runs on your development machine and automates the
local-VM case end to end with [Multipass](https://multipass.run): it creates
the VM, streams your locally built docker images into it (nothing is rebuilt
inside the VM), copies both source trees, derives a hostname and runs the
provisioner:

```bash
bash scripts/deployment/launch_qcrbox_vm.sh --apps "olex2_linux"
```

## Hostnames without /etc/hosts

If you do not pass `--domain`, the launcher uses
`qcrbox.<vm-ip>.nip.io`. nip.io is a public wildcard DNS service that
resolves any `*.<ip>.nip.io` name to that IP, so `auth.qcrbox.….nip.io` and
`olex2.gui.qcrbox.….nip.io` work in any browser with **no hosts-file
entries** — including from Windows when the VM runs under Multipass/Hyper-V.

Caveats: lookups need internet access, and some routers' DNS-rebind
protection refuses answers that point at private IPs (use your router's
allowlist, or fall back to hosts-file entries pointing at the VM IP).

## TLS options

| Mode | Flag | When |
| ---- | ---- | ---- |
| Self-signed (default) | — | Local/LAN VMs; browsers warn once |
| Let's Encrypt | `--acme-email you@example.org` | Host publicly reachable on ports 80/443 with real DNS |
| Supplied certificate | `--tls-cert cert.pem --tls-key key.pem` | Institutional/commercial CA certificates |

A supplied certificate is served by Traefik as the default certificate via
the file provider (`services/core/qcrbox_traefik/dynamic/`). It must cover
the root domain, `auth.`, `api.registry.`, `traefik.` and `*.gui.` names.
**A single wildcard `*.<domain>` does not cover the two-level
`*.gui.<domain>` names** — request a SAN certificate listing both wildcards
(`*.<domain>` and `*.gui.<domain>`) plus the root domain.

## Prerequisites for the launcher

- Multipass: `winget install Canonical.Multipass` on Windows (the script
  finds `multipass.exe` from WSL automatically), `snap install multipass` on
  Linux.
- The QCrBox images built locally (`qcb build` in the devbox shell) for core
  plus every app you pass via `--apps`; the frontend image is built
  automatically if missing.
- The `QCrBoxFrontend` repository checked out next to `QCrBox`.
- Disk/patience: the image stream into the VM is tens of GB.

## After provisioning

- Open `https://<domain>` and log in with the credentials printed at the end
  (user `admin`; also valid for the Django admin at `/admin`).
- Credentials are kept at `/root/qcrbox-credentials.txt` in the VM
  (`multipass exec qcrbox-vm -- sudo cat /root/qcrbox-credentials.txt`).
- Manage the VM with `multipass stop|start|delete qcrbox-vm`.
- Re-running the provisioner rerolls all secrets again; note that this wipes
  the Authelia data volume (its database is encrypted with the old key) and
  thereby existing TOTP enrolments.

# Deploying QCrBox to a VM or Server

`scripts/deployment/` contains two scripts that install the complete stack —
backend (Traefik, Authelia, LLDAP, registry, applications) and the web
frontend — onto an Ubuntu VM, **rerolling every secret** in the process
(Authelia secrets, LLDAP secrets, admin password, Django secret key, Postgres
password). The generated credentials are written to
`/root/qcrbox-credentials.txt` on the target machine.

**Trust model:** all accounts are mutually trusted. Every logged-in user can
see all data and shares the same GUI desktop sessions. Only create accounts
for people who may see everything; QCrBox does not yet provide per-user data
isolation.

## The scripts

**`deploy_qcrbox_ssh.sh`** runs on your development machine and deploys to
any SSH-reachable Ubuntu VM — e.g. an EOSC / EGI Cloud Compute (OpenStack)
instance. It streams your locally built docker images to the VM (nothing is
built there), copies both source trees, and runs the provisioner:

```bash
bash scripts/deployment/deploy_qcrbox_ssh.sh --host ubuntu@<public-ip> \
    --identity ~/.ssh/eosc_key --apps "olex2_linux" \
    --domain qcrbox.example.org --acme-email you@example.org
```

Use `--no-images` on re-deploys to skip the (tens of GB) image stream.

**`provision_qcrbox.sh`** is what the deploy script executes *on* the VM; it
can also be run by hand on any fresh Ubuntu 24.04 server with the two source
trees present. It installs docker, generates all secrets, writes the
environment files and starts both stacks:

```bash
sudo bash provision_qcrbox.sh --domain qcrbox.example.org \
    [--source /opt/qcrbox-src] [--apps "olex2_linux dummy_gui"] \
    [--acme-email you@example.org | --tls-cert cert.pem --tls-key key.pem]
```

## Prerequisites

- Local: the QCrBox images built (`qcb build` in the devbox shell) for core
  plus every app you pass via `--apps`; the `QCrBoxFrontend` repository
  checked out next to `QCrBox` (its image is built automatically if missing).
  **Important:** all images must be built from the same commit — the registry
  rejects applications whose pyqcrbox version differs from its own.
- VM: Ubuntu 24.04, ≥4 vCPU, 8 GB RAM, ≥60 GB disk; a public/floating IP;
  SSH key access as a sudo-capable user (cloud images: `ubuntu`); firewall /
  OpenStack security group allowing only ports 22, 80 and 443.

## DNS and TLS

For a real deployment, create DNS A/AAAA records pointing at the VM for the
root domain plus `auth.`, `users.`, `api.registry.`, `traefik.` and
`*.gui.<domain>`.

For a quick trial without DNS, omit `--domain`: the script uses
`qcrbox.<vm-ip>.nip.io`, a public wildcard DNS service that resolves in any
browser without configuration. Caveats: needs internet DNS, some routers'
rebind protection blocks answers pointing at private IPs, and Let's Encrypt
rate-limits nip.io names heavily — stay on the self-signed certificate for
trials.

| TLS mode | Flag | When |
| -------- | ---- | ---- |
| Self-signed (default) | — | Trials; browsers warn once |
| Let's Encrypt | `--acme-email you@example.org` | Host publicly reachable on 80/443 with real DNS |
| Supplied certificate | `--tls-cert cert.pem --tls-key key.pem` | Institutional/commercial CA certificates |

A supplied certificate is served by Traefik as the default certificate via
the file provider (`services/core/qcrbox_traefik/dynamic/`). It must cover
the root domain and all subdomains above. **A single wildcard `*.<domain>`
does not cover the two-level `*.gui.<domain>` names** — request a SAN
certificate listing both wildcards plus the root domain.

## Server hardening checklist

The compose files bind everything except 80/443 to `127.0.0.1` (NATS has no
authentication and must never be exposed). Beyond that:

1. **Firewall**: allow only 22, 80, 443. Docker publishes ports via iptables
   and **bypasses ufw** — rely on the loopback bindings and your cloud
   security group, not on ufw, for docker-published ports.
2. **SSH**: key-based authentication only (`PasswordAuthentication no`);
   consider fail2ban.
3. **Updates**: enable unattended OS upgrades; rebuild and re-deploy images
   periodically.
4. **2FA**: consider switching the GUI rules in `authelia_config.yml` from
   `one_factor` to `two_factor` once users enrolled TOTP — GUI sessions grant
   shell-equivalent access.
5. **Verify from outside**: from another machine, check only 22/80/443 answer
   (`nmap <host>`), `http://…` redirects to HTTPS, and every subdomain
   redirects to the Authelia login when unauthenticated.

## After provisioning

- Open `https://<domain>` and log in with the credentials printed at the end
  (user `admin`; also valid for the Django admin at `/admin`).
- Create accounts at `https://users.<domain>` (LLDAP web UI, restricted to
  the `lldap_admin` group), then assign them to research groups in the
  frontend.
- Credentials are kept at `/root/qcrbox-credentials.txt` on the VM.
- Re-running the provisioner rerolls all secrets and wipes the Authelia and
  LLDAP data volumes — **all user accounts, passwords and TOTP enrolments are
  recreated from scratch**.

## Operations

- **Backups**: the docker volumes (`qcrbox-registry-db`, `qcrbox-nats-storage`,
  `qcrbox-authelia-data`, `qcrbox-lldap-data`, the frontend's
  `postgres_data`) and `shared_files/`.
- **Password resets**: the notifier writes reset links to a file inside the
  Authelia container (`/config/notification.txt`). For real users configure
  an SMTP notifier in `authelia_config.yml`.

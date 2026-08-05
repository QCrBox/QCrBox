# Deploying QCrBox to a VM or Server

`scripts/deployment/` contains two scripts that install the complete stack —
backend (Traefik, Authelia, LLDAP, registry, applications) and the web
frontend — onto an Ubuntu VM, **rerolling every secret** in the process
(Authelia secrets, LLDAP secrets, admin password, Django secret key, Postgres
password, and frontend/Traefik identity tokens). The generated credentials are written to
`/root/qcrbox-credentials.txt` on the target machine.

**Trust model:** application containers and their GUI routes are owned by the
user who invoked them, but stored datasets are not yet isolated. Only create
accounts for selected stakeholders who may see all structures. This deployment
is not yet suitable for mutually untrusted tenants.

## The scripts

**`deploy_qcrbox_ssh.sh`** runs on your development machine and deploys to
any SSH-reachable Ubuntu VM — e.g. an EOSC / EGI Cloud Compute (OpenStack)
instance. By default it clones both source repositories directly on the VM
from GitHub, then runs the provisioner which pulls all images from GHCR:

```bash
# Set credentials without putting them in shell history (see GHCR authentication below)
export GHCR_USER=niolon
read -rsp "GHCR token: " GHCR_TOKEN && echo && export GHCR_TOKEN

bash scripts/deployment/deploy_qcrbox_ssh.sh --host ubuntu@<public-ip> \
    --version 0.2.0 \
    --identity ~/.ssh/eosc_key --apps "qcrbox_quality olex2_linux mopro" \
    --domain qcrbox.example.org --acme-email you@example.org
```

Omit `--version` to deploy `:latest` images from the `main` branch. For
development deployments on a specific branch, use `--branch <name>` (applies
to both repos) and optionally `--frontend-branch <name>` to override only the
frontend repo's branch.

For an unpublished test deployment, pass both `--transfer-images` and
`--transfer-sources`. The script packages the exact local image set, uploads
it with resumable `rsync`, loads it on the VM, and transfers the local source
trees instead of cloning them. Generated environment files and secrets are
never copied from the development machine; an `--update` preserves the ones
already installed on the VM.

**`provision_qcrbox.sh`** is what the deploy script executes *on* the VM; it
can also be run by hand on any fresh Ubuntu 24.04 server with the two source
trees present. It installs docker, generates all secrets, writes the
environment files, pulls images and starts both stacks:

```bash
sudo bash provision_qcrbox.sh --domain qcrbox.example.org \
    [--version 0.2.0] [--source /opt/qcrbox-src] [--apps "olex2_linux dummy_gui"] \
    [--acme-email you@example.org | --tls-cert cert.pem --tls-key key.pem]
```

## Prerequisites

- **Images**: for the default deployment path, QCrBox and frontend images must
  be published at the target version — see [Creating a release](github_release.md).
  For an unpublished deployment, every required image must instead exist
  locally under its exact deployment tag and `--transfer-images` must be used.
  In either case all QCrBox images must be built from a compatible source
  version: the registry ignores applications whose `pyqcrbox` version differs
  from its own.
- **GHCR access (published-image path only)**: images are published as
  *internal* (organisation-only). Create a GitHub Personal Access Token (PAT)
  with `read:packages` scope — see
  [GHCR authentication](#ghcr-authentication) below.
- **VM**: Ubuntu 24.04, ≥4 vCPU, 8 GB RAM, ≥60 GB disk; a public/floating IP;
  SSH key access as a sudo-capable user (cloud images: `ubuntu`); internet
  access to install Docker. GitHub and GHCR access are only required when the
  corresponding local transfer flags are omitted. The firewall / OpenStack
  security group should allow only ports 22, 80 and 443.

### Unpublished local-image deployment

The SSH deployer can transfer the complete image set, including licensed
applications, without pushing anything to GHCR. Choose a deployment tag and,
inside the QCrBox Devbox shell, build the backend images with `qcb`:

```bash
cd QCrBox
devbox shell

export TEST_TAG=stakeholder-test
export QCRBOX_DOCKER_TAG=$TEST_TAG
export PYTHONPATH="$PWD/pyqcrbox${PYTHONPATH:+:$PYTHONPATH}"

# Build a mutually compatible registry, always-on quality service and MoPro.
qcb build pyqcrbox
qcb build base-ancestor
qcb build registry qcrbox_quality mopro

```

Build the frontend from the adjacent `QCrBoxFrontend` checkout. Before doing
so, make sure its `QCrBoxAPIClient/` directory contains the multi-user client
checkout:

```bash
rsync -a --delete --exclude=.git ../QCrBoxAPIClient/ ../QCrBoxFrontend/QCrBoxAPIClient/
docker compose -f ../QCrBoxFrontend/docker-compose.yml \
    --project-directory ../QCrBoxFrontend --project-name qcrboxfrontend build server
```

If `qcb` and the frontend build produced `:latest` images rather than
`:$TEST_TAG`, there is no need to tag every image manually. Tell the deployer
which local source tag to use; it creates all exact deployment tags after
validating the corresponding image exists.

The transfer includes public runtime dependencies too. Pull any that are not
already present locally:

```bash
QCRBOX_DOCKER_REPO=ghcr.io/qcrbox QCRBOX_DOCKER_TAG=$TEST_TAG \
    docker compose --env-file .env.prod -f docker-compose.prebuilt.yml \
    -f services/applications/qcrbox_quality/docker-compose.qcrbox_quality.prebuilt.yml \
    -f services/applications/mopro/docker-compose.mopro.prebuilt.yml pull --ignore-pull-failures
docker compose -f ../QCrBoxFrontend/docker-compose.yml \
    --project-directory ../QCrBoxFrontend pull nginx db
```

Then deploy the local checkouts and local images directly:

```bash
bash scripts/deployment/deploy_qcrbox_ssh.sh \
    --host ubuntu@<public-ip> \
    --identity ~/.ssh/eosc_key \
    --version "$TEST_TAG" \
    --local-image-tag latest \
    --apps "qcrbox_quality mopro" \
    --transfer-images --transfer-sources \
    --domain qcrbox.example.org --acme-email you@example.org
```

No GHCR credentials are needed. The script validates every image before
uploading and reports the first genuinely missing source image. When
`--local-image-tag` is supplied, its local `qcrbox/*` images deliberately
replace any existing exact deployment tags; this prevents an old
`ghcr.io/qcrbox/*:<version>` alias from silently winning over a fresh `qcb
build --all`. The unnamespaced `qcrboxfrontend-server:<tag>` image is treated
the same way. The deployer compares a deterministic runtime fingerprint for
each exact local tag with the same tag on the VM. This fingerprint covers the
platform, runtime configuration, and ordered filesystem layers, while ignoring
Docker build-history metadata that changes on otherwise equivalent rebuilds.
Missing and materially changed images are archived; loaded images are verified
against the expected fingerprint before provisioning. If everything already
matches, packing, transfer, and loading are skipped. A mode-`0600`,
rsync-friendly copy of the latest delta remains under `~/.cache/qcrbox/` on
the VM so interrupted uploads can resume and subsequent deltas can reuse
common compressed blocks. Remove that directory manually if disk space is
more important than incremental transfer speed. The local temporary archive
is removed after it loads successfully. The deployer
also passes `--no-pull` to the remote provisioner, preventing a transferred tag
from being replaced by a remotely published one.
Add `--update` on later deployments to preserve accounts, data and secrets.
Core containers are recreated during an update so transferred bind-mounted
configuration takes effect; named account and data volumes are retained.

Spawned desktop applications are exposed below one stable TLS hostname, for
example `https://gui.qcrbox.example/olex2-108643ec/`. Traefik obtains that
hostname's certificate during provisioning, then authenticates every request
and asks the registry to verify that the signed-in user owns the requested
instance. VNC ports are not published directly on the VM.

If a retry is needed after the exact images have already loaded successfully,
replace `--transfer-images` with `--reuse-remote-images`. This skips local
packing and network transfer while retaining the provisioner's `--no-pull`
guarantee. Use it only after confirming the VM has every required exact tag.

## GHCR authentication

QCrBox images are published as *internal* packages on GHCR, meaning only
members of the GitHub organisation can pull them. The VM must authenticate
before `docker compose pull` will succeed.

**Create a PAT** (one-time, per deployer):

1. Go to GitHub → **Settings → Developer settings → Personal access tokens →
   Tokens (classic)**.
2. Click **Generate new token (classic)**.
3. Give it a descriptive name (e.g. `qcrbox-deploy-read`), set an expiry, and
   tick only the **`read:packages`** scope.
4. Copy the token (`ghp_…`) — it is shown only once.

**Pass the token to the deploy script** without putting it in your shell
history — set it as an environment variable using `read -rs`, which echoes
nothing and is not recorded by bash/zsh:

```bash
export GHCR_USER=<your-github-username>
read -rsp "GHCR token: " GHCR_TOKEN && echo && export GHCR_TOKEN

bash scripts/deployment/deploy_qcrbox_ssh.sh \
    --host ubuntu@<public-ip> \
    --version 0.2.0 \
    ...
```

Both scripts pick up `GHCR_USER` and `GHCR_TOKEN` from the environment
automatically; `--ghcr-user` / `--ghcr-token` flags are also accepted for CI or
secrets-manager use.

The deploy script forwards the credentials to the VM by writing them to a
root-only file in `/run` (tmpfs — RAM only, never touches persistent disk),
sourcing it inside `provision_qcrbox.sh`, then deleting it immediately. The
token never appears in a process argument list on either machine.

If you are running `provision_qcrbox.sh` directly on the VM (without the SSH
wrapper), set the environment variables there in the same way before calling the
script.

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
- In the default on-demand mode, `qcrbox_quality` remains running while
  registered application containers start only when a stakeholder invokes
  them. Each authenticated user receives an owner-bound container and GUI
  route; another user receives `403` when attempting to open that route.
- Credentials are kept at `/root/qcrbox-credentials.txt` on the VM.
- A fresh provision rerolls all secrets and wipes identity volumes; `--update`
  preserves accounts, data and valid secrets. When upgrading an older install,
  it only backfills missing or placeholder identity tokens.

After two stakeholders invoke an application, confirm per-user instances with:

```bash
sudo docker ps --filter label=org.qcrbox.spawned=true \
  --format 'table {{.Names}}\t{{.Label "org.qcrbox.application_slug"}}\t{{.Status}}'
```

Spawnable applications must have no long-running pool container. Idle
instances are removed automatically according to the
`QCRBOX__ORCHESTRATOR__*` settings in `.env.vm`.

## Operations

- **Backups**: the docker volumes (`qcrbox-registry-db`, `qcrbox-nats-storage`,
  `qcrbox-authelia-data`, `qcrbox-lldap-data`, the frontend's
  `postgres_data`). The legacy `shared_files/` directory is only mounted by
  the Wine-based applications (CrysAlisPro, MoPro); all other file exchange
  goes through the NATS data store.
- **Password resets**: the notifier writes reset links to a file inside the
  Authelia container (`/config/notification.txt`). For real users configure
  an SMTP notifier in `authelia_config.yml`.

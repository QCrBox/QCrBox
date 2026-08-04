# Deploying QCrBox on a Local Network

This guide covers running QCrBox on a server inside a lab or workgroup
network — users access it from their workstations on the LAN, and the server
is **not reachable from the public internet**. It builds on
[Deploying QCrBox to a VM](deploy_qcrbox_to_a_vm.md) (same scripts, same
prerequisites); read that first. This page covers only what is *different*
on a LAN: DNS, TLS, and day-2 operation.

**Trust model reminder:** all accounts are mutually trusted and GUI sessions
are shell-equivalent inside their containers. On-demand containers belong to
the user who started them, but all users can see all data. Only create
accounts for members of the group.

## Overview

What a LAN deployment needs that the internet-facing path gives you for free:

1. **Wildcard DNS** for the QCrBox domain, resolving to the server's LAN IP —
   including the *two-level* wildcard `*.gui.<domain>` used by on-demand GUI
   containers.
2. **TLS without Let's Encrypt** — ACME challenges cannot reach a LAN-only
   host. Use a certificate from your institution's CA, or a self-signed one
   whose CA you distribute to the workstations.
3. **Image access** — either let the server reach GHCR and GitHub, or use the
   SSH deployer's `--transfer-images --transfer-sources` mode described in the
   VM deployment guide.

## 1. DNS

QCrBox serves everything under one domain, e.g. `qcrbox.lab.internal`:
the frontend at the root, `auth.`, `users.`, `api.registry.`, `traefik.` —
and **`<app>-<id>.gui.<domain>`** for every on-demand GUI container. The GUI
hostnames are created dynamically at spawn time, so the DNS entry **must be a
wildcard**; per-workstation `hosts` files cannot work (they don't support
wildcards, and the GUI names change with every container).

**Recommended: dnsmasq** on the lab's DNS resolver (or the QCrBox server
itself). A single line covers the domain and *all* subdomain levels,
including `*.gui.`:

```text
# /etc/dnsmasq.d/qcrbox.conf  — 192.168.10.20 = the QCrBox server
address=/qcrbox.lab.internal/192.168.10.20
```

Point the workstations (usually via the router's DHCP settings) at this
resolver.

Alternatives:

- **Institutional DNS**: ask your IT department for `qcrbox.lab.internal A
  192.168.10.20` plus wildcards `*.qcrbox.lab.internal` **and
  `*.gui.qcrbox.lab.internal`** (a single-level wildcard does not match
  two-level names in DNS — same pitfall as with certificates).
- **Pi-hole**: Local DNS → add the domain with "wildcard" enabled (it uses
  dnsmasq's `address=/.../` underneath).
- **`nip.io`** (`qcrbox.192-168-10-20.nip.io`) requires internet DNS from the
  workstations and is frequently blocked by router DNS-rebind protection for
  private IPs — test before relying on it.

## 2. TLS

Set `QCRBOX_TLS_CERT_RESOLVER=` (empty — the default in `.env.prod`).
**Do not** set it to `letsencrypt`: ACME HTTP-01 validation has to reach the
server from the internet and will fail on a LAN.

The certificate must cover — as Subject Alternative Names — all of:

- `qcrbox.lab.internal` (the root domain)
- `*.qcrbox.lab.internal` (auth, users, api.registry, traefik, ...)
- `*.gui.qcrbox.lab.internal` (on-demand GUI containers)

A single wildcard is **not** enough: `*.qcrbox.lab.internal` does not match
`olex2-1a2b3c4d.gui.qcrbox.lab.internal`.

### Option A: certificate from your institution's CA

Request a SAN certificate for the three names above, then install it either
with the provisioner (`--tls-cert qcrbox.crt --tls-key qcrbox.key`) or by
dropping the files into `services/core/qcrbox_traefik/dynamic/` (see the
README there). Workstations trust it automatically if they trust the
institutional CA.

### Option B: own CA (self-signed)

Create a small CA once, sign a server certificate with the required SANs,
and install the CA certificate on the workstations:

```bash
DOMAIN=qcrbox.lab.internal

# One-off: the CA (keep ca.key offline/safe)
openssl req -x509 -newkey rsa:4096 -sha256 -days 3650 -nodes \
    -keyout ca.key -out ca.crt -subj "/CN=QCrBox Lab CA"

# Server key + CSR + certificate with all three SANs
openssl req -newkey rsa:4096 -sha256 -nodes \
    -keyout qcrbox.key -out qcrbox.csr -subj "/CN=${DOMAIN}"
openssl x509 -req -in qcrbox.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
    -days 825 -sha256 -out qcrbox.crt \
    -extfile <(printf "subjectAltName=DNS:%s,DNS:*.%s,DNS:*.gui.%s" \
               "$DOMAIN" "$DOMAIN" "$DOMAIN")
```

Pass `--tls-cert qcrbox.crt --tls-key qcrbox.key` to the provision/deploy
script, and install `ca.crt` as a trusted CA on each workstation (or accept
the browser warning, as with Traefik's default self-signed certificate —
workable for a quick trial, tiresome for daily use because the warning
reappears per subdomain).

Verify what Traefik serves, including the GUI wildcard:

```bash
openssl s_client -connect 192.168.10.20:443 \
    -servername test.gui.$DOMAIN </dev/null 2>/dev/null \
    | openssl x509 -noout -ext subjectAltName
```

## 3. Provisioning

With DNS and the certificate in place, deployment is the standard scripted
path from the VM guide:

```bash
bash scripts/deployment/deploy_qcrbox_ssh.sh --host admin@192.168.10.20 \
    --version 0.2.0 --domain qcrbox.lab.internal \
    --apps "olex2_linux" \
    --tls-cert qcrbox.crt --tls-key qcrbox.key
```

The provisioner enables **on-demand containers** by default: applications are
registered with the registry, and a container is spawned per user when they
launch an application (pass `--no-on-demand` for the classic long-running
containers instead). Per-container resource limits are written to `.env.vm`:

```text
QCRBOX__ORCHESTRATOR__CONTAINER_MEMORY_LIMIT_MB=8192   # 8 GB per container
QCRBOX__ORCHESTRATOR__CONTAINER_CPU_LIMIT=4            # 4 CPUs per container
QCRBOX__ORCHESTRATOR__MAX_TOTAL_INSTANCES=10           # across all users
```

Adjust these to the server's hardware. Idle containers are removed after 30
minutes (`QCRBOX__ORCHESTRATOR__IDLE_TIMEOUT`); users are limited to
`QCRBOX__ORCHESTRATOR__MAX_INSTANCES_PER_USER` (default 5) live containers.
As a sizing rule of thumb, plan for the memory limit times the number of
*simultaneously active* users, plus ~4 GB for the core services.

## 4. Firewall

Expose **only 443** (and 80, which just redirects to HTTPS) to the LAN.
Everything else is loopback-bound by design and must stay that way:

- NATS (4222/8222) has **no authentication** — never change
  `QCRBOX_NATS_BIND_ADDRESS` away from `127.0.0.1`.
- The registry API (11000) is unauthenticated admin/tooling access — reach it
  via SSH tunnel (`ssh -L 11000:127.0.0.1:11000 admin@server`) when needed.

Note that Docker publishes ports by manipulating iptables directly, so
host-level firewalls like `ufw` do **not** restrict them — restrict access at
the network level (router/VLAN) if the server has interfaces beyond the lab
LAN.

## 5. Updating

To upgrade a running installation **without losing accounts, data or
secrets**, use `--update`:

```bash
bash scripts/deployment/deploy_qcrbox_ssh.sh --host admin@192.168.10.20 \
    --version 0.3.0 --domain qcrbox.lab.internal --apps "olex2_linux" --update
```

This re-clones the sources, bumps the image version, re-pulls and restarts —
but keeps `.env.vm`, the frontend environment, and all volumes (LLDAP
accounts, Authelia state, frontend database). Without `--update`,
provisioning **wipes accounts and data and rerolls every secret** (that is
the right behaviour for a first install or a deliberate reset).

Back up the named volumes listed in the
[VM guide](deploy_qcrbox_to_a_vm.md#operations) before updating.

## If the server has no registry or GitHub access

Transfer both directly from the development machine:

```bash
bash scripts/deployment/deploy_qcrbox_ssh.sh --host admin@192.168.10.20 \
    --version stakeholder-test --domain qcrbox.lab.internal \
    --apps "qcrbox_quality mopro" \
    --transfer-images --transfer-sources
```

The VM still needs package access if Docker is not installed yet. Once Docker
is present, the selected source trees and complete runtime image set are
transferred without using GitHub or GHCR from the server. See
[Unpublished local-image deployment](deploy_qcrbox_to_a_vm.md#unpublished-local-image-deployment)
for build and exact-tag instructions.

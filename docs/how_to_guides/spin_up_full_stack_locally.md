# Spinning up the Full QCrBox Stack Locally

This guide walks through running the complete QCrBox system on a local machine:
the QCrBox backend (registry, message bus, application containers) behind the
Traefik reverse proxy with Authelia authentication, plus the
[QCrBoxFrontend](https://github.com/QCrBox/QCrBoxFrontend) web application with
single sign-on.

For how the authentication works, see
[Authentication in QCrBox](setup_authelia_authentication.md).
For deploying to a server or VM with freshly generated secrets, see
[Deploying QCrBox to a VM](deploy_qcrbox_to_a_vm.md) instead.

## What you end up with

| URL | Service | Authentication |
| --- | ------- | -------------- |
| `https://qcrbox.localhost` | Web frontend (Django) | Authelia (SSO) |
| `https://auth.qcrbox.localhost` | Authelia login portal | — |
| `https://api.registry.qcrbox.localhost` | Registry REST API | Authelia |
| `https://<app>.gui.qcrbox.localhost` | noVNC GUI of an application (e.g. `olex2`) | Authelia |
| `https://users.qcrbox.localhost` | User management (LLDAP) | Authelia (admins only) |
| `https://traefik.qcrbox.localhost` | Traefik dashboard | Authelia (admins only) |

One Authelia login (dev default: `admin` / `changeme`) covers all of them. The
frontend recognises the Authelia user automatically via the `Remote-User`
header — its own login page is not used.

## Prerequisites

1. QCrBox development environment set up
   (see [Setting up a development environment](set_up_a_dev_environment.md))
2. The `QCrBoxFrontend` repository checked out next to `QCrBox`
   (both repos in the same parent directory is assumed below)
3. Docker running

## Step 1: DNS configuration — none needed

The development domain is `qcrbox.localhost`. Browsers (and systemd-resolved)
resolve every `*.localhost` name to `127.0.0.1` natively, at any subdomain
depth — so `auth.qcrbox.localhost` and `olex2.gui.qcrbox.localhost` work with
**no `/etc/hosts` entries**, including from a Windows browser when QCrBox runs
inside WSL2 (localhost forwarding carries port 443 through).

Command-line tools do not all share this behaviour; for `curl`, pass
`--resolve <name>:443:127.0.0.1` as shown in Step 5.

## Step 2: Start the QCrBox backend

From the `QCrBox` repository:

```bash
devbox shell

# Optional sanity check of the authentication setup
bash scripts/devbox/test_qcb_with_authelia.sh

# Start everything (or list specific applications instead of --all)
qcb up --all
```

`qcb up` starts a long-running container per application. Alternatively,
`qcb serve --all` registers the applications but lets the registry spawn
containers on demand, per user, when they are actually used — the mode a
multi-user deployment runs in (requires `QCRBOX__ORCHESTRATOR__ENABLED=true`
in `.env.dev`). See
[the qcb guide](use_qcb_to_interact_with_and_manage_qcrbox.md) for the
difference.

Wait until all containers report healthy:

```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

## Step 3: Start the frontend

The frontend is a separate docker compose project that joins the QCrBox docker
network, so **the backend must already be running** (Step 2 creates the
`qcrbox_qcrbox-net` network).

From the `QCrBoxFrontend` repository:

```bash
cp environment.env.template environment.env
# Edit environment.env: set DJANGO_SUPERUSER_EMAIL / _USERNAME / _PASSWORD.
# The remaining defaults are correct for a local setup.

docker compose up -d --build
```

The frontend is not published on any host port — it is only reachable through
Traefik at `https://qcrbox.localhost`. This is required for the single sign-on
header to be trustworthy.

## Step 4: Log in and set up users

1. Open `https://qcrbox.localhost` in a browser. You will be redirected to the
   Authelia portal. Accept the self-signed-certificate warning (local
   development uses Traefik's default certificate; real deployments use
   Let's Encrypt).
2. Log in with the development credentials `admin` / `changeme`.
3. You land in the frontend, logged in as `admin` — the Django user is created
   automatically on first visit.
4. In the frontend, create at least one group (Groups → Create Group) and
   assign your user to it; data uploads require a group.
5. To create accounts for other people, open `https://users.qcrbox.localhost`
   (LLDAP web UI, admins only) and add users there. They can log in at the
   Authelia portal immediately; afterwards add them to a frontend group.

**How accounts work:** Authelia owns login credentials and (optional)
two-factor authentication; the accounts themselves live in LLDAP and are
managed at `https://users.<domain>`. The frontend keeps its own user records
(auto-created on first visit, matched by username) for research-group
membership and dataset permissions. The Django superuser from
`environment.env` is only needed for the Django admin interface at
`https://qcrbox.localhost/admin`.

## Step 5: Verify

```bash
# Health check, no login required
curl -k https://api.registry.qcrbox.localhost/api/healthz

# Everything else redirects to the login portal when unauthenticated
curl -k -o /dev/null -w '%{http_code} %{redirect_url}\n' https://qcrbox.localhost/
# -> 302 https://auth.qcrbox.localhost/?rd=...
```

In the browser (logged in): open a dataset in the frontend and start an
interactive session — the GUI opens in a new tab on
`https://<app>.gui.qcrbox.localhost` without a second login.

## Shutting down

```bash
# Frontend (from QCrBoxFrontend/)
docker compose down

# Backend (from QCrBox/, inside devbox shell)
qcb down
```

## Troubleshooting

**`network qcrbox_qcrbox-net not found` when starting the frontend** — the
backend is not running. Run `qcb up` in the QCrBox repository first.

**Browser shows the Authelia portal again when opening a GUI tab** — the
session cookie was issued for a different domain (e.g. after changing
`QCRBOX_DOMAIN`) — clear cookies for `qcrbox.localhost` and log in again.

**403 "Access denied" on `users.` or `traefik.` subdomains** — these are
restricted to members of the LLDAP group `lldap_admin`; the built-in `admin`
user is a member, other users are not (by design).

**Logged in, but the frontend shows no data / cannot upload** — your user is
not in any group yet. Create a group and add the user (Step 4.4).

**Logged in via SSO, but cannot create groups or users** — frontend users
auto-created from the Authelia login start without any Django permissions,
and the frontend only creates its superuser on an empty database. If your
database already had users, promote your SSO user once:

```bash
docker exec qcrboxfrontend-server-1 python /app/qcrbox_frontend/manage.py shell -c "
from django.contrib.auth.models import User
u = User.objects.get(username='admin'); u.is_superuser = True; u.is_staff = True; u.save()"
```

(Additional Authelia users are unprivileged by design — grant them group
membership or permissions through the frontend as the admin user.)

**Frontend cannot reach the registry (errors on pages listing applications)** —
check from inside the container:
`docker exec qcrboxfrontend-server-1 python -c "import urllib.request; print(urllib.request.urlopen('http://qcrbox-registry:8000/api/healthz').read())"`.
The registry container must be healthy and both containers on `qcrbox_qcrbox-net`.

**Changed `authelia_config.yml`** — restart Authelia:
`docker restart qcrbox-qcrbox-authelia-1`. (User/group changes in the LLDAP UI
need no restart.)

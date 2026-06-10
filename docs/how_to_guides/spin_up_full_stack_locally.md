# Spinning up the Full QCrBox Stack Locally

This guide walks through running the complete QCrBox system on a local machine:
the QCrBox backend (registry, message bus, application containers) behind the
Traefik reverse proxy with Authelia authentication, plus the
[QCrBoxFrontend](https://github.com/QCrBox/QCrBoxFrontend) web application with
single sign-on.

For details on the authentication setup itself, see
[Setting up Authelia Authentication](setup_authelia_authentication.md).
If you prefer an isolated VM (no `/etc/hosts` editing, freshly generated
secrets), see [Deploying QCrBox to a VM](deploy_qcrbox_to_a_vm.md) instead.

## What you end up with

| URL | Service | Authentication |
| --- | ------- | -------------- |
| `https://localhost.local` | Web frontend (Django) | Authelia (SSO) |
| `https://auth.localhost.local` | Authelia login portal | — |
| `https://api.registry.localhost.local` | Registry REST API | Authelia |
| `https://<app>.gui.localhost.local` | noVNC GUI of an application (e.g. `olex2`) | Authelia |
| `https://traefik.localhost.local` | Traefik dashboard | Authelia |

One Authelia login (dev default: `admin` / `changeme`) covers all of them. The
frontend recognises the Authelia user automatically via the `Remote-User`
header — its own login page is not used.

## Prerequisites

1. QCrBox development environment set up
   (see [Setting up a development environment](set_up_a_dev_environment.md))
2. The `QCrBoxFrontend` repository checked out next to `QCrBox`
   (both repos in the same parent directory is assumed below)
3. Docker running

## Step 1: DNS configuration

`/etc/hosts` does not support wildcards, so every subdomain you want to use
needs an entry. Add one line (extend the `gui` list with the applications you
use):

```text
127.0.0.1   localhost.local auth.localhost.local api.registry.localhost.local traefik.localhost.local olex2.gui.localhost.local dummy-gui.gui.localhost.local qcrbox-quality.gui.localhost.local
```

**Note for WSL users:** add the same line to the Windows hosts file
(`C:\Windows\System32\drivers\etc\hosts`) if you browse from Windows; see the
WSL section in [the Authelia guide](setup_authelia_authentication.md) for
port-forwarding details.

## Step 2: Start the QCrBox backend

From the `QCrBox` repository:

```bash
devbox shell

# Optional sanity check of the authentication setup
bash scripts/devbox/test_qcb_with_authelia.sh

# Start everything (or list specific applications instead of --all)
qcb up --all
```

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
Traefik at `https://localhost.local`. This is required for the single sign-on
header to be trustworthy.

## Step 4: Log in and set up users

1. Open `https://localhost.local` in a browser. You will be redirected to the
   Authelia portal. Accept the self-signed-certificate warning (local
   development uses Traefik's default certificate; real deployments use
   Let's Encrypt).
2. Log in with the development credentials `admin` / `changeme`.
3. You land in the frontend, logged in as `admin` — the Django user is created
   automatically on first visit.
4. In the frontend, create at least one group (Groups → Create Group) and
   assign your user to it; data uploads require a group.

**How accounts work:** Authelia owns credentials and (optional) two-factor
authentication — users are defined in
`services/core/qcrbox_auth/users_database.yml`. The frontend keeps its own user
records (auto-created on first visit, matched by username) for group membership
and dataset permissions. The Django superuser from `environment.env` is only
needed for the Django admin interface at `https://localhost.local/admin`.

## Step 5: Verify

```bash
# Health check, no login required
curl -k https://api.registry.localhost.local/api/healthz

# Everything else redirects to the login portal when unauthenticated
curl -k -o /dev/null -w '%{http_code} %{redirect_url}\n' https://localhost.local/
# -> 302 https://auth.localhost.local/?rd=...
```

In the browser (logged in): open a dataset in the frontend and start an
interactive session — the GUI opens in a new tab on
`https://<app>.gui.localhost.local` without a second login.

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

**Browser shows the Authelia portal again when opening a GUI tab** — the GUI
subdomain is missing from `/etc/hosts`, so the session cookie (scoped to
`localhost.local`) is fine but the name does not resolve; or the cookie was
issued for a different domain — clear cookies for `localhost.local`.

**Logged in, but the frontend shows no data / cannot upload** — your user is
not in any group yet. Create a group and add the user (Step 4.4).

**Frontend cannot reach the registry (errors on pages listing applications)** —
check from inside the container:
`docker exec qcrboxfrontend-server-1 python -c "import urllib.request; print(urllib.request.urlopen('http://qcrbox-registry:8000/api/healthz').read())"`.
The registry container must be healthy and both containers on `qcrbox_qcrbox-net`.

**Changed `users_database.yml` or `authelia_config.yml`** — restart Authelia:
`docker restart qcrbox-qcrbox-authelia-1`.

# Authentication in QCrBox (Authelia + LLDAP)

This guide explains how authentication works in QCrBox and how to manage it.
For step-by-step setup instructions, see
[Spinning up the full QCrBox stack locally](spin_up_full_stack_locally.md);
for server deployments, see [Deploying QCrBox to a VM](deploy_qcrbox_to_a_vm.md).

## Architecture

```text
Browser ── Traefik (HTTPS :443) ── forwardAuth ── Authelia ── LDAP ── LLDAP
                 │                                   │
                 └── routes to frontend / API /      └── login portal at
                     GUIs after successful auth          auth.<domain>
```

Three components share the work:

- **Traefik** terminates TLS and applies the `authelia-auth` forwardAuth
  middleware to every public route. Requests without a valid session are
  redirected to the login portal.
- **Authelia** is the authentication portal and policy engine
  (`services/core/qcrbox_auth/authelia_config.yml`): session cookies scoped
  to `<domain>`, access-control rules, optional TOTP two-factor, brute-force
  regulation.
- **LLDAP** stores the accounts and groups, with a web UI at
  `https://users.<domain>`.

After login, Traefik forwards the `Remote-User` / `Remote-Groups` headers to
the services; the web frontend uses `Remote-User` for single sign-on.

**Internal access is unauthenticated by design:** services on the
`qcrbox-net` docker network reach the registry directly at
`http://qcrbox-registry:8000`, bypassing Traefik. This is also how `qcb`
commands and the frontend's API client work — they never need an Authelia
login. For host-side dev/test tooling (robot tests, `qcrbox-test`), the
registry is additionally published on the **loopback interface only** at
`http://127.0.0.1:11000` — never reachable from the network.

## Access control rules

Defined in `authelia_config.yml` (first match wins):

| Route | Policy |
| ----- | ------ |
| `api.registry.<domain>/api/healthz` | public (bypass) |
| `api.registry.<domain>` | any logged-in user |
| `*.gui.<domain>` | any logged-in user |
| `users.<domain>`, `traefik.<domain>` | members of `lldap_admin` only |
| everything else | deny |

Consider raising the GUI rule to `two_factor` for internet deployments — GUI
sessions grant shell-equivalent access.

## User management

Open `https://users.<domain>` (LLDAP web UI; `lldap_admin` members only — the
built-in `admin` account is one, its password is `LLDAP_ADMIN_PASSWORD` from
the env file, `changeme` in development). There you can create and delete
users, manage groups, and reset passwords. New users can log in at the
Authelia portal immediately, no restart needed.

QCrBox dataset/research-group permissions are still managed in the web
frontend (Django): an LLDAP account controls *who can log in*, the frontend
controls *what data they see*. New users start without any frontend group and
must be added to one by a frontend admin.

### Future: ORCID / federated login

Authelia cannot delegate authentication to upstream identity providers such
as ORCID. If federated login becomes a requirement, the planned path is to
replace Authelia with **Authentik** or **Keycloak** — both can use this LLDAP
directory as a user source, so accounts created now carry over, and both
support forward-auth so the Traefik/Django integration survives the swap.

## Configuration reference

`services/core/qcrbox_auth/authelia_config.yml` — Authelia configuration.
`{{ env "..." }}` placeholders are expanded from container environment
variables (`X_AUTHELIA_CONFIG_FILTERS=template`). Sessions last 1 h
(15 min inactivity); Authelia state lives in the `qcrbox-authelia-data`
volume, accounts in `qcrbox-lldap-data`.

Environment variables (`.env.dev` / `.env.prod`; regenerate every secret for
any deployment — the committed `.env.dev` values are public):

| Variable | Purpose |
| -------- | ------- |
| `QCRBOX_DOMAIN` | Domain everything is served under |
| `AUTHELIA_JWT_SECRET` | Password-reset token signing (`openssl rand -hex 32`) |
| `AUTHELIA_SESSION_SECRET` | Session encryption (`openssl rand -hex 64`) |
| `AUTHELIA_STORAGE_ENCRYPTION_KEY` | Authelia database encryption (`openssl rand -hex 32`) |
| `LLDAP_JWT_SECRET`, `LLDAP_KEY_SEED` | LLDAP internals (`openssl rand -hex 32`) |
| `LLDAP_ADMIN_PASSWORD` | Password of the `admin` account |
| `QCRBOX_TLS_CERT_RESOLVER`, `QCRBOX_ACME_EMAIL` | Empty = self-signed; `letsencrypt` + email for real certificates |

Validate a config change without restarting the stack:

```bash
docker run --rm \
  -v $PWD/services/core/qcrbox_auth/authelia_config.yml:/config/configuration.yml:ro \
  -e X_AUTHELIA_CONFIG_FILTERS=template -e QCRBOX_DOMAIN=qcrbox.localhost \
  -e QCRBOX_AUTH_JWT_SECRET=x -e QCRBOX_AUTH_SESSION_SECRET=x \
  -e QCRBOX_AUTH_STORAGE_ENCRYPTION_KEY=x -e QCRBOX_AUTH_LDAP_PASSWORD=x \
  authelia/authelia:4.38 authelia validate-config --config /config/configuration.yml
```

## Troubleshooting

**Authelia container not starting** — `docker logs qcrbox-qcrbox-authelia-1
--tail 50`. Usual causes: missing env vars, a config syntax error (run
`validate-config` above), or LLDAP not healthy yet (Authelia checks the LDAP
connection at startup).

**Redirect loop at the login portal** — the session cookie predates a change
of `QCRBOX_DOMAIN` or `AUTHELIA_SESSION_SECRET`: clear cookies for the domain
(or use a private window).

**403 "Access denied" on `users.`/`traefik.`** — the logged-in user is not in
the `lldap_admin` group (by design).

**Certificate warnings in the browser** — expected with the self-signed
development certificate; click "Advanced → proceed" (and use `curl -k` on the
command line). Real deployments use Let's Encrypt or a supplied certificate.

**Config changed but not picked up** — `authelia_config.yml` is read at
startup: `docker restart qcrbox-qcrbox-authelia-1`. User/group changes in the
LLDAP UI need no restart.

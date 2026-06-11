# Setting up Authelia Authentication for QCrBox

This guide describes how to set up and use Authelia authentication for securing external access to the QCrBox Registry API via Traefik reverse proxy.

## Overview

By default, QCrBox services are accessible only on localhost. When deploying QCrBox for LAN or web access, the Registry API should be protected with authentication. This guide covers:

- **Authelia**: Self-hosted authentication service with local user database
- **Traefik**: Reverse proxy with ForwardAuth middleware for authentication
- **HTTPS**: Self-signed certificates for secure communication

Internal services (within the Docker network) can still access the registry without authentication.

## Architecture

```
Browser/Client → Traefik (HTTPS:443) → Authelia (Auth Check) → Registry API
                                              ↓
                                         Login Page
```

**Key components:**
- **External access**: `https://api.registry.localhost.local:443` (requires authentication)
- **Internal access**: `http://qcrbox-registry:8000` (no authentication)
- **Auth portal**: `https://auth.localhost.local:443`

## Prerequisites

Before starting, ensure you have:

1. QCrBox development environment set up (see [Setting up a development environment](set_up_a_dev_environment.md))
2. Docker and Docker Compose running
3. Devbox shell activated (`devbox shell`)

## Step 1: DNS Configuration

Add entries to `/etc/hosts` for the localhost domains:

```bash
sudo nano /etc/hosts
```

Add this line (extend the `gui` list with the applications you use):
```
127.0.0.1   localhost.local auth.localhost.local api.registry.localhost.local traefik.localhost.local olex2.gui.localhost.local
```

Save and exit (Ctrl+X, Y, Enter).

**Verify DNS resolution:**
```bash
ping -c 1 auth.localhost.local
ping -c 1 api.registry.localhost.local
# Both should resolve to 127.0.0.1
```

## Step 2: Verify Environment Variables

The `.env.dev` file should already contain the necessary Authelia secrets. Verify they exist:

```bash
grep AUTHELIA .env.dev
```

Expected output should show:
```
QCRBOX_DOMAIN=localhost.local
AUTHELIA_JWT_SECRET=<generated-secret>
AUTHELIA_SESSION_SECRET=<generated-secret>
AUTHELIA_STORAGE_ENCRYPTION_KEY=<generated-secret>
```

If these are missing, they need to be regenerated (contact the development team).

## Step 3: Start QCrBox Services

### Using qcb command (Recommended)

From within the devbox shell:

```bash
# Start all core services including Authelia
qcb up --all
```

Wait for services to start (30-60 seconds). Services will start in this order:
1. Syslog
2. NATS
3. Traefik (reverse proxy)
4. Authelia (authentication)
5. Registry API

### Using docker compose directly

If not using devbox shell:

```bash
docker compose -f docker-compose.run.yml --env-file .env.dev up -d
```

## Step 4: Verify Services are Running

Check all containers are up and healthy:

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

**Expected services:**
- ✅ `qcrbox-qcrbox-syslog-1` - Up (healthy)
- ✅ `qcrbox-qcrbox-nats-1` - Up (healthy)
- ✅ `qcrbox-qcrbox-reverse-proxy-1` - Up (healthy)
- ✅ `qcrbox-qcrbox-authelia-1` - Up (healthy)
- ✅ `qcrbox-qcrbox-registry-1` - Up (healthy)

**Check Authelia health specifically:**
```bash
docker exec qcrbox-qcrbox-authelia-1 wget -q -O- http://localhost:9091/api/health
```

Expected output: `{"status":"OK"}`

If any service is unhealthy, check logs:
```bash
docker logs qcrbox-qcrbox-authelia-1 --tail 50
docker logs qcrbox-qcrbox-registry-1 --tail 50
```

## Step 5: Test Registry Access

### Test health endpoint (no authentication required)

```bash
curl -k https://api.registry.localhost.local:443/api/healthz
```

Expected output: `{"status":"ok"}`

**Note:** The `-k` flag bypasses certificate verification for self-signed certificates.

### Test authenticated access via browser

1. **Open browser** and navigate to:
   ```
   https://api.registry.localhost.local:443
   ```

2. **Accept certificate warning**:
   - Chrome/Edge: Click "Advanced" → "Proceed to api.registry.localhost.local (unsafe)"
   - Firefox: Click "Advanced" → "Accept the Risk and Continue"

3. **You'll be redirected** to Authelia login page:
   ```
   https://auth.localhost.local:443
   ```

4. **Login with default credentials**:
   - Username: `admin`
   - Password: `changeme`

5. **After successful login**, you'll be redirected back to the registry API

6. **Test accessing registry endpoints**:
   - `https://api.registry.localhost.local:443/api/applications`
   - `https://api.registry.localhost.local:443/docs` (FastAPI documentation)

## Step 6: Test Internal Service Access

Internal services within the Docker network can access the registry **without authentication**:

```bash
# Test from another container
docker exec qcrbox-qcrbox-nats-1 wget -q -O- http://qcrbox-registry:8000/api/healthz
```

Expected output: `{"status":"ok"}`

This confirms that applications running inside QCrBox can communicate with the registry directly.

## Viewing Traefik Dashboard

The dashboard is served through the reverse proxy itself and requires an
Authelia login (add `traefik.localhost.local` to `/etc/hosts` for local use):

```
https://traefik.localhost.local
```

Check these sections:

- **HTTP Routers**: Should see `authelia`, `registry-api`, `registry-healthz`, `traefik-dashboard` and the `to-<app>-*` GUI routers
- **HTTP Services**: Should see `authelia-service`, `registry-service`
- **HTTP Middlewares**: Should see `authelia-auth` (ForwardAuth middleware) and `security-headers`

## User Management

Users and groups live in **LLDAP**, a lightweight LDAP server with a web UI
that Authelia uses as its authentication backend
(`services/core/qcrbox_auth/authelia_config.yml`, `implementation: lldap`).

Open `https://users.<domain>` (e.g. `https://users.qcrbox.localhost`) and log
in. Only members of the `lldap_admin` group can reach this page (enforced by
an Authelia access-control rule). The built-in `admin` account is a member;
its password comes from `LLDAP_ADMIN_PASSWORD` in the env file
(`changeme` in development).

From the LLDAP UI you can:

- **Create and delete users** (username, email, display name, password).
  New users can log in at the Authelia portal immediately — no restart needed.
- **Manage groups**. Two group names have meaning today: `lldap_admin`
  (access to this UI and the Traefik dashboard) and group membership in
  general is forwarded to applications in the `Remote-Groups` header.
- **Reset passwords** for any user.

Note that QCrBox dataset/research-group permissions are still managed in the
web frontend (Django) — an LLDAP account controls *who can log in*, while the
frontend controls *what data they see*. New users start without any frontend
group and must be added to one by a frontend admin.

### Future: ORCID / federated login

Authelia cannot delegate authentication to upstream identity providers such
as ORCID. If federated login becomes a requirement, the planned path is to
replace Authelia with **Authentik** or **Keycloak** — both can use this LLDAP
directory as a user source, so accounts created now carry over, and both
support forward-auth so the Traefik/Django integration survives the swap.

## Troubleshooting

### DNS not resolving

**Symptom:** `curl: (6) Could not resolve host: auth.localhost.local`

**Fix:**
```bash
# Verify /etc/hosts entry
cat /etc/hosts | grep localhost.local

# If missing, add it:
echo "127.0.0.1   localhost.local auth.localhost.local api.registry.localhost.local" | sudo tee -a /etc/hosts
```

### Certificate warnings in browser

**This is expected behavior** for development environments using self-signed certificates.

**Options:**
- Click "Advanced" and proceed (safe for localhost development)
- Use `curl -k` flag to bypass certificate verification
- For production, use proper certificates from Let's Encrypt or another CA

### Authelia not starting

**Check logs:**
```bash
docker logs qcrbox-qcrbox-authelia-1 --tail 100
```

**Common issues:**
- Missing environment variables in `.env.dev`
- Configuration syntax errors in `authelia_config.yml`
- Port conflicts

**Fix:**
```bash
# Restart Authelia
docker compose -f docker-compose.run.yml --env-file .env.dev restart qcrbox-authelia

# Verify it becomes healthy
docker ps | grep authelia
```

### Registry not accessible

**Check registry is running:**
```bash
docker ps | grep registry
```

**Test internal access:**
```bash
docker exec qcrbox-qcrbox-registry-1 curl http://localhost:8000/api/healthz
```

**Check registry logs:**
```bash
docker logs qcrbox-qcrbox-registry-1 --tail 50
```

### Authentication redirect loop

**Symptom:** Keeps redirecting to login page

**Possible causes:**
- Cookies blocked by browser
- Session secret changed without clearing cookies
- Time synchronization issues

**Fix:**
```bash
# Clear browser cookies for localhost.local domain
# Or use incognito/private browsing mode

# Verify Authelia health
docker exec qcrbox-qcrbox-authelia-1 wget -q -O- http://localhost:9091/api/health
```

### Port conflicts

**Symptom:** `Error: bind: address already in use`

**Check what's using the port:**
```bash
sudo lsof -i :443
sudo lsof -i :12345
```

**Fix:** Stop the conflicting service or change ports in `.env.dev`

### Browser access from Windows (WSL users)

**Symptom:** `curl` works from WSL terminal but Windows browser cannot access `https://api.registry.localhost.local:443`

This is a common WSL2 networking issue. WSL2 uses a virtual network interface, and Windows needs special configuration to access WSL services.

**Solution 1: Update Windows hosts file and use WSL IP**

1. **Get your WSL IP address:**
   ```bash
   # Run in WSL terminal
   ip addr show eth0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}'
   ```
   Example output: `172.24.144.23`

2. **Update Windows hosts file:**
   - Open Notepad as Administrator
   - Open `C:\Windows\System32\drivers\etc\hosts`
   - Add these lines (replace with your WSL IP):
   ```
   172.24.144.23   localhost.local
   172.24.144.23   auth.localhost.local
   172.24.144.23   api.registry.localhost.local
   ```
   - Save the file

3. **Access from Windows browser:**
   ```
   https://api.registry.localhost.local:443
   ```

**Note:** WSL IP may change after restart. You'll need to update the Windows hosts file if it does.

**Solution 2: Use WSL IP directly**

Access using the WSL IP address directly in your Windows browser:
```
https://172.24.144.23:443/api/healthz
```

**Important:** You'll still get certificate warnings because the certificate is for `localhost.local`, not the IP address.

**Solution 3: Port forwarding (automatic in older WSL versions)**

WSL2 versions may require manual port forwarding. Run in **Windows PowerShell as Administrator**:

```powershell
# Get WSL IP
wsl hostname -I

# Forward port 443 to WSL (replace WSL_IP with your WSL IP)
netsh interface portproxy add v4tov4 listenport=443 listenaddress=0.0.0.0 connectport=443 connectaddress=WSL_IP
netsh interface portproxy add v4tov4 listenport=12345 listenaddress=0.0.0.0 connectport=12345 connectaddress=WSL_IP
```

To remove port forwarding:
```powershell
netsh interface portproxy delete v4tov4 listenport=443 listenaddress=0.0.0.0
netsh interface portproxy delete v4tov4 listenport=12345 listenaddress=0.0.0.0
```

**Solution 4: Access with browser in WSL**

Install a text-based browser in WSL:
```bash
sudo apt-get install lynx
lynx https://api.registry.localhost.local:443
```

Or set up X server (VcXsrv, WSLg) to run graphical browsers from WSL.

## Configuration Files Reference

### Authelia Configuration

Main configuration: `services/core/qcrbox_auth/authelia_config.yml`

Key settings:
- Server listens on port 9091 (internal)
- Session domain: `localhost.local`
- Session expiration: 1 hour
- Access control: Public for `/api/healthz`, requires authentication for all other `/api/*` paths

### User Database

Location: `services/core/qcrbox_auth/users_database.yml`

Format:
```yaml
users:
  <username>:
    displayname: "<Display Name>"
    password: "$argon2id$..."  # Argon2id hash
    email: user@example.com
    groups:
      - group1
      - group2
```

### Environment Variables

Located in `.env.dev`:
- `QCRBOX_DOMAIN`: Domain for QCrBox services (e.g., `localhost.local`)
- `AUTHELIA_JWT_SECRET`: Secret for JWT token signing
- `AUTHELIA_SESSION_SECRET`: Secret for session encryption
- `AUTHELIA_STORAGE_ENCRYPTION_KEY`: Secret for database encryption

## Using qcb Commands with Authentication

Commands from the devbox shell automatically use internal Docker network access and **do not require authentication**:

```bash
# These work without Authelia login
qcb list applications
qcb registry status
qcb create application my-app
```

The `qcb` tool connects to `http://qcrbox-registry:8000` internally, bypassing Traefik and Authelia.

## Deploying on an Internet-Facing VM

The settings in this repository default to a safe local-development setup. The
checklist below covers everything that must change for a deployment on a VM
that is reachable from the internet.

**Trust model:** all Authelia accounts are mutually trusted. Every logged-in
user can see all data, all calculations, and shares the same GUI desktop
sessions. Only create accounts for people who may see everything; QCrBox does
not yet provide per-user data isolation.

### DNS

Create A/AAAA records pointing at the VM for:

- `auth.<domain>` (Authelia portal)
- `api.registry.<domain>` (registry API)
- `traefik.<domain>` (dashboard)
- `*.gui.<domain>` (one per GUI application, or a wildcard)

### Environment (`.env.prod`)

1. **Domain**: set `QCRBOX_DOMAIN` to your actual domain (e.g. `qcrbox.example.com`).
2. **Secrets**: replace every `CHANGEME` value. Generate with `openssl rand -hex 32`
   (JWT, storage encryption) and `openssl rand -hex 64` (session). Never reuse
   the committed `.env.dev` values — they are public.
3. **TLS**: keep `QCRBOX_TLS_CERT_RESOLVER=letsencrypt` and set `QCRBOX_ACME_EMAIL`
   to a monitored address. Certificates are issued automatically via HTTP-01;
   ports 80 and 443 must be reachable from the internet for this to work.
4. **NATS**: keep `QCRBOX_NATS_BIND_ADDRESS=127.0.0.1`. NATS has no
   authentication; if it is ever exposed, anyone can control the pipeline.

### Users

1. Replace the default `admin`/`changeme` user in
   `services/core/qcrbox_auth/users_database.yml` (hash generation:
   `docker run --rm authelia/authelia:4.38 authelia crypto hash generate argon2 --password '...'`).
2. Encourage (or enforce, by switching the GUI rules in `authelia_config.yml`
   from `one_factor` to `two_factor`) TOTP enrolment — GUI sessions grant
   shell-equivalent access to the shared data.

### VM hardening

1. **Firewall**: allow only 22, 80 and 443. Note that Docker publishes ports by
   manipulating iptables directly and **bypasses ufw** — do not rely on ufw to
   protect a port that docker-compose publishes on `0.0.0.0`. The compose files
   in this repository bind everything except 80/443 to `127.0.0.1` for exactly
   this reason; keep it that way.
2. **SSH**: key-based authentication only (`PasswordAuthentication no`),
   consider fail2ban.
3. **Updates**: enable unattended upgrades for the OS and renew the QCrBox
   images regularly.
4. **Verify from outside** after starting the stack: from a machine that is not
   the VM, check that only 22/80/443 answer (e.g. `nmap <host>`), that
   `http://…` redirects to HTTPS, and that every subdomain redirects to the
   Authelia login when unauthenticated.

### Operational considerations

1. **Backups**: back up the docker volumes (`qcrbox-registry-db`,
   `qcrbox-nats-storage`, `qcrbox-authelia-data`) and `shared_files/`.
2. **Password resets**: the notifier writes reset links to a file inside the
   Authelia container (`/config/notification.txt`). For real users configure an
   SMTP notifier in `authelia_config.yml` instead.
3. **External session/user storage** (Redis/PostgreSQL) is only needed once you
   scale beyond a single VM.

## Quick Commands Reference

```bash
# Start all services
qcb up --all

# Stop all services
qcb down

# View logs
docker logs qcrbox-qcrbox-authelia-1 -f
docker logs qcrbox-qcrbox-registry-1 -f

# Restart Authelia
docker compose -f docker-compose.run.yml --env-file .env.dev restart qcrbox-authelia

# Check service health
docker ps --format "table {{.Names}}\t{{.Status}}"

# Test health endpoints
curl -k https://api.registry.localhost.local:443/api/healthz
docker exec qcrbox-qcrbox-authelia-1 wget -q -O- http://localhost:9091/api/health

# Generate password hash
docker run --rm authelia/authelia:4.38 authelia crypto hash generate argon2 --password 'mypassword'
```

## Success Criteria

✅ All containers show `healthy` status  
✅ `https://auth.localhost.local:443` displays Authelia login page  
✅ `https://api.registry.localhost.local:443/api/healthz` returns `{"status":"ok"}`  
✅ Login with credentials redirects to registry API  
✅ Internal access works without authentication  
✅ Traefik dashboard shows correct routing configuration  

**Your QCrBox cluster is now secured with Authelia authentication! 🎉**

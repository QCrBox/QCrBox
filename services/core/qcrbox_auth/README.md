# QCrBox Authentication with Authelia

This directory contains configuration files for Authelia authentication service.

## Configuration Files

- `authelia_config.yml` - Main Authelia server configuration
- `users_database.yml` - Local user database with password hashes
- `.gitignore` - Excludes generated database and notification files

## Initial Setup

### 1. Generate Required Secrets

Add these to your `.env.dev` or `.env.prod` file:

```bash
# Generate JWT secret (32 bytes = 64 hex characters)
openssl rand -hex 32

# Generate session secret (64 bytes = 128 hex characters)
openssl rand -hex 64

# Generate storage encryption key (32 bytes = 64 hex characters)
openssl rand -hex 32
```

Add to `.env.dev`:
```bash
AUTHELIA_JWT_SECRET=<output-from-first-command>
AUTHELIA_SESSION_SECRET=<output-from-second-command>
AUTHELIA_STORAGE_ENCRYPTION_KEY=<output-from-third-command>
```

### 2. Generate Admin Password Hash

Replace the default password hash in `users_database.yml`:

```bash
docker run --rm authelia/authelia:4.38 authelia crypto hash generate argon2 --password 'your-secure-password'
```

Copy the output (starting with `$argon2id$...`) and replace the hash in `users_database.yml` for the admin user.

### 3. Add Additional Users

To add more users, add entries to `users_database.yml`:

```yaml
users:
  admin:
    # ... existing admin config ...
  
  scientist1:
    displayname: "Scientist One"
    password: "$argon2id$v=19$m=65536,t=3,p=4$..."  # Generate with command above
    email: scientist1@example.com
    groups:
      - users
```

## Access URLs

**Development (using devbox shell):**
- Start services: `devbox shell` then `qcb up --all`
- **Login UI**: http://auth.localhost:12345 (development)
- **Registry API**: http://api.registry.localhost:12345 (requires authentication)
- **Health Check**: http://api.registry.localhost:12345/api/healthz (no auth required)

## Production Deployment

For production:

1. Update domain in `.env.prod`: `QCRBOX_DOMAIN=yourdomain.com`
2. Use HTTPS with valid TLS certificates
3. Change session domain in `authelia_config.yml` to match your domain
4. Update access_control domains to match your production domain

## Troubleshooting

Check Authelia logs:
```bash
docker logs qcrbox-authelia
```

Verify configuration:
```bash
docker exec qcrbox-authelia authelia validate-config /config/configuration.yml
```

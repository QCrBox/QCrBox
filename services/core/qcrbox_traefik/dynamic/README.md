# Traefik dynamic configuration

Files in this directory are loaded (and watched) by Traefik's file provider.

Its main purpose is serving a supplied TLS certificate instead of the
self-signed default or Let's Encrypt: place `qcrbox.crt` / `qcrbox.key` here
together with a `tls.yml` such as

```yaml
tls:
  stores:
    default:
      defaultCertificate:
        certFile: /etc/traefik/dynamic/qcrbox.crt
        keyFile: /etc/traefik/dynamic/qcrbox.key
```

The certificate must cover the root domain plus the subdomains
`auth.<domain>`, `api.registry.<domain>`, `traefik.<domain>` and
`*.gui.<domain>`. Note that a single wildcard `*.<domain>` does **not** cover
the two-level `*.gui.<domain>` names — request a SAN certificate listing both
wildcards.

`scripts/deployment/provision_qcrbox.sh --tls-cert ... --tls-key ...` writes
these files automatically. Certificates and keys are git-ignored; never commit
private keys.

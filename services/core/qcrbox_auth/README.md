# QCrBox Authentication Configuration

`authelia_config.yml` configures Authelia, QCrBox's authentication portal and
access-control engine. Accounts and groups live in LLDAP (see the
`qcrbox-lldap` service in the top-level compose files) and are managed via
its web UI at `https://users.<QCRBOX_DOMAIN>`.

`{{ env "..." }}` placeholders in the config are expanded from container
environment variables (`X_AUTHELIA_CONFIG_FILTERS=template`), which the
compose files map from the `AUTHELIA_*` / `LLDAP_*` variables in
`.env.dev` / `.env.prod`.

Full documentation:

- How it works, user management, configuration reference and troubleshooting:
  [`docs/how_to_guides/setup_authelia_authentication.md`](../../../docs/how_to_guides/setup_authelia_authentication.md)
- Local setup: [`docs/how_to_guides/spin_up_full_stack_locally.md`](../../../docs/how_to_guides/spin_up_full_stack_locally.md)
- Server deployment: [`docs/how_to_guides/deploy_qcrbox_to_a_vm.md`](../../../docs/how_to_guides/deploy_qcrbox_to_a_vm.md)

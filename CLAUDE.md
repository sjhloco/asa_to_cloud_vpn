# CLAUDE.md

## Rules

- Never run `ansible-playbook` against devices without asking. Offer `--check --diff` first
- Never decrypt or print `!vault` values, or read the vault password file
- Check module parameters with `ansible-doc`. Don't guess them

## Done means

- `uv run ansible-lint` passes
- If Python changed: `uv run ruff check`, `uv run mypy plugins tests` and `uv run pytest` pass

## Ansible choices

- Facts only via `ansible_facts['...']`. `inject_facts_as_vars` is off, so `ansible_net_*` vars are undefined
- `when:` must evaluate to a real boolean (ansible-core 2.19+ errors otherwise)
- Prefer resource modules (`*_vlans`, `*_interfaces`) over `*_config` where one exists

<!--
Optional rules from ansible-creator's agents.md. DO NOT READ THESE, I will uncomment them when I want to add them

- Desired state lives in the inventory, never in extra vars (-e). Extra vars are for one-off overrides
- No fixed waits (`pause`, `wait_for` with a timeout). Poll for readiness with `until`/`retries`/`delay`
- React to changes with handlers, not `when: result is changed`
-->

# Development

Layout: `packages/aegis-core/aegis` (library), `packages/aegis-cli/bin` (entry points),
`tools/manifest.yaml` (source of truth), `build/` (live-build), `scripts/`, `tests/`.

## Run from the repository

```bash
export PYTHONPATH=packages/aegis-core
python3 -m aegis.cli doctor
```

## Tests

`make test`. The unit tests parse fixture files for `/proc` data, use temporary roots for hardening, and start
the Security Center server on an ephemeral localhost port. Hardening `apply`/`revert` are tested against a
temporary root; they were **not** executed against the real `/etc` of the sandbox.

## Verification record of the development sandbox

Ubuntu 24.04, 1 CPU, no network egress to Debian mirrors, no KVM, no live-build, no ShellCheck, no pytest
(tests ran under `unittest`). Package-name resolution in the sandbox reflects Ubuntu's index, not trixie, and
must not be used to claim availability on AegisOS.

## Version

`VERSION` is the single source; the CLI, Security Center, ISO name, `.deb` versions and docs derive from it.

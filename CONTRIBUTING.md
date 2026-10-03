# Contributing to AegisOS

## Development setup

```bash
git clone <repository-url> aegisos && cd aegisos
sudo apt-get install python3 python3-yaml python3-pytest shellcheck   # Debian/Ubuntu
make test
```

## Build and test

- `make test` - manifest validation, `bash -n`, ShellCheck (if installed), Python tests
- `make verify` - static repository verification
- `make debs` - build the Aegis `.deb` packages
- `make build` - build the ISO (Debian 13 + root; see `docs/BUILD.md`)

Tests use `unittest.TestCase` classes so they run under both `pytest` and `python3 -m unittest`.

## Coding standards

- Python 3.11+, standard library plus PyYAML only. Real data only: never fake output or values.
- Shell: `set -euo pipefail`, ShellCheck-clean, no secrets.
- Anything that cannot be tested must be labelled **NOT VERIFIED** in code comments and docs.

## Adding a tool

1. Add an entry to `tools/manifest.yaml`. Required: `name`, `category`, `tier`, `installation_method`,
   `description`. Optional: `also`, `package` (apt only), `license`, `homepage`, `documentation`,
   `redistribution`, `version`, `bundled`.
2. **Verify before you fill in metadata.** License, homepage and redistribution status must come from the
   upstream project or Debian package metadata. If unsure, leave `unverified`. Never invent URLs or licenses.
3. `bundled: true` is only accepted when the license is verified, redistribution is `allowed`, and the
   method is `apt`. Proprietary or unclear-license software must not be bundled.
4. Run `python3 -m aegis.cli manifest validate` (with `PYTHONPATH=packages/aegis-core`), then
   `python3 scripts/gen-tool-docs.py` to regenerate `docs/TOOLS.md` and `docs/TOOL-LICENSING.md`.
5. Offensive tools: make sure the category carries a `usage_notice`.

## Pull requests

Fill in the PR template with the exact commands you ran. One logical change per PR.

## Issues

Use the templates. Include `aegis version` and `aegis doctor` output. Report vulnerabilities privately per
`SECURITY.md`.

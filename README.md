# AegisOS

**Defend. Analyze. Understand.**

An open-source Linux distribution project for cybersecurity, defensive security, digital forensics,
network analysis, reverse engineering, and security education. Base: Debian 13 "trixie".

> **Project status: pre-alpha (0.1.0).** The tooling exists and is tested. An ISO has been built by
> GitHub Actions and booted (live session, UEFI) in VMware Workstation. Installation to disk, VirtualBox
> and most tools are untested - see [Verification status](#verification-status).

## Features

- `aegis` tool manager that orchestrates `apt` (it does not replace it), driven by `tools/manifest.yaml`
- 138 manifest entries across 18 categories and 12 install profiles
- `aegis-net` for real network information read from `/proc` and `/sys`
- `aegis doctor` health checks with exit codes (0 PASS, 1 WARN, 2 FAIL)
- Optional, reversible hardening (`aegis hardening status|audit|apply|revert`)
- Security Center: read-only dashboard (text, JSON, or local web UI bound to 127.0.0.1)
- live-build configuration for a UEFI amd64 hybrid ISO with XFCE
- Own branding (logo, wallpaper, banner); no third-party distribution branding

## Verification status

| Area | Status |
|------|--------|
| Aegis CLI, doctor, hardening, net, Security Center backend, manifest validator | VERIFIED by tests in the dev sandbox (Ubuntu 24.04 host) |
| `.deb` package build and installed-layout run | VERIFIED (dpkg-deb, extracted layout) |
| Booted AegisOS 0.1.0 live image in VMware Workstation 17 Pro (UEFI): `os-release`, `aegis doctor`, `aegis security-center`, `aegis-net`, `aegis hardening apply/revert`, `aegis manifest check-packages` | VERIFIED once, 2026-10-04 (see `docs/VMWARE.md`) |
| ShellCheck, pytest, manifest validation, `.deb` build, static verification in CI | VERIFIED: workflow `test` run #4 green (after fixing the findings of runs #1-#3) |
| ISO package lists and core-tier package names on `debian:trixie` | VERIFIED by the same green run (name resolution only; installation of every package is not separately tested) |
| Debian package names resolving on trixie | NOT VERIFIED (CI job `trixie-packages` checks) |
| ISO build in GitHub Actions, live boot with UEFI | VERIFIED (build #1 succeeded; boot observed in VMware) |
| Installer ("Start installer" entry exists), installation to disk | NOT VERIFIED |
| VMware Workstation: display auto-resize | observed NOT working, cause unknown |
| VirtualBox | NOT VERIFIED |
| Desktop wallpaper | VERIFIED in VMware after a fix (menu categories NOT VERIFIED) |

No screenshots are included in the repository yet.

## Quick start (verified commands)

```bash
git clone <repository-url> aegisos
cd aegisos
make test          # manifest validation, shell syntax, unit/integration tests
make verify        # static repository verification
make debs          # build the Aegis .deb packages into dist/debs
```

Run the tools straight from the repository:

```bash
export PYTHONPATH=packages/aegis-core
python3 -m aegis.cli version
python3 -m aegis.cli search nmap
python3 -m aegis.cli profile blue-team --dry-run
python3 -m aegis.cli doctor
python3 -m aegis.net_cli interfaces
python3 -m aegis.cli security-center
```

## Building the ISO (NOT VERIFIED)

Requires Debian 13 (or a `debian:trixie` privileged container) with root. See [docs/BUILD.md](docs/BUILD.md).

```bash
make build      # expected result: dist/AegisOS-<VERSION>-amd64.iso and dist/SHA256SUMS
```

## Aegis CLI

| Command | Purpose |
|---------|---------|
| `aegis version` / `banner` / `welcome` | identity and first-boot guide |
| `aegis search <term>` / `info <tool>` / `list` / `category [name]` | explore the manifest |
| `aegis install <tool...>` / `remove <tool...>` | apt-backed, with `--dry-run` and `--yes` |
| `aegis profile [name]` | list or install a profile |
| `aegis update` / `upgrade` | `apt-get update` / `upgrade` after repository validation |
| `aegis doctor` | health checks |
| `aegis hardening status\|audit\|apply\|revert` | optional hardening |
| `aegis manifest validate\|check-packages\|package-list` | manifest tooling |
| `aegis security-center [--json] [--serve --open]` | dashboard |

Availability labels: `OFFLINE AVAILABLE` (installed), `ONLINE AVAILABLE` (installable from configured
repositories), `REQUIRES INTERNET` (external/container tools or unresolved packages). Not every tool
works offline; see [docs/TOOLS.md](docs/TOOLS.md).

## Documentation

[Architecture](docs/ARCHITECTURE.md) | [Build](docs/BUILD.md) | [Installation](docs/INSTALLATION.md) |
[Development](docs/DEVELOPMENT.md) | [VMware](docs/VMWARE.md) | [VirtualBox](docs/VIRTUALBOX.md) |
[Tools](docs/TOOLS.md) | [Tool licensing](docs/TOOL-LICENSING.md) | [Security](docs/SECURITY.md) |
[Troubleshooting](docs/TROUBLESHOOTING.md) | [Roadmap](docs/ROADMAP.md)

## Responsible use

Offensive-security tools are packaged for **authorized testing and education only**. Use them only on
systems you own or have written permission to test. AegisOS ships no malware, credential-theft,
persistence, or automated attack tooling.

## Licensing

Project code: Apache-2.0 (see `LICENSE`). Third-party tools keep their own licenses; the per-tool record
is in [docs/TOOL-LICENSING.md](docs/TOOL-LICENSING.md), where unverified facts are marked `unverified`.

## Contributing and security

See [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), and [SECURITY.md](SECURITY.md).

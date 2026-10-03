# AegisOS Architecture

Status of this document: design. Items marked **NOT VERIFIED** have not been
executed in any environment yet.

## 1. Base selection

### Verification record

Verified on **2026-10-03** from official Debian sources
(<https://www.debian.org/releases/>) and the live-build manual pages
(<https://manpages.debian.org/trixie/live-build/lb_config.1.en.html>):

| Fact | Value |
|------|-------|
| Current Debian stable | Debian 13 "trixie" |
| Initial release | 2025-08-09 |
| Latest point release at verification time | 13.7 (2026-09-12) |
| Previous stable | Debian 12 "bookworm", now oldstable; regular security support ended 2026-07-11, LTS until 2028-06-30 |
| Debian support model | 3 years full support + 2 years LTS |
| Next release | "forky" (currently testing) |

Trixie support dates beyond the release page (security until 2028-08-09, LTS
until 2030-06-30) come from a third-party tracker (endoflife.date), not from
debian.org directly; re-check them before 1.0.

### Decision

**AegisOS 0.x is based on Debian 13 "trixie" (stable).**

Reasons:

- It is the current stable release with the longest remaining support window.
  Basing a new project on bookworm would start it on an oldstable release whose
  regular security support has already ended.
- `apt`/`dpkg`, a large security-tool archive, UEFI-capable `grub-efi`, and
  `live-build` (the Debian Live project's ISO builder) are all in the archive.
- Long-term maintainability: security updates come from the Debian security
  team, and we do not need to carry a custom kernel.
- Rejected: Ubuntu (extra branding and snap constraints), Debian testing/sid
  (not suitable for a reproducible, supportable base), custom kernel (no
  justification).

The codename is not hardcoded in logic: it lives in one place,
`build/profiles/default.env` (`AEGIS_DEBIAN_SUITE`). Moving to the next stable
release is a one-line change plus a re-test.

## 2. ISO build architecture

- Tool: `live-build` (`lb config`, `lb build`). Option names used below were
  confirmed against the trixie `lb_config(1)` man page: `--distribution`,
  `--architectures`, `--binary-images iso-hybrid`, `--bootloaders grub-efi`,
  `--archive-areas`, `--debian-installer`, `--bootappend-live`, `--iso-*`.
- Pipeline (`scripts/build.sh`): preflight checks, `lb config` from
  `build/config/auto/config`, `lb build`, rename to
  `dist/AegisOS-<VERSION>-amd64.iso`, `sha256sum` into `dist/SHA256SUMS`,
  then `scripts/verify.sh`.
- Builder host: a Debian 13 host or `debian:trixie` container with root and
  loop/mount privileges. Building on other hosts (for example Ubuntu) is
  **NOT VERIFIED**.
- Image: UEFI-only `iso-hybrid` using `grub-efi`. **BIOS boot is not supported
  in 0.x** and is not claimed.
- Installer: the build profile selects `AEGIS_INSTALLER` (`live` for the
  Debian Installer in live mode, or `none`). The default is `live`, but
  installer behavior is **NOT VERIFIED**; a community report suggests the
  live-mode installer can be troublesome. Calamares is a roadmap candidate
  if it proves unreliable.
- Reproducibility: not claimed for 0.x. Planned for 1.0 (pinned snapshot
  mirror, fixed `SOURCE_DATE_EPOCH`).

## 3. Package architecture

Aegis software is shipped as ordinary `.deb` packages built by
`scripts/build-debs.sh` (plain `dpkg-deb`, no custom package manager):

| Package | Source dir | Contents |
|---------|-----------|----------|
| `aegis-core` | `packages/aegis-core` | Python library `aegis`: manifest, doctor, hardening, network info, Security Center backend |
| `aegis-cli` | `packages/aegis-cli` | `/usr/bin/aegis`, `/usr/bin/aegis-net` entry points |
| `aegis-tools` | `packages/aegis-tools` | `tools/manifest.yaml` and profile definitions installed to `/usr/share/aegis` |
| `aegis-security-center` | `packages/aegis-security-center` | `aegis-security-center` launcher and desktop entry |
| `aegis-branding` | `packages/aegis-branding` | os-release fragments, MOTD banner, wallpapers, theme defaults |

Runtime dependencies are limited to Python 3 and PyYAML (`python3-yaml`).

## 4. Desktop architecture

XFCE, chosen for low resource use in virtual machines and a stable,
well-packaged configuration model. Desktop defaults live in
`configs/desktop` and are copied into `/etc/skel` and
`/usr/share/aegis` via live-build `includes.chroot`. Menu categories are
defined once in `tools/manifest.yaml` (`categories:`). Desktop behavior inside
a booted image is **NOT VERIFIED**.

## 5. Repository (APT) architecture

0.x uses the official Debian trixie archive (`main contrib non-free-firmware`;
`non-free` is not enabled by default). No third-party repositories are added
silently. A dedicated Aegis APT repository is a post-1.0 roadmap item; until
then Aegis `.deb` files are shipped inside the ISO (live-build
`packages.chroot`).

## 6. Aegis tooling architecture

`aegis` orchestrates, it does not replace, `apt`.

- **Source of truth:** `tools/manifest.yaml`. Profiles, categories, the menu,
  documentation, and licensing tables are derived from it.
- **Metadata honesty:** every tool carries a `verification` block. License,
  homepage, documentation, redistribution status, and Debian package
  availability default to `unverified`. A tool may only be `bundled: true`
  when its license and redistribution status are verified; the validator
  enforces this.
- **Package names are candidates until resolved.** `aegis install` runs
  `apt-cache policy` against the configured repositories and refuses to
  install if there is no candidate. `aegis manifest check-packages`
  reports which candidates resolve on the current host.
- **Install methods:** `apt` (implemented), `external`, `pipx`, `container`
  (recorded in metadata; refused by the installer in 0.x with instructions).
- **Availability labels:** `OFFLINE AVAILABLE` (installed locally),
  `ONLINE AVAILABLE` (installable from configured repositories when online),
  `REQUIRES INTERNET` (external, container, or unresolved).

## 7. Update model

`aegis update` runs `apt-get update`; `aegis upgrade` runs `apt-get upgrade`
(confirmation required unless `--yes`). No custom updater, no unsigned
sources: `aegis doctor` warns on `trusted=yes` or missing repositories.

## 8. Security model

- Live user is unprivileged; privilege goes through `sudo`.
- No offensive automation is shipped. Tools are installed from distribution
  packages and documented for authorized testing and education only.
- Hardening is opt-in and reversible: `aegis hardening apply` writes one
  drop-in (`/etc/sysctl.d/90-aegis-hardening.conf`) and records state;
  `revert` removes it. It never edits critical files in place.
- The Security Center backend is read-only, binds to `127.0.0.1`, validates
  the `Host` header, and exposes no state-changing endpoints.
- No secrets, keys, or credentials are stored in the repository.

## 9. Verification status

| Area | Status |
|------|--------|
| Base selection facts | VERIFIED (2026-10-03, web sources above) |
| Python components | Tested in the development sandbox (see `docs/DEVELOPMENT.md`) |
| ISO build, boot, installer | NOT VERIFIED |
| VMware, VirtualBox | NOT VERIFIED |
| Package availability in trixie | NOT VERIFIED (resolved at runtime on a Debian host) |

# Building AegisOS

**Status: the ISO build is NOT VERIFIED.** The development sandbox had no network access and no
`live-build`, so `scripts/build.sh` has only been exercised up to its preflight failure path.

## Requirements

- Debian 13 "trixie" host, VM, or privileged `debian:trixie` container; root privileges
- Network access to a Debian mirror
- About 20 GB free disk and 4 GB RAM (estimates, not measured)

```bash
apt-get install live-build debootstrap xorriso squashfs-tools mtools dosfstools \
  grub-efi-amd64-bin dpkg-dev python3 python3-yaml
```

## Build

```bash
make test
make build        # = scripts/build.sh
```

Pipeline (`scripts/build.sh`): preflight, validate manifest, build Aegis `.deb` packages, assemble the
live-build tree in `build/work`, generate the tool package list from the manifest (`core` tier, apt only),
`lb config`, `lb build`, size and EFI boot-image checks, `dist/AegisOS-<VERSION>-amd64.iso`,
`dist/SHA256SUMS`.

Verify afterwards:

```bash
cd dist && sha256sum -c SHA256SUMS
```

## Configuration

`build/profiles/default.env` holds the suite (`trixie`), architecture, archive areas, bootloader
(`grub-efi`, UEFI only) and installer mode (`live` or `none`). `build/config/` holds package lists, hooks and
files included in the image. `scripts/check-package-lists.sh` verifies package names on a trixie host.

## Known unknowns

- Whether the Debian Installer in live mode works with this configuration
- Whether the `os-release` diversion survives upgrades
- Image size and boot behaviour in any hypervisor

## Size budget

GitHub allows less than 2 GiB per release file (2147483648 bytes), so the ISO must stay below that to be published
as a GitHub Release. `scripts/size-report.sh` prints the margin and the largest parts of the image at the end of
every build, and the release workflow refuses to publish an ISO at or over the limit.

Measured on the live medium of the 2026-10-04 build (2156599296 bytes, 2.008 GiB, over the limit):

| Part | Size |
|------|------|
| `live/filesystem.squashfs` (already xz compressed) | 1.3 GiB |
| `live/initrd.img-*` | 134 MiB |
| `pool/` (non-free-firmware 259 MiB, main 154 MiB including the 103 MiB kernel package) | 412 MiB |
| `install/` | 110 MiB |
| `pool-udeb/` | 87 MiB |

Levers, with their trade-offs (only the first is applied): `--firmware-binary false` (removes the installer's firmware
pool; applied), `--firmware-chroot false` (smaller squashfs and initrd, but the live system loses firmware for real
hardware), `--apt-recommends false` (smaller, may drop desktop pieces), dropping packages such as `firefox-esr`.
Changing the squashfs compression type will not help: it is already xz. If a full tool set cannot fit under 2 GiB,
host the ISO outside GitHub and keep checksums and links in the Release.

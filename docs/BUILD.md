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

# VMware

Status: **PARTIALLY VERIFIED** - one observed run, described below. Everything not listed under
"Observed" is NOT VERIFIED.

## Observed (2026-10-03, reported by the project owner with screenshots and command output)

- Host: Windows with VMware Workstation (exact version not recorded).
- ISO: produced by the `build-iso` GitHub Actions workflow (run #1, success, about 11 minutes), downloaded
  as an artifact (a zip containing the ISO, about 2 GB) and extracted with 7-Zip.
- VM guest OS type selected: "Debian 12.x 64-bit". VMware's list had no Debian 13 entry; the label only
  selects default VM settings, it does not change what boots.
- The ISO booted to a live XFCE session. The first-boot welcome terminal ("Welcome to AegisOS", version 0.1.0)
  appeared, and `aegis version` printed `aegis 0.1.0`.
- `/sys/firmware/efi` existed, so the guest booted via **UEFI**.
- Base system reported by `/etc/os-release`: Debian GNU/Linux 13 (trixie), 13.7, kernel 6.12.111+deb13-amd64.
- Networking worked: `ping deb.debian.org` and an HTTPS request succeeded.
- `open-vm-tools` and `open-vm-tools-desktop` were installed in the image.
- Free space on `/` in the live session was about 944 MiB. The live root is memory-backed, so installing
  large tool sets in a live session can exhaust it; give the VM more RAM or install to disk.

## Known defects found in that run (fixes committed, not yet re-tested in a VM)

- `/etc/os-release` still said Debian: the identification hook was in the wrong live-build directory.
- Desktop wallpaper stayed the XFCE default. Cause confirmed by experiment: after choosing the wallpaper by
  hand, XFCE had created the key `/backdrop/screen0/monitorVirtual1/...` (monitor name `Virtual1` under VMware,
  no hyphen), a name the image's configuration did not list. The image now lists that key and also runs
  `aegis desktop-setup` once per user at login, which reads the real output names from `xrandr`.
  Both changes are untested in a booted VM.
- `aegis doctor` reported FAIL for a repository with signature verification disabled. Cause found: the
  image's `/etc/apt/sources.list` begins with `deb [trusted=yes] file:/run/live/medium trixie main contrib
  non-free-firmware`, a local, unsigned repository pointing at the live medium (who adds it, live-build or the
  installer integration, is not confirmed). The other lines are the normal Debian mirrors, and
  `apt-get update` worked against them. The doctor now reports an unsigned local `file:` repository as a
  WARN and keeps FAIL for unsigned network repositories.

## NOT VERIFIED

Firmware settings other than "UEFI was in use", clipboard, drag and drop, display auto-resize, shared folders,
installer ("Install" boot entry) and installation to a virtual disk, persistence across reboot, sound, USB,
any VMware version other than the one used.

## Suggested VM settings (starting point, not a tested configuration)

2 or more vCPUs, 4 GB RAM or more, 40 GB disk, NAT networking, **UEFI firmware** (the ISO has no BIOS bootloader).

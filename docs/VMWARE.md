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

## Defects found in the first run (all fixed; confirmed in the second run below)

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

## Second run (2026-10-04, rebuilt ISO, reported with screenshots and command output)

- New VM `AegisOS-test2`: VMware Workstation 17 Pro, guest type "Debian 12.x 64-bit", 2 vCPUs, 8 GB RAM, 40 GB disk,
  NAT, UEFI firmware. The GRUB menu offered "Live system", "Live system (fail-safe mode)", "Start installer",
  "Start installer with speech synthesis", "Advanced install options" and "Utilities". The menu header still shows
  Debian branding and a Debian logo; AegisOS branding of the boot menu is not done.
- Booted the first entry (Live system). The AegisOS wallpaper showed at first login and the welcome terminal opened.
- `/etc/os-release`: `ID=aegisos`, `PRETTY_NAME="AegisOS 0.1.0"`.
- `aegis doctor`: 11 PASS, 2 WARN, 0 FAIL. WARN 1: the unsigned local repository on the live medium plus plain-HTTP
  Debian mirrors. WARN 2: `NTPSynchronized=no` (cause not investigated).
- `xfconf-query` showed the Aegis wallpaper set on `monitor0`, `monitor1`, `monitorVirtual-1` and `monitorVirtual1`.
- Free space on `/` was 3.8 GiB with 8 GB RAM.
- `apt-get update` succeeded against the Debian mirrors. `aegis manifest check-packages`: 95 apt candidates resolved,
  13 did not (see `docs/TOOLS.md`, verification log).
- `aegis security-center` showed real values (kernel, CPU, 7.7 GiB RAM, interface `ens33` 192.168.254.131, DNS).
  As a normal user it said "no firewall tool installed"; as root it said "nftables ruleset empty". The first was a
  bug: `nft` lives in `/usr/sbin`, which is not on a normal user's PATH. Fixed (not yet re-tested in a VM). With
  root, process names appeared next to the listening sockets (all `avahi-daemon`, UDP only, no TCP listeners).
- `aegis hardening apply --yes` wrote `/etc/sysctl.d/90-aegis-hardening.conf` and the audit then showed 10 of 10
  settings compliant. `aegis hardening revert --yes` removed the drop-in and its state file, and the audit went back
  to the same four compliant settings seen before `apply` (the six others returned to their previous values).
  This is the first execution of apply/revert against a real `/etc` and live kernel settings.
- `aegis install nmap --dry-run` reported "already installed" (nmap is in the image); the tool-install path itself
  (a real `apt-get install` through `aegis`) was NOT run.
- Clipboard between Windows and the guest worked.
- Display did NOT resize automatically with the VMware window; cause not diagnosed.

## NOT VERIFIED

Drag and drop, shared folders, display auto-resize (observed failing, cause unknown), the installer ("Start
installer" entry exists but was not run) and installation to a virtual disk, persistence across reboot, sound, USB,
Secure Boot, any VMware version other than Workstation 17 Pro, whether any tool actually installs and runs.

## Suggested VM settings (starting point, not a tested configuration)

2 or more vCPUs, 4 GB RAM or more, 40 GB disk, NAT networking, **UEFI firmware** (the ISO has no BIOS bootloader).

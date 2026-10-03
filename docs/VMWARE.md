# VMware

**Status: NOT VERIFIED. No VMware product has been used with AegisOS.** The values below are a starting
point derived from the image design (UEFI-only, amd64), not tested results.

- Firmware: **UEFI is required** (the ISO has no BIOS bootloader).
- Suggested starting resources: 2 vCPU, 4 GB RAM, 40 GB disk (untested guesses).
- Attach `AegisOS-<VERSION>-amd64.iso` to the virtual CD/DVD and boot.
- Network: NAT is the safe default; bridged only on networks you are authorized to test.
- Guest tools: the package list includes `open-vm-tools` and `open-vm-tools-desktop` (names unverified on
  trixie until CI `trixie-packages` passes). Clipboard, display resizing and shared folders: NOT VERIFIED.
- Troubleshooting: if the VM does not boot, confirm UEFI is enabled and re-verify the ISO checksum.

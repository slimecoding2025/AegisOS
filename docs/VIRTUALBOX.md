# VirtualBox

**Status: NOT VERIFIED. No VirtualBox version has been used with AegisOS.**

- Enable EFI in the VM's System settings (**UEFI is required**; there is no BIOS bootloader).
- Suggested starting resources: 2 CPUs, 4 GB RAM, 40 GB disk (untested guesses).
- Attach the ISO as optical drive and boot.
- Network: NAT by default.
- Guest Additions: not included in the package list. Debian 13 availability of VirtualBox guest packages was
  not verified; display, clipboard and shared-folder behaviour are NOT VERIFIED.
- Troubleshooting: black screen or no boot - check EFI is enabled and the checksum matches.

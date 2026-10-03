# Installation

**No ISO has been built yet (NOT VERIFIED).** These are the intended steps once a release exists.

1. Download `AegisOS-<VERSION>-amd64.iso` and `SHA256SUMS` from the project's GitHub Releases.
2. Verify: `sha256sum -c SHA256SUMS` (run in the download folder).
3. Boot in a UEFI virtual machine (see `docs/VMWARE.md`, `docs/VIRTUALBOX.md`). BIOS boot is not supported.
4. The live session has a default live user created by `live-config`; change credentials on any installed system.
5. Installation to disk uses the Debian Installer in live mode (NOT VERIFIED). If it fails, use
   `AEGIS_INSTALLER=none` builds and report the issue.

Install the Aegis tooling on an existing Debian 13 system instead (VERIFIED as `.deb` build only):
`make debs`, then `apt install ./dist/debs/aegis-*.deb` (install step itself NOT VERIFIED on Debian).

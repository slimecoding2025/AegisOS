# Changelog

All notable changes are documented here. This project follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-10-04

Pre-alpha. Edit the date if the tag is created on another day.

### Added
- `aegis` tool manager, `aegis doctor`, reversible `aegis hardening`, `aegis manifest` tools, `aegis security-center`
  (text, JSON and a read-only local web dashboard) and `aegis-net`.
- Tool manifest (138 entries, 18 categories, 12 profiles) with a validator.
- live-build configuration for a UEFI amd64 hybrid ISO based on Debian 13 "trixie" with XFCE and Aegis branding.
- `.deb` packaging, GitHub Actions workflows (test, build-iso, release) and documentation.

### Verified
- The ISO is built by GitHub Actions and boots a live session under UEFI in VMware Workstation 17 Pro.
- `aegis doctor`, `aegis-net`, the Security Center and hardening apply/revert run on a booted image.
- CI (ShellCheck, pytest, manifest validation, package build, trixie package-name check) passes.

### Not verified
- Installation to disk with the Debian Installer, VirtualBox, Secure Boot, and installing and running individual tools.

### Known issues
- The VMware display does not resize automatically with the window (cause not found).
- The boot menu still shows Debian branding.
- 13 tools in the manifest are not available in Debian 13 and are listed as external installs.

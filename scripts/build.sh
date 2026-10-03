#!/usr/bin/env bash
# Build the AegisOS ISO with live-build. NOT VERIFIED in the development sandbox (no network, no live-build).
# Run on Debian 13 (trixie) as root, or via .github/workflows/build-iso.yml.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VERSION="$(tr -d '[:space:]' < VERSION)"
PROFILE="${AEGIS_PROFILE:-$ROOT/build/profiles/default.env}"
WORK="$ROOT/build/work"
DIST="$ROOT/dist"
ISO_NAME="AegisOS-${VERSION}-amd64.iso"

echo "==> preflight"
missing=()
for c in lb debootstrap xorriso mksquashfs dpkg-deb python3 sha256sum; do
  command -v "$c" >/dev/null 2>&1 || missing+=("$c")
done
if [ "${#missing[@]}" -gt 0 ]; then
  echo "error: missing required tools: ${missing[*]}" >&2
  echo "On Debian 13: apt-get install live-build debootstrap xorriso squashfs-tools mtools dosfstools grub-efi-amd64-bin dpkg-dev python3 python3-yaml" >&2
  exit 1
fi
if [ "$(id -u)" -ne 0 ]; then echo "error: live-build must run as root" >&2; exit 1; fi
# shellcheck disable=SC1090
source "$PROFILE"
export AEGIS_DEBIAN_SUITE AEGIS_ARCH AEGIS_ARCHIVE_AREAS AEGIS_BOOTLOADERS AEGIS_INSTALLER
export AEGIS_VERSION="$VERSION"
export PYTHONPATH="$ROOT/packages/aegis-core"

echo "==> validate manifest"
python3 -m aegis.cli manifest validate

echo "==> build Aegis .deb packages"
"$ROOT/scripts/build-debs.sh" "$ROOT/dist/debs"

echo "==> prepare live-build tree in $WORK"
rm -rf "$WORK"
mkdir -p "$WORK/config/packages.chroot" "$WORK/auto"
cp -r "$ROOT/build/config/auto/." "$WORK/auto/"
for d in package-lists hooks includes.chroot; do
  [ -d "$ROOT/build/config/$d" ] && cp -r "$ROOT/build/config/$d" "$WORK/config/"
done
cp "$ROOT"/dist/debs/*.deb "$WORK/config/packages.chroot/"
# Tool package list comes from the manifest (single source of truth): tier "core", apt-managed only.
python3 -m aegis.cli manifest package-list --tier core > "$WORK/config/package-lists/aegis-tools.list.chroot"

echo "==> lb config"
( cd "$WORK" && lb config )

echo "==> lb build (this takes a long time and downloads packages)"
( cd "$WORK" && lb build ) 2>&1 | tee "$WORK/build.log"

echo "==> collect artifact"
built="$(find "$WORK" -maxdepth 1 -name '*.iso' | head -n1)"
if [ -z "$built" ]; then echo "error: lb build produced no ISO (see $WORK/build.log)" >&2; exit 1; fi
mkdir -p "$DIST"
cp "$built" "$DIST/$ISO_NAME"

echo "==> validate ISO"
size=$(stat -c %s "$DIST/$ISO_NAME")
[ "$size" -gt 104857600 ] || { echo "error: ISO is suspiciously small ($size bytes)" >&2; exit 1; }
xorriso -indev "$DIST/$ISO_NAME" -report_el_torito plain 2>&1 | tee "$DIST/iso-boot-report.txt" | grep -qi 'efi' \
  || { echo "error: no EFI boot image found in ISO" >&2; exit 1; }

echo "==> checksums"
( cd "$DIST" && sha256sum "$ISO_NAME" > SHA256SUMS && sha256sum -c SHA256SUMS )
echo "built $DIST/$ISO_NAME ($size bytes). Booting it in a VM is a separate, manual verification step."

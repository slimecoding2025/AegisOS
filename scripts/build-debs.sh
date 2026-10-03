#!/usr/bin/env bash
# Build the Aegis .deb packages with dpkg-deb into dist/debs. Verified only where dpkg-deb exists.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION")"
OUT="${1:-$ROOT/dist/debs}"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
command -v dpkg-deb >/dev/null || { echo "error: dpkg-deb not found" >&2; exit 1; }
mkdir -p "$OUT"

stage_pkg() { # name
  local d="$STAGE/$1"; mkdir -p "$d/DEBIAN"
  sed "s/@VERSION@/$VERSION/g" "$ROOT/packages/$1/DEBIAN/control" > "$d/DEBIAN/control"
  echo "$d"
}
finish() { # name dir
  dpkg-deb --root-owner-group --build "$2" "$OUT/$1_${VERSION}_all.deb" >/dev/null
  echo "built $OUT/$1_${VERSION}_all.deb"
}

d=$(stage_pkg aegis-core)
mkdir -p "$d/usr/lib/aegis"
cp -r "$ROOT/packages/aegis-core/aegis" "$d/usr/lib/aegis/"
find "$d" -name __pycache__ -type d -prune -exec rm -rf {} +
finish aegis-core "$d"

d=$(stage_pkg aegis-cli)
install -D -m 0755 "$ROOT/packages/aegis-cli/bin/aegis" "$d/usr/bin/aegis"
install -D -m 0755 "$ROOT/packages/aegis-cli/bin/aegis-net" "$d/usr/bin/aegis-net"
finish aegis-cli "$d"

d=$(stage_pkg aegis-tools)
install -D -m 0644 "$ROOT/tools/manifest.yaml" "$d/usr/share/aegis/manifest.yaml"
install -D -m 0644 "$ROOT/VERSION" "$d/usr/share/aegis/VERSION"
finish aegis-tools "$d"

d=$(stage_pkg aegis-security-center)
install -D -m 0755 "$ROOT/packages/aegis-cli/bin/aegis-security-center" "$d/usr/bin/aegis-security-center"
install -D -m 0644 "$ROOT/configs/desktop/applications/aegis-security-center.desktop" \
  "$d/usr/share/applications/aegis-security-center.desktop"
finish aegis-security-center "$d"

d=$(stage_pkg aegis-branding)
install -D -m 0644 "$ROOT/assets/branding/logo.svg" "$d/usr/share/aegis/branding/logo.svg"
install -D -m 0644 "$ROOT/assets/wallpapers/aegis-dark.svg" "$d/usr/share/backgrounds/aegisos/aegis-dark.svg"
install -D -m 0644 "$ROOT/configs/shell/aegis-banner.sh" "$d/etc/profile.d/aegis-banner.sh"
for f in aegis-tool-manager aegis-docs; do
  install -D -m 0644 "$ROOT/configs/desktop/applications/$f.desktop" "$d/usr/share/applications/$f.desktop"
done
install -D -m 0644 "$ROOT/configs/desktop/autostart/aegis-welcome.desktop" "$d/etc/xdg/autostart/aegis-welcome.desktop"
mkdir -p "$d/usr/share/doc/aegis-branding"
cp "$ROOT"/docs/*.md "$d/usr/share/doc/aegis-branding/"
finish aegis-branding "$d"

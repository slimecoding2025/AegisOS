#!/usr/bin/env bash
# Verify that every package named in the ISO package lists and the manifest core tier resolves via apt.
# Only meaningful on Debian 13 "trixie" with fresh package lists (`apt-get update`).
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$ROOT/packages/aegis-core"
# shellcheck source=/dev/null
codename="$(. /etc/os-release && echo "${VERSION_CODENAME:-unknown}")"
if [ "$codename" != "trixie" ]; then
  echo "WARNING: host codename is '$codename', not 'trixie'; results are NOT valid for AegisOS" >&2
fi
mapfile -t pkgs < <( { grep -hvE '^\s*(#|$)' "$ROOT"/build/config/package-lists/*.list.chroot; \
                        python3 -m aegis.cli manifest package-list --tier core; } | sort -u )
bad=0
for p in "${pkgs[@]}"; do
  cand="$(apt-cache policy "$p" 2>/dev/null | awk '/Candidate:/ {print $2}')"
  if [ -z "$cand" ] || [ "$cand" = "(none)" ]; then echo "MISSING $p"; bad=1; else echo "ok      $p $cand"; fi
done
echo "${#pkgs[@]} packages checked, host codename: $codename"
exit $bad

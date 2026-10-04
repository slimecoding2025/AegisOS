#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -d "$ROOT/build/work" ] && command -v lb >/dev/null; then
  (cd "$ROOT/build/work" && lb clean --purge 2>/dev/null) || true
fi
rm -rf "$ROOT/build/work" "$ROOT/dist"
find "$ROOT" -name __pycache__ -type d -prune -exec rm -rf {} +
echo "clean"

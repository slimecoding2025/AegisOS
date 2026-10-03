#!/usr/bin/env bash
# Maintainer helper: build ISO + checksums. Publishing a GitHub Release is done by the release workflow.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"$ROOT/scripts/test.sh"
"$ROOT/scripts/build.sh"
"$ROOT/scripts/verify.sh"
echo "release artifacts:"; ls -l "$ROOT/dist"

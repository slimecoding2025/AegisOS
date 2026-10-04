#!/usr/bin/env bash
# Print an ISO's size against GitHub's 2 GiB per-release-asset limit and, when the live-build
# binary tree is given, where the bytes go. Exit 2 when the ISO is over the limit.
set -euo pipefail
LIMIT=2147483648
iso="${1:?usage: size-report.sh ISO [BINARY_DIR]}"
size=$(stat -c %s "$iso")
margin=$((LIMIT - size))
gib=$(awk -v s="$size" 'BEGIN { printf "%.3f", s / 1073741824 }')
printf 'ISO size: %d bytes (%s GiB)\n' "$size" "$gib"
status=0
if [ "$margin" -lt 0 ]; then
  printf 'OVER the GitHub release asset limit (2 GiB) by %d bytes\n' "$((-margin))"
  status=2
elif [ "$margin" -lt $((LIMIT / 10)) ]; then
  printf 'WARNING: only %d bytes below the 2 GiB GitHub release asset limit\n' "$margin"
else
  printf 'OK: %d bytes below the 2 GiB GitHub release asset limit\n' "$margin"
fi
bin="${2:-}"
if [ -n "$bin" ] && [ -d "$bin" ]; then
  echo "Largest top-level parts of the image:"
  du -sh "$bin"/* 2>/dev/null | sort -h | tail -8
  if [ -d "$bin/live" ]; then ls -lh "$bin/live"; fi
fi
exit "$status"

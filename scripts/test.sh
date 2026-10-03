#!/usr/bin/env bash
# Run every check that is possible on this machine and say clearly what was skipped.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT/packages/aegis-core"
rc=0

echo "== manifest validation =="
python3 -m aegis.cli manifest validate || rc=1

echo "== shell syntax (bash -n) =="
while IFS= read -r f; do
  if bash -n "$f"; then echo "ok  $f"; else echo "FAIL $f"; rc=1; fi
done < <(find scripts build -type f \( -name '*.sh' -o -path '*/auto/*' -o -path '*/hooks/*' \) | sort)

echo "== shellcheck =="
if command -v shellcheck >/dev/null; then
  find scripts build -type f \( -name '*.sh' -o -path '*/auto/*' -o -path '*/hooks/*' \) -print0 | xargs -0 shellcheck || rc=1
else
  echo "SKIPPED: shellcheck is not installed (NOT VERIFIED)"
fi

echo "== python tests =="
if python3 -c 'import pytest' 2>/dev/null; then
  python3 -m pytest -q tests || rc=1
else
  echo "pytest not installed; running the same tests with unittest"
  python3 -m unittest discover -s tests -t . || rc=1
fi
exit $rc

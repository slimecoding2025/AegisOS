#!/usr/bin/env bash
# Static repository verification. Does not boot anything; reports ISO state honestly.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT/packages/aegis-core"
fail=0
note() { echo "$*"; }
bad() { echo "FAIL: $*"; fail=1; }

VERSION="$(tr -d '[:space:]' < VERSION)"
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] && note "ok   VERSION $VERSION is semantic" || bad "VERSION '$VERSION' is not MAJOR.MINOR.PATCH"

for f in README.md LICENSE CONTRIBUTING.md CODE_OF_CONDUCT.md SECURITY.md CHANGELOG.md Makefile \
         docs/ARCHITECTURE.md docs/BUILD.md docs/TOOL-LICENSING.md tools/manifest.yaml build/config/auto/config; do
  [ -f "$f" ] && note "ok   $f" || bad "missing $f"
done

if python3 -m aegis.cli manifest validate >/dev/null; then note "ok   manifest valid"; else bad "manifest invalid"; fi
[ "$(python3 -m aegis.cli version)" = "aegis $VERSION" ] && note "ok   CLI version matches VERSION" || bad "CLI version mismatch"

# TOOL-LICENSING.md must be in sync with the manifest
if python3 scripts/gen-tool-docs.py --check >/dev/null 2>&1; then note "ok   docs/TOOL-LICENSING.md and docs/TOOLS.md match manifest"; else bad "generated tool docs are stale (run scripts/gen-tool-docs.py)"; fi

# simple secret scan (patterns only; not a substitute for a real scanner)
if grep -rEIn --exclude-dir=.git --exclude=verify.sh \
   -e 'AKIA[0-9A-Z]{16}' -e '-----BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY-----' \
   -e '(password|passwd|secret|api[_-]?key)[[:space:]]*[:=][[:space:]]*["'"'"'][^"'"'"' ]{8,}' . ; then
  bad "possible secret found"
else note "ok   no secret patterns found"; fi

if ls dist/AegisOS-*-amd64.iso >/dev/null 2>&1; then
  if [ -f dist/SHA256SUMS ]; then (cd dist && sha256sum -c SHA256SUMS) && note "ok   ISO checksum" || bad "ISO checksum mismatch"
  else bad "ISO present without dist/SHA256SUMS"; fi
else
  note "ISO: not present - ISO build NOT VERIFIED"
fi
exit $fail

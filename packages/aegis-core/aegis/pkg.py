"""Thin, safe wrappers around apt/dpkg. Aegis never replaces apt; it calls it."""
from __future__ import annotations

import os
import shutil
import subprocess

# Debian keeps administration tools (nft, iptables, ufw, ...) in sbin directories that are not on an
# unprivileged user's PATH. Observed on AegisOS 0.1.0: as a normal user the Security Center claimed
# "no firewall tool installed" although nft was present.
SBIN_DIRS = ["/usr/local/sbin", "/usr/sbin", "/sbin"]


def have(cmd: str) -> bool:
    path = os.environ.get("PATH", "")
    extra = [d for d in SBIN_DIRS if d not in path.split(os.pathsep)]
    return shutil.which(cmd, path=os.pathsep.join([path, *extra])) is not None


def run(cmd: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)


def candidate(package: str) -> str | None:
    """Return the candidate version apt would install, or None if there is none."""
    if not have("apt-cache"):
        return None
    r = run(["apt-cache", "policy", package])
    if r.returncode != 0:
        return None
    for line in r.stdout.splitlines():
        line = line.strip()
        if line.startswith("Candidate:"):
            val = line.split(":", 1)[1].strip()
            return None if val in ("(none)", "") else val
    return None


def installed_version(package: str) -> str | None:
    if not have("dpkg-query"):
        return None
    r = run(["dpkg-query", "-W", "-f=${Status}|${Version}", package])
    if r.returncode != 0:
        return None
    status, _, version = r.stdout.partition("|")
    return version if status.endswith("installed") and "not-installed" not in status else None


def broken_packages() -> list[str]:
    if not have("dpkg"):
        return []
    r = run(["dpkg", "--audit"])
    return [l for l in r.stdout.splitlines() if l.strip()]

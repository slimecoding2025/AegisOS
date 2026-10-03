"""aegis hardening: optional, documented, reversible.

apply writes ONE drop-in file and a state file; revert removes both. No existing system file is edited.
Every function accepts `root` so it can be tested against a temporary directory.
"""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

DROPIN = "etc/sysctl.d/90-aegis-hardening.conf"
STATE = "etc/aegis/hardening-state.json"

# key -> (hardened value, rationale). Chosen to avoid breaking normal usage or debugging tools.
SYSCTL_POLICY = {
    "kernel.kptr_restrict": ("2", "hide kernel pointers from unprivileged users"),
    "kernel.dmesg_restrict": ("1", "restrict dmesg to privileged users"),
    "net.ipv4.tcp_syncookies": ("1", "mitigate SYN flood attacks"),
    "net.ipv4.conf.all.rp_filter": ("1", "enable reverse-path filtering"),
    "net.ipv4.conf.default.rp_filter": ("1", "enable reverse-path filtering for new interfaces"),
    "net.ipv4.conf.all.accept_redirects": ("0", "ignore ICMP redirects"),
    "net.ipv4.conf.all.send_redirects": ("0", "do not send ICMP redirects"),
    "net.ipv6.conf.all.accept_redirects": ("0", "ignore IPv6 ICMP redirects"),
    "fs.protected_hardlinks": ("1", "restrict hardlink creation"),
    "fs.protected_symlinks": ("1", "restrict symlink following in sticky dirs"),
}


@dataclass
class Finding:
    key: str
    current: str | None
    wanted: str
    ok: bool
    why: str


def read_sysctl(key: str, proc_root: str = "/proc/sys") -> str | None:
    p = Path(proc_root) / key.replace(".", "/")
    try:
        return p.read_text().strip()
    except OSError:
        return None


def audit(proc_root: str = "/proc/sys") -> list[Finding]:
    out = []
    for key, (want, why) in SYSCTL_POLICY.items():
        cur = read_sysctl(key, proc_root)
        out.append(Finding(key, cur, want, cur == want, why))
    return out


def is_applied(root: str = "/") -> bool:
    return (Path(root) / DROPIN).is_file()


def status(root: str = "/", proc_root: str = "/proc/sys") -> dict:
    findings = audit(proc_root)
    return {
        "applied": is_applied(root),
        "compliant": sum(f.ok for f in findings),
        "total": len(findings),
        "dropin": str(Path(root) / DROPIN),
    }


def render_dropin() -> str:
    lines = ["# Managed by AegisOS: `aegis hardening apply`. Remove with `aegis hardening revert`."]
    for key, (val, why) in SYSCTL_POLICY.items():
        lines.append(f"# {why}")
        lines.append(f"{key} = {val}")
    return "\n".join(lines) + "\n"


def apply(root: str = "/", dry_run: bool = False, reload: bool = True, proc_root: str = "/proc/sys") -> dict:
    if not dry_run and root == "/" and os.geteuid() != 0:
        raise PermissionError("root privileges required")
    drop = Path(root) / DROPIN
    state = Path(root) / STATE
    before = {k: read_sysctl(k, proc_root) for k in SYSCTL_POLICY}
    result = {"dropin": str(drop), "dry_run": dry_run, "previous_values": before}
    if dry_run:
        result["content"] = render_dropin()
        return result
    drop.parent.mkdir(parents=True, exist_ok=True)
    state.parent.mkdir(parents=True, exist_ok=True)
    drop.write_text(render_dropin(), encoding="utf-8")
    state.write_text(json.dumps({"previous_values": before}, indent=2), encoding="utf-8")
    if reload and root == "/":
        r = subprocess.run(["sysctl", "-p", str(drop)], capture_output=True, text=True)
        result["reload_returncode"] = r.returncode
        result["reload_output"] = (r.stdout + r.stderr).strip()
    return result


def revert(root: str = "/", reload: bool = True) -> dict:
    if root == "/" and os.geteuid() != 0:
        raise PermissionError("root privileges required")
    drop = Path(root) / DROPIN
    state = Path(root) / STATE
    removed = []
    previous = {}
    if state.is_file():
        previous = json.loads(state.read_text()).get("previous_values", {})
    for f in (drop, state):
        if f.is_file():
            f.unlink()
            removed.append(str(f))
    restored = {}
    if reload and root == "/":
        for k, v in previous.items():
            if v is None:
                continue
            r = subprocess.run(["sysctl", "-w", f"{k}={v}"], capture_output=True, text=True)
            restored[k] = r.returncode == 0
    return {"removed": removed, "restored_runtime_values": restored}

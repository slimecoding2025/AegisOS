"""Per-user desktop defaults applied at first login (XFCE wallpaper on every connected monitor).

Why this exists: XFCE stores the wallpaper per monitor *name*, and the name depends on the graphics
driver (observed on VMware Workstation: `Virtual1`, with no hyphen). A static list of names cannot cover
every hypervisor or real machine, so the connected output names are read from `xrandr` at login.
Applied once per user (marker file) so the user's later wallpaper choice is never overwritten.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import pkg

WALLPAPER = "/usr/share/backgrounds/aegisos/aegis-dark.svg"
CHANNEL = "xfce4-desktop"
NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")
CONNECTED_RE = re.compile(r"^(\S+) connected\b", re.MULTILINE)


def connected_outputs(xrandr_text: str) -> list[str]:
    return [n for n in CONNECTED_RE.findall(xrandr_text) if NAME_RE.match(n)]


def monitor_keys(outputs: list[str]) -> list[str]:
    keys = ["monitor0"]
    for o in outputs:
        k = f"monitor{o}"
        if k not in keys:
            keys.append(k)
    return keys


def commands(keys: list[str], image: str = WALLPAPER) -> list[list[str]]:
    cmds = []
    for k in keys:
        base = f"/backdrop/screen0/{k}/workspace0"
        cmds.append(["xfconf-query", "-c", CHANNEL, "-p", f"{base}/last-image", "-n", "-t", "string", "-s", image])
        cmds.append(["xfconf-query", "-c", CHANNEL, "-p", f"{base}/image-style", "-n", "-t", "int", "-s", "5"])
    return cmds


def default_marker() -> Path:
    return Path.home() / ".config" / "aegis" / "wallpaper-done"


def apply_wallpaper(runner=pkg.run, marker: Path | None = None, force: bool = False,
                    dry_run: bool = False, have=pkg.have) -> dict:
    marker = marker or default_marker()
    if marker.exists() and not force:
        return {"status": "skipped", "reason": "already applied for this user (use --force)"}
    if not have("xfconf-query"):
        return {"status": "unavailable", "reason": "xfconf-query not found (not an XFCE session?)"}
    outputs: list[str] = []
    if have("xrandr"):
        r = runner(["xrandr", "--query"], timeout=10)
        if r.returncode == 0:
            outputs = connected_outputs(r.stdout)
    cmds = commands(monitor_keys(outputs))
    if dry_run:
        return {"status": "dry-run", "outputs": outputs, "commands": cmds}
    failures = 0
    for c in cmds:
        if runner(c, timeout=10).returncode != 0:
            failures += 1
    if failures == 0:
        try:
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.touch()
        except OSError:
            pass
    return {"status": "ok" if failures == 0 else "partial", "outputs": outputs, "failures": failures}

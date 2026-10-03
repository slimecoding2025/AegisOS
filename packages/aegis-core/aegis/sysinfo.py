"""Real system information read from /proc, /sys and the standard library."""
from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path


def read_os_release(path: str = "/etc/os-release") -> dict[str, str]:
    data: dict[str, str] = {}
    try:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            data[key] = val.strip().strip('"').strip("'")
    except OSError:
        pass
    return data


def kernel() -> dict[str, str]:
    u = platform.uname()
    return {"release": u.release, "version": u.version, "machine": u.machine}


def cpu(cpuinfo: str = "/proc/cpuinfo") -> dict:
    model = None
    try:
        for line in Path(cpuinfo).read_text(encoding="utf-8", errors="replace").splitlines():
            if line.lower().startswith("model name"):
                model = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    return {"model": model or "unknown", "logical_cpus": os.cpu_count() or 0}


def memory(meminfo: str = "/proc/meminfo") -> dict:
    vals: dict[str, int] = {}
    try:
        for line in Path(meminfo).read_text(encoding="utf-8").splitlines():
            key, _, rest = line.partition(":")
            parts = rest.split()
            if parts and parts[0].isdigit():
                vals[key] = int(parts[0]) * 1024  # kB -> bytes
    except OSError:
        pass
    total = vals.get("MemTotal", 0)
    avail = vals.get("MemAvailable", vals.get("MemFree", 0))
    return {"total_bytes": total, "available_bytes": avail, "used_bytes": max(total - avail, 0)}


def disks(paths=("/",)) -> list[dict]:
    out = []
    for p in paths:
        try:
            u = shutil.disk_usage(p)
            out.append({"path": p, "total_bytes": u.total, "used_bytes": u.used, "free_bytes": u.free})
        except OSError:
            continue
    return out


def uptime_seconds(path: str = "/proc/uptime") -> float | None:
    try:
        return float(Path(path).read_text().split()[0])
    except (OSError, ValueError, IndexError):
        return None


def human_bytes(n: int) -> str:
    size = float(n)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{n} B"

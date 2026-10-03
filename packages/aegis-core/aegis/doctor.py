"""aegis doctor: real health checks. Exit codes: 0 all PASS, 1 any WARN, 2 any FAIL."""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import __version__, manifest, pkg, sysinfo

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"


@dataclass
class Check:
    name: str
    status: str
    detail: str


def check_os() -> Check:
    osr = sysinfo.read_os_release()
    if not osr:
        return Check("os", FAIL, "/etc/os-release not readable")
    pretty = osr.get("PRETTY_NAME", "unknown")
    if osr.get("ID") == "aegisos":
        return Check("os", PASS, pretty)
    if osr.get("ID") in ("debian", "ubuntu") or "debian" in osr.get("ID_LIKE", ""):
        return Check("os", WARN, f"{pretty} (Debian family, but not AegisOS)")
    return Check("os", WARN, f"{pretty} (not a Debian-family system; apt features may not work)")


def check_kernel() -> Check:
    k = sysinfo.kernel()
    return Check("kernel", PASS, f"{k['release']} ({k['machine']})")


def check_package_manager() -> Check:
    missing = [c for c in ("apt-get", "apt-cache", "dpkg") if not pkg.have(c)]
    if missing:
        return Check("package-manager", FAIL, "missing: " + ", ".join(missing))
    return Check("package-manager", PASS, "apt-get, apt-cache, dpkg found")


def check_repositories(root: str = "/") -> Check:
    base = Path(root)
    files = []
    sl = base / "etc/apt/sources.list"
    if sl.is_file():
        files.append(sl)
    d = base / "etc/apt/sources.list.d"
    if d.is_dir():
        files += sorted(p for p in d.iterdir() if p.suffix in (".list", ".sources"))
    if not files:
        return Check("repositories", FAIL, "no APT sources configured")
    active: list[tuple[Path, str]] = []
    for f in files:
        for line in f.read_text(errors="replace").splitlines():
            if line.strip() and not line.strip().startswith("#"):
                active.append((f, line))
    if not active:
        return Check("repositories", FAIL, "APT sources contain no active entries")
    warnings: list[str] = []
    for f, line in active:
        low = line.lower().replace(" ", "")
        insecure = ("trusted=yes" in low or "allow-insecure=yes" in low
                    or low.startswith("trusted:yes") or low.startswith("allow-insecure:yes"))
        if insecure:
            # An unsigned repository fetched over the network is a failure. An unsigned repository on a
            # local file: path (for example the read-only live medium) is reported, but only as a warning.
            if "file:" in line and "http" not in line:
                warnings.append(f"{f.name}: unsigned local repository (signature check disabled): {line.strip()[:100]}")
            else:
                return Check("repositories", FAIL, f"{f.name}: signature verification disabled in: {line.strip()[:120]}")
        elif line.strip().startswith("deb http://") or line.strip().startswith("URIs: http://"):
            if not any("plain-HTTP" in w for w in warnings):
                warnings.append(f"plain-HTTP repository in {f.name} (APT still verifies signatures)")
    if warnings:
        return Check("repositories", WARN, "; ".join(warnings))
    return Check("repositories", PASS, f"{len(files)} source file(s), signature checks enabled")


def check_dns(host: str = "deb.debian.org") -> Check:
    old = socket.getdefaulttimeout()
    socket.setdefaulttimeout(4)
    try:
        socket.getaddrinfo(host, 443)
        return Check("dns", PASS, f"resolved {host}")
    except OSError as exc:
        return Check("dns", WARN, f"cannot resolve {host}: {exc}")
    finally:
        socket.setdefaulttimeout(old)


def check_connectivity(url: str = "https://deb.debian.org/") -> Check:
    """A bare TCP connect can be accepted by a filtering proxy, so require a real HTTPS response."""
    import urllib.error
    import urllib.request

    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": f"aegis-doctor/{__version__}"})
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            return Check("connectivity", PASS, f"HTTPS {resp.status} from {url}")
    except urllib.error.HTTPError as exc:
        return Check("connectivity", WARN, f"HTTPS request to {url} answered {exc.code} (blocked or filtered?)")
    except (urllib.error.URLError, OSError) as exc:
        return Check("connectivity", WARN, f"cannot reach {url}: {exc} (offline use is still possible)")


def check_disk(path: str = "/", warn_pct: int = 85, fail_pct: int = 95) -> Check:
    try:
        u = shutil.disk_usage(path)
    except OSError as exc:
        return Check("disk", FAIL, str(exc))
    pct = int(u.used * 100 / u.total) if u.total else 100
    detail = f"{pct}% used, {sysinfo.human_bytes(u.free)} free on {path}"
    return Check("disk", FAIL if pct >= fail_pct else WARN if pct >= warn_pct else PASS, detail)


def check_time_sync() -> Check:
    if not pkg.have("timedatectl"):
        return Check("time-sync", WARN, "timedatectl not available")
    r = pkg.run(["timedatectl", "show", "-p", "NTPSynchronized", "--value"])
    val = r.stdout.strip()
    if r.returncode != 0 or not val:
        return Check("time-sync", WARN, "cannot query time synchronization (systemd not running?)")
    return Check("time-sync", PASS if val == "yes" else WARN, f"NTPSynchronized={val}")


def check_dependencies() -> Check:
    missing = []
    try:
        import yaml  # noqa: F401
    except ImportError:
        missing.append("python3-yaml")
    if missing:
        return Check("dependencies", FAIL, "missing: " + ", ".join(missing))
    return Check("dependencies", PASS, "python3-yaml present")


def check_aegis_components() -> Check:
    return Check("aegis-components", PASS, f"aegis library {__version__} loaded")


def check_manifest() -> Check:
    try:
        raw = manifest.load_raw()
    except manifest.ManifestError as exc:
        return Check("manifest", FAIL, str(exc))
    errs, warns = manifest.validate(raw)
    n = len(raw.get("tools", []))
    if errs:
        return Check("manifest", FAIL, f"{len(errs)} error(s), first: {errs[0]}")
    if warns:
        return Check("manifest", WARN, f"{n} tools, {len(warns)} warning(s)")
    return Check("manifest", PASS, f"{n} tools valid")


def check_configuration() -> Check:
    state = Path("/etc/aegis")
    if not state.exists():
        return Check("configuration", PASS, "no local Aegis configuration (defaults in use)")
    return Check("configuration", PASS if os.access(state, os.R_OK) else FAIL, f"{state} readable")


def check_broken_packages() -> Check:
    if not pkg.have("dpkg"):
        return Check("broken-packages", WARN, "dpkg not available")
    issues = pkg.broken_packages()
    if issues:
        return Check("broken-packages", FAIL, f"dpkg --audit reports {len(issues)} line(s)")
    return Check("broken-packages", PASS, "dpkg --audit clean")


ALL_CHECKS = [check_os, check_kernel, check_package_manager, check_repositories, check_dns,
              check_connectivity, check_disk, check_time_sync, check_dependencies,
              check_aegis_components, check_manifest, check_configuration, check_broken_packages]


def run_all(checks=None) -> list[Check]:
    results = []
    for fn in checks or ALL_CHECKS:
        try:
            results.append(fn())
        except Exception as exc:  # a failing check must never crash the doctor
            results.append(Check(fn.__name__.removeprefix("check_").replace("_", "-"), FAIL, f"check crashed: {exc}"))
    return results


def exit_code(results: list[Check]) -> int:
    if any(r.status == FAIL for r in results):
        return 2
    if any(r.status == WARN for r in results):
        return 1
    return 0

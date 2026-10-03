"""Tool manager logic behind the `aegis` CLI."""
from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass

from . import pkg
from .manifest import Manifest, Tool

ONLINE = "ONLINE AVAILABLE"
OFFLINE = "OFFLINE AVAILABLE"
NEEDS_NET = "REQUIRES INTERNET"

NOTICES = {
    "authorized": "Use only against systems you own or have explicit written permission to test.",
    "lab": "Analyze samples only in an isolated laboratory environment.",
}


def availability(tool: Tool, checker=pkg.installed_version, resolver=pkg.candidate) -> str:
    """OFFLINE AVAILABLE: installed locally. ONLINE AVAILABLE: installable via configured APT
    repositories when online. REQUIRES INTERNET: external/container tools or unresolved packages."""
    if tool.installation_method == "apt" and checker(tool.package):
        return OFFLINE
    if tool.installation_method == "apt" and resolver(tool.package):
        return ONLINE
    return NEEDS_NET


@dataclass
class Plan:
    apt: list[str]
    skipped: list[tuple[str, str]]  # (tool, reason)


def plan_install(tools: list[Tool], resolver=pkg.candidate, checker=pkg.installed_version) -> Plan:
    apt: list[str] = []
    skipped: list[tuple[str, str]] = []
    for t in tools:
        if t.installation_method != "apt":
            skipped.append((t.name, f"{t.installation_method} install is not automated in this version"))
        elif checker(t.package):
            skipped.append((t.name, "already installed"))
        elif not resolver(t.package):
            skipped.append((t.name, f"package '{t.package}' has no candidate in configured repositories"))
        elif t.package not in apt:
            apt.append(t.package)
    return Plan(apt=apt, skipped=skipped)


def apt_cmd(action: str, packages: list[str], assume_yes: bool) -> list[str]:
    cmd = ["apt-get", action]
    if assume_yes:
        cmd.append("-y")
    return cmd + packages


def run_apt(cmd: list[str]) -> int:
    if os.geteuid() != 0:
        if pkg.have("sudo"):
            cmd = ["sudo", *cmd]
        else:
            print("error: root privileges required (run as root or install sudo)", file=sys.stderr)
            return 1
    return subprocess.call(cmd)


def check_packages(m: Manifest, resolver=pkg.candidate) -> dict[str, list[str]]:
    result = {"resolved": [], "unresolved": [], "not_apt": []}
    for t in m.tools:
        if t.installation_method != "apt":
            result["not_apt"].append(t.name)
        elif resolver(t.package):
            result["resolved"].append(t.name)
        else:
            result["unresolved"].append(t.name)
    return result

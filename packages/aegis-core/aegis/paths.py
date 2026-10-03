"""Locate Aegis data files (installed layout first, repository layout second)."""
from __future__ import annotations

import os
from pathlib import Path

INSTALLED_SHARE = Path("/usr/share/aegis")
REPO_ROOT = Path(__file__).resolve().parents[3]


def _first_existing(candidates):
    for c in candidates:
        if c and Path(c).is_file():
            return Path(c)
    return None


def version_file() -> Path | None:
    return _first_existing(
        [os.environ.get("AEGIS_VERSION_FILE"), INSTALLED_SHARE / "VERSION", REPO_ROOT / "VERSION"]
    )


def manifest_file() -> Path | None:
    return _first_existing(
        [
            os.environ.get("AEGIS_MANIFEST"),
            INSTALLED_SHARE / "manifest.yaml",
            REPO_ROOT / "tools" / "manifest.yaml",
        ]
    )


def read_version() -> str:
    vf = version_file()
    return vf.read_text(encoding="utf-8").strip() if vf else "unknown"

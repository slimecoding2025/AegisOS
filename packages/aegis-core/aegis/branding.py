"""Terminal banner and first-boot welcome text."""
from __future__ import annotations

from pathlib import Path

from . import __version__

TAGLINE = "Defend. Analyze. Understand."

LOGO = r"""
    _    _____ ____ ___ ____   ___  ____
   / \  | ____/ ___|_ _/ ___| / _ \/ ___|
  / _ \ |  _|| |  _ | |\___ \| | | \___ \
 / ___ \| |__| |_| || | ___) | |_| |___) |
/_/   \_\_____\____|___|____/ \___/|____/
"""


def banner() -> str:
    return f"{LOGO}\n  AegisOS {__version__}  -  {TAGLINE}\n"


WELCOME_STEPS = [
    ("Start Here", "Read the docs: /usr/share/doc/aegis-branding/ or the Documentation shortcut"),
    ("Tool Manager", "aegis list | aegis search <term> | aegis profile"),
    ("Security Center", "aegis security-center  (add --serve --open for the local dashboard)"),
    ("Documentation", "aegis info <tool>  shows license/homepage metadata (unverified fields say so)"),
    ("System Settings", "XFCE Settings Manager from the application menu"),
]


def welcome(marker: Path | None = None, force: bool = False) -> str:
    """Return welcome text; create the marker so the autostart entry only shows it once."""
    marker = marker or Path.home() / ".config" / "aegis" / "welcome-done"
    if marker.exists() and not force:
        return ""
    lines = [banner(), "First boot - where to go next:\n"]
    for title, hint in WELCOME_STEPS:
        lines.append(f"  * {title:<16} {hint}")
    lines.append("\nOffensive-security tools are for authorized testing and education only.")
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()
    except OSError:
        pass
    return "\n".join(lines) + "\n"

"""Tool manifest loading, validation and queries. tools/manifest.yaml is the source of truth."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import paths

TIERS = {"core", "optional", "external", "containerized", "development", "specialized"}
METHODS = {"apt", "external", "pipx", "container"}
REDISTRIBUTION = {"unverified", "allowed", "not-allowed"}
REQUIRED_TOOL_FIELDS = ("name", "category", "tier", "installation_method", "description")
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9.+_-]*$")
PKG_RE = re.compile(r"^[a-z0-9][a-z0-9.+-]+$")
URL_RE = re.compile(r"^https://[^\s]+$")
UNVERIFIED = "unverified"


class ManifestError(Exception):
    pass


@dataclass
class Tool:
    data: dict

    def __getattr__(self, item):
        try:
            return self.data[item]
        except KeyError as exc:
            raise AttributeError(item) from exc

    @property
    def categories(self) -> list[str]:
        return [self.data["category"], *self.data.get("also", [])]


@dataclass
class Manifest:
    raw: dict
    tools: list[Tool] = field(default_factory=list)

    @property
    def categories(self) -> dict:
        return self.raw.get("categories", {})

    @property
    def profiles(self) -> dict:
        return self.raw.get("profiles", {})

    def get(self, name: str) -> Tool | None:
        n = name.lower()
        return next((t for t in self.tools if t.name.lower() == n), None)

    def search(self, query: str) -> list[Tool]:
        q = query.lower()
        return [t for t in self.tools
                if q in t.name.lower() or q in t.description.lower() or q in t.category]

    def by_category(self, category: str) -> list[Tool]:
        return [t for t in self.tools if category in t.categories]

    def profile_tools(self, profile: str) -> list[Tool]:
        if profile not in self.profiles:
            raise ManifestError(f"unknown profile: {profile}")
        cats = set(self.profiles[profile]["categories"])
        return [t for t in self.tools if cats & set(t.categories)]

    def usage_notice(self, tool: Tool) -> str | None:
        cat = self.categories.get(tool.category, {})
        return cat.get("usage_notice")


def load_raw(path: str | Path | None = None) -> dict:
    p = Path(path) if path else paths.manifest_file()
    if not p or not Path(p).is_file():
        raise ManifestError("tool manifest not found")
    try:
        data = yaml.safe_load(Path(p).read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ManifestError(f"invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ManifestError("manifest root must be a mapping")
    return data


def build(raw: dict) -> Manifest:
    defaults = raw.get("defaults", {}) or {}
    tools = []
    for entry in raw.get("tools", []) or []:
        merged = {**defaults, **entry}
        tools.append(Tool(merged))
    return Manifest(raw=raw, tools=tools)


def validate(raw: dict) -> tuple[list[str], list[str]]:
    """Return (errors, warnings)."""
    errors: list[str] = []
    warns: list[str] = []
    if raw.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    cats = raw.get("categories") or {}
    profiles = raw.get("profiles") or {}
    if not cats:
        errors.append("categories section is empty")
    if not isinstance(raw.get("tools"), list) or not raw["tools"]:
        errors.append("tools must be a non-empty list")
        return errors, warns

    seen: set[str] = set()
    used_cats: set[str] = set()
    m = build(raw)
    for i, t in enumerate(m.tools):
        d = t.data
        label = d.get("name", f"#{i}")
        for f in REQUIRED_TOOL_FIELDS:
            if not d.get(f):
                errors.append(f"{label}: missing required field '{f}'")
        name = str(d.get("name", ""))
        if name and not NAME_RE.match(name):
            errors.append(f"{label}: invalid name")
        if name.lower() in seen:
            errors.append(f"{label}: duplicate tool name")
        seen.add(name.lower())
        for c in [d.get("category"), *d.get("also", [])]:
            if c and c not in cats:
                errors.append(f"{label}: unknown category '{c}'")
            used_cats.add(c)
        if d.get("tier") not in TIERS:
            errors.append(f"{label}: invalid tier '{d.get('tier')}'")
        method = d.get("installation_method")
        if method not in METHODS:
            errors.append(f"{label}: invalid installation_method '{method}'")
        pkg = d.get("package")
        if method == "apt":
            if not pkg or not PKG_RE.match(str(pkg)):
                errors.append(f"{label}: apt tools need a valid candidate package name")
        elif pkg:
            errors.append(f"{label}: package is only allowed for apt tools")
        if d.get("redistribution") not in REDISTRIBUTION:
            errors.append(f"{label}: invalid redistribution value")
        for f in ("homepage", "documentation"):
            v = d.get(f)
            if v != UNVERIFIED and not (isinstance(v, str) and URL_RE.match(v)):
                errors.append(f"{label}: {f} must be 'unverified' or an https URL")
        if not isinstance(d.get("bundled"), bool):
            errors.append(f"{label}: bundled must be true/false")
        if d.get("bundled") is True:
            if d.get("license") == UNVERIFIED:
                errors.append(f"{label}: bundled requires a verified license")
            if d.get("redistribution") != "allowed":
                errors.append(f"{label}: bundled requires redistribution 'allowed'")
            if method != "apt":
                errors.append(f"{label}: only apt tools can be bundled")
        if d.get("tier") == "core" and method != "apt":
            warns.append(f"{label}: core tier tool is not installable via apt")
    for pname, p in profiles.items():
        for c in p.get("categories", []):
            if c not in cats:
                errors.append(f"profile {pname}: unknown category '{c}'")
            elif not m.by_category(c):
                warns.append(f"profile {pname}: category '{c}' has no tools")
    for c in cats:
        if c not in used_cats:
            warns.append(f"category '{c}' has no tools")
    menu = set(raw.get("menu_categories", []))
    for c, meta in cats.items():
        if menu and meta.get("title") not in menu:
            errors.append(f"category {c}: title '{meta.get('title')}' not in menu_categories")
    return errors, warns


def load(path: str | Path | None = None, validate_first: bool = True) -> Manifest:
    raw = load_raw(path)
    if validate_first:
        errs, _ = validate(raw)
        if errs:
            raise ManifestError("manifest invalid: " + "; ".join(errs[:5]))
    return build(raw)


def package_list(m: Manifest, tiers: set[str]) -> list[str]:
    """Sorted, de-duplicated apt package names for tools in the given tiers (used to build the ISO)."""
    return sorted({t.package for t in m.tools if t.installation_method == "apt" and t.tier in tiers})

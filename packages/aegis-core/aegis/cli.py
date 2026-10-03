"""`aegis` command line interface."""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__, branding, desktop, doctor, hardening, manifest, pkg, security_center, tools

EXIT_OK, EXIT_ERROR = 0, 1


def _confirm(prompt: str, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    if not sys.stdin.isatty():
        print("refusing to continue without confirmation (use --yes in scripts)", file=sys.stderr)
        return False
    return input(f"{prompt} [y/N] ").strip().lower() in ("y", "yes")


def _load():
    try:
        return manifest.load()
    except manifest.ManifestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return None


def _row(t, m, with_avail=False):
    cols = [f"{t.name:<16}", f"{t.category:<20}", f"{t.tier:<13}"]
    if with_avail:
        cols.append(f"{tools.availability(t):<18}")
    cols.append(t.description)
    return " ".join(cols)


def cmd_version(a):
    print(f"aegis {__version__}")
    return EXIT_OK


def cmd_welcome(a):
    text = branding.welcome(force=a.force)
    if text:
        print(text)
    return EXIT_OK


def cmd_desktop_setup(a):
    res = desktop.apply_wallpaper(force=a.force, dry_run=a.dry_run)
    print(json.dumps(res, indent=2))
    return EXIT_OK if res["status"] in ("ok", "skipped", "dry-run") else EXIT_ERROR


def cmd_banner(a):
    print(branding.banner())
    return EXIT_OK


def cmd_search(a):
    m = _load()
    if not m:
        return EXIT_ERROR
    hits = m.search(a.query)
    for t in hits:
        print(_row(t, m))
    if not hits:
        print(f"no tools match '{a.query}'")
    return EXIT_OK if hits else EXIT_ERROR


def cmd_info(a):
    m = _load()
    if not m:
        return EXIT_ERROR
    t = m.get(a.name)
    if not t:
        print(f"error: unknown tool '{a.name}'", file=sys.stderr)
        return EXIT_ERROR
    info = {k: v for k, v in t.data.items()}
    info["availability"] = tools.availability(t)
    if t.installation_method == "apt":
        info["installed_version"] = pkg.installed_version(t.package)
        info["candidate_version"] = pkg.candidate(t.package)
    if a.json:
        print(json.dumps(info, indent=2))
    else:
        for k, v in info.items():
            print(f"{k:<20}: {v}")
    notice = m.usage_notice(t)
    if notice:
        print(f"\nNOTICE: {tools.NOTICES[notice]}")
    return EXIT_OK


def cmd_list(a):
    m = _load()
    if not m:
        return EXIT_ERROR
    items = m.tools
    if a.installed:
        items = [t for t in items if t.installation_method == "apt" and pkg.installed_version(t.package)]
    for t in items:
        print(_row(t, m, a.availability))
    print(f"\n{len(items)} tool(s)")
    return EXIT_OK


def cmd_category(a):
    m = _load()
    if not m:
        return EXIT_ERROR
    if not a.name:
        for c, meta in m.categories.items():
            print(f"{c:<24} {meta['title']:<22} {len(m.by_category(c))} tools")
        return EXIT_OK
    if a.name not in m.categories:
        print(f"error: unknown category '{a.name}' (run `aegis category`)", file=sys.stderr)
        return EXIT_ERROR
    for t in m.by_category(a.name):
        print(_row(t, m, a.availability))
    return EXIT_OK


def _do_install(names_tools, a, label):
    plan = tools.plan_install(names_tools)
    for name, reason in plan.skipped:
        print(f"skip   {name}: {reason}")
    if not plan.apt:
        print("nothing to install")
        return EXIT_OK
    print("apt packages:", " ".join(plan.apt))
    if a.dry_run:
        print("dry run: " + " ".join(tools.apt_cmd("install", plan.apt, a.yes)))
        return EXIT_OK
    if not _confirm(f"Install {len(plan.apt)} package(s) for {label}?", a.yes):
        return EXIT_ERROR
    return tools.run_apt(tools.apt_cmd("install", plan.apt, a.yes))


def cmd_install(a):
    m = _load()
    if not m:
        return EXIT_ERROR
    sel = []
    for n in a.names:
        t = m.get(n)
        if not t:
            print(f"error: unknown tool '{n}' (try `aegis search {n}`)", file=sys.stderr)
            return EXIT_ERROR
        notice = m.usage_notice(t)
        if notice:
            print(f"NOTICE ({t.name}): {tools.NOTICES[notice]}")
        sel.append(t)
    return _do_install(sel, a, ", ".join(a.names))


def cmd_remove(a):
    m = _load()
    if not m:
        return EXIT_ERROR
    for n in a.names:
        t = m.get(n)
        if not t:
            print(f"error: unknown tool '{n}'", file=sys.stderr)
            return EXIT_ERROR
        if t.installation_method != "apt":
            print(f"error: {n}: removal of {t.installation_method} tools is not automated", file=sys.stderr)
            return EXIT_ERROR
        shared = [o.name for o in m.tools if o.package == t.package and o.name != t.name]
        if shared:
            print(f"warning: package '{t.package}' also provides: {', '.join(shared)}")
    pkgs = sorted({m.get(n).package for n in a.names})
    if a.dry_run:
        print("dry run: " + " ".join(tools.apt_cmd("remove", pkgs, a.yes)))
        return EXIT_OK
    if not _confirm(f"Remove {', '.join(pkgs)}?", a.yes):
        return EXIT_ERROR
    return tools.run_apt(tools.apt_cmd("remove", pkgs, a.yes))


def cmd_profile(a):
    m = _load()
    if not m:
        return EXIT_ERROR
    if not a.name:
        for p, meta in m.profiles.items():
            print(f"{p:<22} {meta['description']} ({len(m.profile_tools(p))} tools)")
        return EXIT_OK
    if a.name not in m.profiles:
        print(f"error: unknown profile '{a.name}' (run `aegis profile`)", file=sys.stderr)
        return EXIT_ERROR
    sel = m.profile_tools(a.name)
    for t in sel:
        notice = m.usage_notice(t)
        if notice:
            print(f"NOTICE: {tools.NOTICES[notice]}")
            break
    return _do_install(sel, a, f"profile {a.name}")


def _check_repos_or_abort():
    c = doctor.check_repositories()
    if c.status == doctor.FAIL:
        print(f"error: repository validation failed: {c.detail}", file=sys.stderr)
        return False
    if c.status == doctor.WARN:
        print(f"warning: {c.detail}")
    return True


def cmd_update(a):
    if not _check_repos_or_abort():
        return EXIT_ERROR
    if a.dry_run:
        print("dry run: apt-get update")
        return EXIT_OK
    return tools.run_apt(["apt-get", "update"])


def cmd_upgrade(a):
    if not _check_repos_or_abort():
        return EXIT_ERROR
    cmd = tools.apt_cmd("upgrade", [], a.yes)
    if a.dry_run:
        print("dry run: " + " ".join(cmd))
        return EXIT_OK
    if not _confirm("Upgrade installed packages?", a.yes):
        return EXIT_ERROR
    return tools.run_apt(cmd)


def cmd_doctor(a):
    results = doctor.run_all()
    if a.json:
        print(json.dumps([r.__dict__ for r in results], indent=2))
    else:
        for r in results:
            print(f"{r.status:<4}  {r.name:<18} {r.detail}")
        counts = {s: sum(r.status == s for r in results) for s in (doctor.PASS, doctor.WARN, doctor.FAIL)}
        print(f"\n{counts['PASS']} PASS, {counts['WARN']} WARN, {counts['FAIL']} FAIL")
    return doctor.exit_code(results)


def cmd_hardening(a):
    try:
        if a.action == "status":
            print(json.dumps(hardening.status(), indent=2))
        elif a.action == "audit":
            bad = 0
            for f in hardening.audit():
                mark = "OK  " if f.ok else "DIFF"
                bad += not f.ok
                print(f"{mark} {f.key} = {f.current} (wanted {f.wanted}) - {f.why}")
            print(f"\n{bad} setting(s) differ from the Aegis hardening policy")
        elif a.action == "apply":
            if a.dry_run:
                print(hardening.apply(dry_run=True)["content"])
                return EXIT_OK
            if not _confirm("Write /etc/sysctl.d/90-aegis-hardening.conf and load it?", a.yes):
                return EXIT_ERROR
            res = hardening.apply()
            print(f"wrote {res['dropin']}; undo with `aegis hardening revert`")
        elif a.action == "revert":
            if not _confirm("Remove Aegis hardening drop-in and restore previous runtime values?", a.yes):
                return EXIT_ERROR
            res = hardening.revert()
            print("removed:", ", ".join(res["removed"]) or "nothing (was not applied)")
    except PermissionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    return EXIT_OK


def cmd_manifest(a):
    if a.action == "validate":
        try:
            raw = manifest.load_raw(a.path)
        except manifest.ManifestError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return EXIT_ERROR
        errs, warns = manifest.validate(raw)
        for w in warns:
            print(f"warning: {w}")
        for e in errs:
            print(f"error: {e}")
        print(f"{len(raw.get('tools', []))} tools, {len(errs)} error(s), {len(warns)} warning(s)")
        return EXIT_ERROR if errs else EXIT_OK
    m = _load()
    if not m:
        return EXIT_ERROR
    if a.action == "package-list":
        tiers = set(a.tier or ["core"])
        unknown = tiers - manifest.TIERS
        if unknown:
            print(f"error: unknown tier(s): {', '.join(sorted(unknown))}", file=sys.stderr)
            return EXIT_ERROR
        print("\n".join(manifest.package_list(m, tiers)))
        return EXIT_OK
    res = tools.check_packages(m)
    print(f"resolved in configured repositories: {len(res['resolved'])}")
    print(f"NOT resolved (no candidate): {len(res['unresolved'])}: {', '.join(res['unresolved'])}")
    print(f"not apt-managed: {len(res['not_apt'])}")
    print("note: results reflect THIS host's APT configuration (check on Debian 13 'trixie' for AegisOS)")
    return EXIT_OK


def cmd_security_center(a):
    if a.serve:
        security_center.serve(a.port, a.open)
        return EXIT_OK
    d = security_center.collect()
    print(json.dumps(d, indent=2) if a.json else security_center.render_text(d))
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="aegis", description="AegisOS tool manager (orchestrates apt; does not replace it)")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name, fn, help_):
        sp = sub.add_parser(name, help=help_)
        sp.set_defaults(fn=fn)
        return sp

    add("version", cmd_version, "show version")
    add("banner", cmd_banner, "print the AegisOS banner")
    s = add("desktop-setup", cmd_desktop_setup, "apply AegisOS desktop defaults for this user (once)")
    s.add_argument("--force", action="store_true"); s.add_argument("--dry-run", action="store_true")
    s = add("welcome", cmd_welcome, "first-boot welcome (shown once)"); s.add_argument("--force", action="store_true")
    s = add("search", cmd_search, "search the tool manifest"); s.add_argument("query")
    s = add("info", cmd_info, "show tool metadata"); s.add_argument("name"); s.add_argument("--json", action="store_true")
    s = add("list", cmd_list, "list tools")
    s.add_argument("--installed", action="store_true"); s.add_argument("--availability", action="store_true")
    s = add("category", cmd_category, "list categories or tools in a category")
    s.add_argument("name", nargs="?"); s.add_argument("--availability", action="store_true")
    for nm, fn, h in (("install", cmd_install, "install tools via apt"), ("remove", cmd_remove, "remove tools via apt")):
        s = add(nm, fn, h)
        s.add_argument("names", nargs="+")
        s.add_argument("--yes", "-y", action="store_true"); s.add_argument("--dry-run", action="store_true")
    s = add("profile", cmd_profile, "install a tool profile (no name: list profiles)")
    s.add_argument("name", nargs="?"); s.add_argument("--yes", "-y", action="store_true"); s.add_argument("--dry-run", action="store_true")
    s = add("update", cmd_update, "refresh package lists (apt-get update)"); s.add_argument("--dry-run", action="store_true")
    s = add("upgrade", cmd_upgrade, "upgrade packages (apt-get upgrade)")
    s.add_argument("--yes", "-y", action="store_true"); s.add_argument("--dry-run", action="store_true")
    s = add("doctor", cmd_doctor, "run health checks (exit 0 PASS, 1 WARN, 2 FAIL)"); s.add_argument("--json", action="store_true")
    s = add("hardening", cmd_hardening, "optional, reversible system hardening")
    s.add_argument("action", choices=["status", "audit", "apply", "revert"])
    s.add_argument("--yes", "-y", action="store_true"); s.add_argument("--dry-run", action="store_true")
    s = add("manifest", cmd_manifest, "validate manifest or check package candidates")
    s.add_argument("action", choices=["validate", "check-packages", "package-list"]); s.add_argument("--path")
    s.add_argument("--tier", action="append", help="tier(s) for package-list (default: core)")
    s = add("security-center", cmd_security_center, "system dashboard (text, JSON or local web UI)")
    s.add_argument("--json", action="store_true"); s.add_argument("--serve", action="store_true")
    s.add_argument("--open", action="store_true"); s.add_argument("--port", type=int, default=8765)
    return p


def main(argv=None) -> int:
    import signal

    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())

"""Aegis Security Center backend: collects real system data; optional read-only local web dashboard."""
from __future__ import annotations

import json
import os
import re
import socket
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import __version__, hardening, manifest, netinfo, pkg, sysinfo

UNAVAILABLE = "unavailable"


def firewall_status() -> dict:
    found = [c for c in ("ufw", "nft", "iptables") if pkg.have(c)]
    if not found:
        return {"state": "no firewall tool installed", "tools": []}
    if os.geteuid() != 0:
        return {"state": "installed; status needs root to query", "tools": found}
    if "ufw" in found:
        r = pkg.run(["ufw", "status"])
        first = (r.stdout.splitlines() or ["unknown"])[0]
        return {"state": first.strip(), "tools": found}
    if "nft" in found:
        r = pkg.run(["nft", "list", "ruleset"])
        return {"state": "nftables ruleset present" if r.stdout.strip() else "nftables ruleset empty", "tools": found}
    r = pkg.run(["iptables", "-S"])
    return {"state": f"iptables: {len(r.stdout.splitlines())} rule line(s)", "tools": found}


def update_status() -> dict:
    """Counts pending updates from the LOCAL package index (run `aegis update` to refresh it)."""
    if not pkg.have("apt-get"):
        return {"state": UNAVAILABLE, "reason": "apt-get not found"}
    r = pkg.run(["apt-get", "-s", "-o", "Debug::NoLocking=1", "upgrade"], timeout=90)
    if r.returncode != 0:
        return {"state": UNAVAILABLE, "reason": r.stderr.strip()[:200]}
    inst = [l for l in r.stdout.splitlines() if l.startswith("Inst ")]
    sec = [l for l in inst if re.search(r"-security|Debian-Security", l)]
    return {"state": "ok", "upgradable": len(inst), "security": len(sec),
            "note": "based on locally cached package lists"}


def running_services() -> dict:
    if not pkg.have("systemctl"):
        return {"state": UNAVAILABLE, "reason": "systemctl not found", "services": []}
    r = pkg.run(["systemctl", "list-units", "--type=service", "--state=running",
                 "--no-legend", "--plain", "--no-pager"])
    if r.returncode != 0:
        return {"state": UNAVAILABLE, "reason": ((r.stderr.strip().splitlines() or ["systemd not running"])[0])[:200], "services": []}
    names = [l.split()[0] for l in r.stdout.splitlines() if l.strip()]
    return {"state": "ok", "services": names}


def aegis_tools_installed() -> dict:
    try:
        m = manifest.load()
    except manifest.ManifestError as exc:
        return {"state": UNAVAILABLE, "reason": str(exc)}
    apt_tools = [t for t in m.tools if t.installation_method == "apt"]
    installed = sorted({t.name for t in apt_tools if pkg.installed_version(t.package)})
    return {"state": "ok", "installed": installed, "installed_count": len(installed),
            "manifest_total": len(m.tools), "apt_installable_total": len(apt_tools)}


def health() -> dict:
    mem = sysinfo.memory()
    disk = (sysinfo.disks() or [{"total_bytes": 0, "used_bytes": 0}])[0]
    try:
        load = os.getloadavg()
    except OSError:
        load = None
    return {
        "load_average": load,
        "memory_used_percent": round(mem["used_bytes"] * 100 / mem["total_bytes"], 1) if mem["total_bytes"] else None,
        "root_disk_used_percent": round(disk["used_bytes"] * 100 / disk["total_bytes"], 1) if disk["total_bytes"] else None,
        "uptime_seconds": sysinfo.uptime_seconds(),
    }


def collect() -> dict:
    osr = sysinfo.read_os_release()
    return {
        "aegis_version": __version__,
        "os": osr.get("PRETTY_NAME", "unknown"),
        "hostname": socket.gethostname(),
        "kernel": sysinfo.kernel(),
        "cpu": sysinfo.cpu(),
        "memory": sysinfo.memory(),
        "disks": sysinfo.disks(),
        "network": {"interfaces": netinfo.interfaces(), "routes": netinfo.routes(), "dns": netinfo.dns()},
        "firewall": firewall_status(),
        "security_updates": update_status(),
        "services": running_services(),
        "listening_ports": netinfo.listening(),
        "health": health(),
        "hardening": hardening.status(),
        "aegis_tools": aegis_tools_installed(),
    }


def render_text(d: dict) -> str:
    h = sysinfo.human_bytes
    mem = d["memory"]
    lines = [
        f"AegisOS {d['aegis_version']}  -  Security Center",
        f"OS        : {d['os']}   host: {d['hostname']}",
        f"Kernel    : {d['kernel']['release']} ({d['kernel']['machine']})",
        f"CPU       : {d['cpu']['model']} ({d['cpu']['logical_cpus']} logical)",
        f"Memory    : {h(mem['used_bytes'])} used of {h(mem['total_bytes'])}",
    ]
    for disk in d["disks"]:
        lines.append(f"Disk      : {disk['path']} {h(disk['used_bytes'])} used of {h(disk['total_bytes'])}")
    for i in d["network"]["interfaces"]:
        lines.append(f"Interface : {i['name']:<8} {i['state']:<8} {i['ipv4'] or '-':<16} {i['mac'] or '-'}")
    lines.append(f"DNS       : {', '.join(d['network']['dns']['nameservers']) or '-'}")
    lines.append(f"Firewall  : {d['firewall']['state']}")
    su = d["security_updates"]
    lines.append("Updates   : " + (f"{su['upgradable']} pending, {su['security']} security ({su['note']})"
                                   if su["state"] == "ok" else f"{su['state']} ({su.get('reason', '')})"))
    sv = d["services"]
    lines.append("Services  : " + (f"{len(sv['services'])} running" if sv["state"] == "ok"
                                   else f"{sv['state']} ({sv.get('reason', '')})"))
    lines.append(f"Listening : {len(d['listening_ports'])} socket(s)")
    for r in d["listening_ports"][:20]:
        lines.append(f"            {r['proto']:<5} {r['local']:<28} {r.get('process') or ''}")
    hd = d["hardening"]
    lines.append(f"Hardening : {hd['compliant']}/{hd['total']} sysctl checks compliant; "
                 f"{'applied' if hd['applied'] else 'not applied'}")
    t = d["aegis_tools"]
    lines.append("Tools     : " + (f"{t['installed_count']} installed of {t['apt_installable_total']} apt-installable "
                                   f"({t['manifest_total']} in manifest)" if t["state"] == "ok" else t["state"]))
    return "\n".join(lines)


PAGE = """<!doctype html><html lang="en"><meta charset="utf-8"><title>Aegis Security Center</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>:root{color-scheme:dark}body{font:14px system-ui,sans-serif;background:#10151c;color:#d7dee7;margin:0;padding:24px}
h1{font-size:20px;margin:0 0 4px}small{color:#8a97a6}section{background:#18202b;border:1px solid #263243;border-radius:8px;
padding:14px 16px;margin:14px 0}h2{font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:#6fb1d6;margin:0 0 8px}
table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:3px 8px 3px 0;vertical-align:top}pre{margin:0;white-space:pre-wrap}</style>
<h1>Aegis Security Center</h1><small id="sub">loading real system data&hellip;</small><div id="out"></div>
<script>
function sec(t,rows){const s=document.createElement('section');const h=document.createElement('h2');h.textContent=t;s.appendChild(h);
const tb=document.createElement('table');for(const r of rows){const tr=tb.insertRow();for(const c of r){tr.insertCell().textContent=c==null?'-':String(c)}}
s.appendChild(tb);document.getElementById('out').appendChild(s)}
fetch('/api/status').then(r=>r.json()).then(d=>{document.getElementById('sub').textContent='AegisOS '+d.aegis_version+' on '+d.os;
const mb=n=>(n/1048576).toFixed(0)+' MiB';
sec('System',[['Host',d.hostname],['Kernel',d.kernel.release],['CPU',d.cpu.model+' ('+d.cpu.logical_cpus+')'],
['Memory',mb(d.memory.used_bytes)+' used / '+mb(d.memory.total_bytes)],['Uptime (s)',d.health.uptime_seconds]]);
sec('Disks',d.disks.map(x=>[x.path,mb(x.used_bytes)+' used / '+mb(x.total_bytes)]));
sec('Network interfaces',d.network.interfaces.map(i=>[i.name,i.state,i.ipv4,i.mac]));
sec('DNS',[[d.network.dns.nameservers.join(', ')]]);
sec('Firewall',[[d.firewall.state]]);
const u=d.security_updates;sec('Updates',[[u.state=='ok'?u.upgradable+' pending, '+u.security+' security ('+u.note+')':u.state+' '+(u.reason||'')]]);
sec('Running services',[[d.services.state=='ok'?d.services.services.join(', '):d.services.state+' '+(d.services.reason||'')]]);
sec('Listening ports',d.listening_ports.map(r=>[r.proto,r.local,r.process]));
sec('Hardening',[[d.hardening.compliant+'/'+d.hardening.total+' compliant',d.hardening.applied?'applied':'not applied']]);
const t=d.aegis_tools;sec('Aegis tools',[[t.state=='ok'?t.installed_count+' installed of '+t.apt_installable_total+' apt-installable ('+t.manifest_total+' in manifest)':t.state]]);
}).catch(e=>{document.getElementById('sub').textContent='error: '+e});
</script></html>"""


def make_handler(port_getter):
    class Handler(BaseHTTPRequestHandler):
        server_version = "AegisSecurityCenter"

        def _allowed_host(self) -> bool:
            host = (self.headers.get("Host") or "").lower()
            return host in (f"127.0.0.1:{port_getter()}", f"localhost:{port_getter()}")

        def _send(self, code: int, body: bytes, ctype: str):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; "
                             "script-src 'unsafe-inline'; connect-src 'self'")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # noqa: N802
            if not self._allowed_host():
                return self._send(403, b"forbidden host", "text/plain")
            if self.path == "/":
                return self._send(200, PAGE.encode(), "text/html; charset=utf-8")
            if self.path == "/api/status":
                return self._send(200, json.dumps(collect()).encode(), "application/json")
            self._send(404, b"not found", "text/plain")

        def _deny(self):
            self._send(405, b"read-only service", "text/plain")

        do_POST = do_PUT = do_DELETE = do_PATCH = _deny  # noqa: N815

        def log_message(self, *args):  # keep the terminal quiet
            pass

    return Handler


def serve(port: int = 8765, open_browser: bool = False) -> None:
    holder = {}
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(lambda: holder["port"]))
    holder["port"] = httpd.server_address[1]
    url = f"http://127.0.0.1:{holder['port']}/"
    print(f"Aegis Security Center listening on {url} (Ctrl+C to stop)")
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()

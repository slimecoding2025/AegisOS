"""`aegis-net` command line interface (real data from /proc and /sys)."""
from __future__ import annotations

import argparse
import json
import sys

from . import netinfo


def _print_table(rows, cols):
    if not rows:
        print("(none)")
        return
    widths = [max(len(c), *(len(str(r.get(c, "") if r.get(c) is not None else "-")) for r in rows)) for c in cols]
    print("  ".join(c.upper().ljust(w) for c, w in zip(cols, widths)))
    for r in rows:
        print("  ".join(str(r.get(c) if r.get(c) is not None else "-").ljust(w) for c, w in zip(cols, widths)))


def main(argv=None) -> int:
    import signal

    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    p = argparse.ArgumentParser(prog="aegis-net", description="AegisOS network information")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("interfaces", "routes", "dns", "connections", "listening", "info"):
        sub.add_parser(name)
    a = p.parse_args(argv)

    if a.cmd == "interfaces":
        data = netinfo.interfaces()
    elif a.cmd == "routes":
        data = netinfo.routes()
    elif a.cmd == "dns":
        data = netinfo.dns()
    elif a.cmd == "connections":
        data = netinfo.connections()
    elif a.cmd == "listening":
        data = netinfo.listening()
    else:
        data = netinfo.info()

    if a.json:
        print(json.dumps(data, indent=2))
        return 0
    if a.cmd == "interfaces":
        _print_table([{**i, "ipv6": ",".join(i["ipv6"]) or None} for i in data],
                     ["name", "state", "ipv4", "ipv4_netmask", "mac", "mtu", "ipv6"])
    elif a.cmd == "routes":
        _print_table(data, ["destination", "gateway", "netmask", "interface", "metric"])
    elif a.cmd == "dns":
        print("nameservers:", ", ".join(data["nameservers"]) or "-")
        print("search:     ", ", ".join(data["search"]) or "-")
    elif a.cmd in ("connections", "listening"):
        _print_table(data, ["proto", "local", "remote", "state", "process"])
    else:
        print(f"hostname: {data['hostname']}")
        print("-- interfaces --")
        _print_table([{**i, "ipv6": ",".join(i["ipv6"]) or None} for i in data["interfaces"]],
                     ["name", "state", "ipv4", "mac"])
        print("-- routes --")
        _print_table(data["routes"], ["destination", "gateway", "interface"])
        print("-- dns --")
        print(", ".join(data["dns"]["nameservers"]) or "-")
    return 0


if __name__ == "__main__":
    sys.exit(main())

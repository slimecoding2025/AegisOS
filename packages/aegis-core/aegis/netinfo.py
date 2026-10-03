"""Linux network information parsed directly from /proc and /sys (no `ip` needed)."""
from __future__ import annotations

import fcntl
import socket
import struct
from pathlib import Path

SIOCGIFADDR = 0x8915
SIOCGIFNETMASK = 0x891B

TCP_STATES = {
    "01": "ESTABLISHED", "02": "SYN_SENT", "03": "SYN_RECV", "04": "FIN_WAIT1",
    "05": "FIN_WAIT2", "06": "TIME_WAIT", "07": "CLOSE", "08": "CLOSE_WAIT",
    "09": "LAST_ACK", "0A": "LISTEN", "0B": "CLOSING",
}


def _ioctl_addr(ifname: str, req: int) -> str | None:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        packed = struct.pack("256s", ifname.encode()[:15])
        res = fcntl.ioctl(s.fileno(), req, packed)
        return socket.inet_ntoa(res[20:24])
    except OSError:
        return None
    finally:
        s.close()


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def ipv6_addresses(path: str = "/proc/net/if_inet6") -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    try:
        lines = Path(path).read_text().splitlines()
    except OSError:
        return out
    for line in lines:
        parts = line.split()
        if len(parts) < 6:
            continue
        raw, prefix, name = parts[0], int(parts[2], 16), parts[5]
        groups = ":".join(raw[i:i + 4] for i in range(0, 32, 4))
        addr = socket.inet_ntop(socket.AF_INET6, socket.inet_pton(socket.AF_INET6, groups))
        out.setdefault(name, []).append(f"{addr}/{prefix}")
    return out


def interfaces(sys_net: str = "/sys/class/net") -> list[dict]:
    base = Path(sys_net)
    v6 = ipv6_addresses()
    result = []
    if not base.is_dir():
        return result
    for d in sorted(base.iterdir()):
        name = d.name
        ipv4 = _ioctl_addr(name, SIOCGIFADDR)
        mask = _ioctl_addr(name, SIOCGIFNETMASK) if ipv4 else None
        result.append({
            "name": name,
            "state": _read(d / "operstate") or "unknown",
            "mac": _read(d / "address"),
            "mtu": int(_read(d / "mtu") or 0),
            "ipv4": ipv4,
            "ipv4_netmask": mask,
            "ipv6": v6.get(name, []),
        })
    return result


def routes(path: str = "/proc/net/route") -> list[dict]:
    out = []
    try:
        lines = Path(path).read_text().splitlines()[1:]
    except OSError:
        return out
    for line in lines:
        f = line.split()
        if len(f) < 8:
            continue
        def ip(h):
            return socket.inet_ntoa(struct.pack("<L", int(h, 16)))
        flags = int(f[3], 16)
        out.append({
            "interface": f[0], "destination": ip(f[1]), "gateway": ip(f[2]),
            "netmask": ip(f[7]), "metric": int(f[6]), "up": bool(flags & 1),
            "is_gateway": bool(flags & 2),
        })
    return out


def dns(resolv: str = "/etc/resolv.conf") -> dict:
    servers, search = [], []
    try:
        for line in Path(resolv).read_text().splitlines():
            parts = line.split()
            if not parts or parts[0].startswith("#"):
                continue
            if parts[0] == "nameserver" and len(parts) > 1:
                servers.append(parts[1])
            elif parts[0] in ("search", "domain"):
                search.extend(parts[1:])
    except OSError:
        pass
    return {"nameservers": servers, "search": search}


def _decode_addr(hexaddr: str, v6: bool) -> str:
    host_hex, port_hex = hexaddr.split(":")
    port = int(port_hex, 16)
    if not v6:
        host = socket.inet_ntoa(struct.pack("<L", int(host_hex, 16)))
        return f"{host}:{port}"
    words = [host_hex[i:i + 8] for i in range(0, 32, 8)]
    raw = b"".join(struct.pack("<L", int(w, 16)) for w in words)
    return f"[{socket.inet_ntop(socket.AF_INET6, raw)}]:{port}"


def _parse_proc_net(path: str, proto: str, v6: bool) -> list[dict]:
    rows = []
    try:
        lines = Path(path).read_text().splitlines()[1:]
    except OSError:
        return rows
    for line in lines:
        f = line.split()
        if len(f) < 10:
            continue
        state = TCP_STATES.get(f[3], f[3]) if proto == "tcp" else ("UNCONN" if f[3] == "07" else f[3])
        rows.append({
            "proto": proto + ("6" if v6 else ""), "local": _decode_addr(f[1], v6),
            "remote": _decode_addr(f[2], v6), "state": state,
            "uid": int(f[7]), "inode": int(f[9]),
        })
    return rows


def _inode_to_process() -> dict[int, str]:
    """Best effort: map socket inodes to process names. Needs privileges for other users' processes."""
    mapping: dict[int, str] = {}
    for p in Path("/proc").iterdir():
        if not p.name.isdigit():
            continue
        try:
            name = (p / "comm").read_text().strip()
            for fd in (p / "fd").iterdir():
                try:
                    target = str(fd.readlink())
                except OSError:
                    continue
                if target.startswith("socket:["):
                    mapping[int(target[8:-1])] = f"{name}({p.name})"
        except OSError:
            continue
    return mapping


def connections(proc_root: str = "/proc/net", with_process: bool = True) -> list[dict]:
    rows = []
    for fname, proto, v6 in (("tcp", "tcp", False), ("tcp6", "tcp", True),
                             ("udp", "udp", False), ("udp6", "udp", True)):
        rows += _parse_proc_net(f"{proc_root}/{fname}", proto, v6)
    if with_process:
        m = _inode_to_process()
        for r in rows:
            r["process"] = m.get(r["inode"])
    return rows


def listening(proc_root: str = "/proc/net", with_process: bool = True) -> list[dict]:
    return [r for r in connections(proc_root, with_process)
            if r["state"] == "LISTEN" or (r["proto"].startswith("udp") and r["state"] == "UNCONN")]


def info() -> dict:
    return {
        "hostname": socket.gethostname(),
        "interfaces": interfaces(),
        "routes": routes(),
        "dns": dns(),
    }

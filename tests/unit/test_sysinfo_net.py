import tempfile
import unittest
from pathlib import Path

from aegis import netinfo, sysinfo

TCP = """  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode
   0: 0100007F:0050 00000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0 12345 1 0000
   1: 0100007F:C350 0100007F:0050 01 00000000:00000000 00:00000000 00000000  1000        0 54321 1 0000
"""
TCP6 = """  sl  local_address                         remote_address                        st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode
   0: 00000000000000000000000001000000:1F90 00000000000000000000000000000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0 777 1 0000
"""
ROUTE = """Iface\tDestination\tGateway \tFlags\tRefCnt\tUse\tMetric\tMask\t\tMTU\tWindow\tIRTT
eth0\t00000000\t0102A8C0\t0003\t0\t0\t100\t00000000\t0\t0\t0
eth0\t0002A8C0\t00000000\t0001\t0\t0\t100\t00FFFFFF\t0\t0\t0
"""


class NetParsing(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        (self.d / "tcp").write_text(TCP)
        (self.d / "tcp6").write_text(TCP6)
        (self.d / "udp").write_text(TCP.split("\n")[0] + "\n")
        (self.d / "udp6").write_text("header\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_ipv4_listening_and_established(self):
        rows = netinfo.connections(str(self.d), with_process=False)
        listen = [r for r in rows if r["state"] == "LISTEN" and r["proto"] == "tcp"]
        self.assertEqual(listen[0]["local"], "127.0.0.1:80")
        est = [r for r in rows if r["state"] == "ESTABLISHED"][0]
        self.assertEqual((est["local"], est["remote"], est["uid"]), ("127.0.0.1:50000", "127.0.0.1:80", 1000))

    def test_ipv6_decoding(self):
        rows = netinfo.listening(str(self.d), with_process=False)
        v6 = [r for r in rows if r["proto"] == "tcp6"][0]
        self.assertEqual(v6["local"], "[::1]:8080")

    def test_listening_excludes_established(self):
        rows = netinfo.listening(str(self.d), with_process=False)
        self.assertTrue(all(r["state"] == "LISTEN" for r in rows))

    def test_routes_parse(self):
        p = self.d / "route"
        p.write_text(ROUTE)
        r = netinfo.routes(str(p))
        self.assertEqual(r[0]["gateway"], "192.168.2.1")
        self.assertTrue(r[0]["is_gateway"])
        self.assertEqual(r[1]["netmask"], "255.255.255.0")

    def test_dns_parse(self):
        p = self.d / "resolv.conf"
        p.write_text("# c\nnameserver 9.9.9.9\nnameserver 1.1.1.1\nsearch example.test lan\n")
        self.assertEqual(netinfo.dns(str(p)), {"nameservers": ["9.9.9.9", "1.1.1.1"], "search": ["example.test", "lan"]})

    def test_missing_files_do_not_crash(self):
        self.assertEqual(netinfo.routes("/nonexistent"), [])
        self.assertEqual(netinfo.dns("/nonexistent"), {"nameservers": [], "search": []})

    def test_ipv6_addresses_parse(self):
        p = self.d / "if_inet6"
        p.write_text("00000000000000000000000000000001 01 80 10 80       lo\n")
        self.assertEqual(netinfo.ipv6_addresses(str(p)), {"lo": ["::1/128"]})

    def test_real_interfaces_include_loopback(self):
        names = [i["name"] for i in netinfo.interfaces()]
        self.assertIn("lo", names)
        lo = next(i for i in netinfo.interfaces() if i["name"] == "lo")
        self.assertEqual(lo["ipv4"], "127.0.0.1")


class SysInfo(unittest.TestCase):
    def test_os_release_parse(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d, "os-release")
            p.write_text('# c\nNAME="AegisOS"\nID=aegisos\nPRETTY_NAME="AegisOS 0.1.0"\n')
            r = sysinfo.read_os_release(str(p))
            self.assertEqual((r["ID"], r["PRETTY_NAME"]), ("aegisos", "AegisOS 0.1.0"))

    def test_memory_parse(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d, "meminfo")
            p.write_text("MemTotal:        1000 kB\nMemAvailable:     400 kB\n")
            m = sysinfo.memory(str(p))
            self.assertEqual((m["total_bytes"], m["used_bytes"]), (1024000, 614400))

    def test_real_values_are_sane(self):
        self.assertTrue(sysinfo.kernel()["release"])
        self.assertGreater(sysinfo.memory()["total_bytes"], 0)
        self.assertGreaterEqual(sysinfo.cpu()["logical_cpus"], 1)
        self.assertGreater(sysinfo.disks()[0]["total_bytes"], 0)

    def test_human_bytes(self):
        self.assertEqual(sysinfo.human_bytes(512), "512 B")
        self.assertEqual(sysinfo.human_bytes(2048), "2.0 KiB")


if __name__ == "__main__":
    unittest.main()

import unittest

from aegis import manifest, tools
from tests import ROOT


class Tools(unittest.TestCase):
    def setUp(self):
        self.m = manifest.load(ROOT / "tools" / "manifest.yaml")

    def test_availability_labels(self):
        nmap = self.m.get("nmap")
        rustscan = self.m.get("rustscan")
        self.assertEqual(tools.availability(nmap, checker=lambda p: "1", resolver=lambda p: "1"), tools.OFFLINE)
        self.assertEqual(tools.availability(nmap, checker=lambda p: None, resolver=lambda p: "1"), tools.ONLINE)
        self.assertEqual(tools.availability(nmap, checker=lambda p: None, resolver=lambda p: None), tools.NEEDS_NET)
        self.assertEqual(tools.availability(rustscan, checker=lambda p: "1", resolver=lambda p: "1"), tools.NEEDS_NET)

    def test_plan_install_filters_correctly(self):
        sel = [self.m.get(n) for n in ("nmap", "rustscan", "masscan", "tcpdump")]
        plan = tools.plan_install(sel, resolver=lambda p: None if p == "masscan" else "1",
                                  checker=lambda p: "1" if p == "tcpdump" else None)
        self.assertEqual(plan.apt, ["nmap"])
        reasons = dict(plan.skipped)
        self.assertIn("not automated", reasons["rustscan"])
        self.assertIn("no candidate", reasons["masscan"])
        self.assertEqual(reasons["tcpdump"], "already installed")

    def test_plan_deduplicates_shared_packages(self):
        sel = [self.m.get("dig"), self.m.get("nslookup")]
        plan = tools.plan_install(sel, resolver=lambda p: "1", checker=lambda p: None)
        self.assertEqual(plan.apt, ["bind9-dnsutils"])

    def test_apt_cmd(self):
        self.assertEqual(tools.apt_cmd("install", ["a"], True), ["apt-get", "install", "-y", "a"])
        self.assertEqual(tools.apt_cmd("upgrade", [], False), ["apt-get", "upgrade"])

    def test_check_packages_partitions(self):
        res = tools.check_packages(self.m, resolver=lambda p: "1" if p == "nmap" else None)
        self.assertIn("nmap", res["resolved"])
        self.assertIn("rustscan", res["not_apt"])
        self.assertIn("masscan", res["unresolved"])


if __name__ == "__main__":
    unittest.main()

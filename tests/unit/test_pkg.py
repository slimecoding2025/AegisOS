import os
import stat
import tempfile
import unittest
from unittest import mock

from aegis import pkg, security_center


class Have(unittest.TestCase):
    def test_finds_tools_in_sbin_even_when_not_on_path(self):
        with tempfile.TemporaryDirectory() as sbin:
            tool = os.path.join(sbin, "fake-fw-tool")
            with open(tool, "w") as f:
                f.write("#!/bin/sh\n")
            os.chmod(tool, os.stat(tool).st_mode | stat.S_IXUSR)
            with mock.patch.dict(os.environ, {"PATH": "/nonexistent"}), mock.patch.object(pkg, "SBIN_DIRS", [sbin]):
                self.assertTrue(pkg.have("fake-fw-tool"))
                self.assertFalse(pkg.have("definitely-not-a-tool"))

    def test_firewall_status_unprivileged_reports_installed_tool(self):
        def have(c):
            return c == "nft"
        with mock.patch.object(security_center.pkg, "have", have), mock.patch("os.geteuid", return_value=1000):
            res = security_center.firewall_status()
        self.assertEqual(res["tools"], ["nft"])
        self.assertIn("needs root", res["state"])

    def test_firewall_status_none_installed(self):
        with mock.patch.object(security_center.pkg, "have", lambda c: False):
            self.assertEqual(security_center.firewall_status()["tools"], [])


if __name__ == "__main__":
    unittest.main()

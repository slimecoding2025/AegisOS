import json
import os
import subprocess
import sys
import unittest

from tests import ROOT

ENV = {**os.environ, "PYTHONPATH": str(ROOT / "packages/aegis-core")}


def aegis(*args, module="aegis.cli"):
    return subprocess.run([sys.executable, "-m", module, *args], capture_output=True, text=True, env=ENV, timeout=120)


class Integration(unittest.TestCase):
    def test_entry_point_wrappers_exist_and_are_executable(self):
        for n in ("aegis", "aegis-net", "aegis-security-center"):
            p = ROOT / "packages/aegis-cli/bin" / n
            self.assertTrue(os.access(p, os.X_OK), n)
            self.assertTrue(p.read_text().startswith("#!/usr/bin/python3"))

    def test_version_end_to_end(self):
        r = aegis("version")
        self.assertEqual(r.stdout.strip(), "aegis " + (ROOT / "VERSION").read_text().strip())

    def test_doctor_exit_code_matches_json(self):
        r = aegis("doctor", "--json")
        results = json.loads(r.stdout)
        expected = 2 if any(x["status"] == "FAIL" for x in results) else 1 if any(x["status"] == "WARN" for x in results) else 0
        self.assertEqual(r.returncode, expected)

    def test_profile_dry_run_uses_manifest_packages(self):
        r = aegis("profile", "forensics", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue("sleuthkit" in r.stdout or "no candidate" in r.stdout or "already installed" in r.stdout)

    def test_aegis_net_json_roundtrip(self):
        r = aegis("--json", "info", module="aegis.net_cli")
        data = json.loads(r.stdout)
        self.assertIn("interfaces", data)
        self.assertIn("lo", [i["name"] for i in data["interfaces"]])

    def test_security_center_json(self):
        r = aegis("security-center", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertGreater(json.loads(r.stdout)["memory"]["total_bytes"], 0)

    def test_generated_docs_are_current(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts/gen-tool-docs.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)


if __name__ == "__main__":
    unittest.main()

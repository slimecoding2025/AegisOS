import os
import shutil
import subprocess
import unittest

from tests import ROOT

SCRIPTS = sorted([*(ROOT / "scripts").glob("*.sh"), ROOT / "build/config/auto/config",
                  *(p for p in (ROOT / "build/config/hooks").rglob("*") if p.is_file())])


class ShellScripts(unittest.TestCase):
    def test_bash_syntax(self):
        self.assertGreaterEqual(len(SCRIPTS), 8)
        for s in SCRIPTS:
            r = subprocess.run(["bash", "-n", str(s)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"{s}: {r.stderr}")

    def test_scripts_are_executable_and_strict(self):
        for s in (ROOT / "scripts").glob("*.sh"):
            self.assertTrue(os.access(s, os.X_OK), s)
            self.assertIn("set -", s.read_text(), s)

    @unittest.skipUnless(shutil.which("shellcheck"), "shellcheck not installed (NOT VERIFIED here)")
    def test_shellcheck(self):
        r = subprocess.run(["shellcheck", *map(str, SCRIPTS)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)

    @unittest.skipIf(shutil.which("lb"), "live-build present: do not start a real build in a unit test")
    def test_build_fails_cleanly_without_live_build(self):
        r = subprocess.run([str(ROOT / "scripts/build.sh")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn("missing required tools", r.stderr)
        self.assertEqual(list((ROOT / "dist").glob("*.iso")) if (ROOT / "dist").exists() else [], [])

    def test_clean_script_is_safe_to_run_twice(self):
        for _ in range(2):
            self.assertEqual(subprocess.run([str(ROOT / "scripts/clean.sh")], capture_output=True).returncode, 0)
        subprocess.run([str(ROOT / "scripts/build-debs.sh")], capture_output=True)  # restore dist/debs for later tests


if __name__ == "__main__":
    unittest.main()

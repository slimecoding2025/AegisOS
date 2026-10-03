import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests import ROOT

NEED = shutil.which("dpkg-deb")


@unittest.skipUnless(NEED, "dpkg-deb not available")
class Debs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        r = subprocess.run([str(ROOT / "scripts/build-debs.sh"), str(cls.out)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        cls.version = (ROOT / "VERSION").read_text().strip()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def field(self, deb, name):
        return subprocess.run(["dpkg-deb", "-f", str(deb), name], capture_output=True, text=True).stdout.strip()

    def contents(self, pkg):
        deb = self.out / f"{pkg}_{self.version}_all.deb"
        return subprocess.run(["dpkg-deb", "-c", str(deb)], capture_output=True, text=True).stdout

    def test_five_debs_with_consistent_version(self):
        debs = sorted(self.out.glob("*.deb"))
        self.assertEqual(len(debs), 5)
        for d in debs:
            self.assertEqual(self.field(d, "Version"), self.version)
            self.assertNotIn("@VERSION@", subprocess.run(["dpkg-deb", "-I", str(d)], capture_output=True, text=True).stdout)

    def test_contents(self):
        self.assertIn("./usr/bin/aegis\n", self.contents("aegis-cli"))
        self.assertIn("./usr/bin/aegis-net\n", self.contents("aegis-cli"))
        self.assertIn("./usr/share/aegis/manifest.yaml", self.contents("aegis-tools"))
        self.assertIn("./usr/lib/aegis/aegis/cli.py", self.contents("aegis-core"))
        self.assertNotIn("__pycache__", self.contents("aegis-core"))
        self.assertIn("./etc/profile.d/aegis-banner.sh", self.contents("aegis-branding"))
        self.assertIn("./usr/share/backgrounds/aegisos/aegis-dark.svg", self.contents("aegis-branding"))

    def test_files_owned_by_root(self):
        for pkg in ("aegis-core", "aegis-cli", "aegis-tools", "aegis-security-center", "aegis-branding"):
            for line in self.contents(pkg).splitlines():
                self.assertIn("root/root", line)

    def test_installed_layout_runs(self):
        import os
        with tempfile.TemporaryDirectory() as root:
            for d in self.out.glob("*.deb"):
                subprocess.run(["dpkg-deb", "-x", str(d), root], check=True)
            env = {"PATH": os.environ["PATH"], "PYTHONPATH": f"{root}/usr/lib/aegis",
                   "AEGIS_MANIFEST": f"{root}/usr/share/aegis/manifest.yaml",
                   "AEGIS_VERSION_FILE": f"{root}/usr/share/aegis/VERSION"}
            r = subprocess.run(["python3", "-c", "import sys; from aegis.cli import main; sys.exit(main(['version']))"],
                               capture_output=True, text=True, env=env)
            self.assertEqual(r.stdout.strip(), f"aegis {self.version}")

    def test_pure_package_dependency_on_version_is_exact(self):
        self.assertIn(f"aegis-core (= {self.version})", self.field(self.out / f"aegis-cli_{self.version}_all.deb", "Depends"))


if __name__ == "__main__":
    unittest.main()

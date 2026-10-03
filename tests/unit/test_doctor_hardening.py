import json
import tempfile
import unittest
from pathlib import Path

from aegis import doctor, hardening


class Doctor(unittest.TestCase):
    def mkroot(self, text, name="sources.list"):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        apt = Path(d.name, "etc/apt")
        target = apt if name == "sources.list" else apt / "sources.list.d"
        target.mkdir(parents=True)
        (target / name).write_text(text)
        return d.name

    def test_repositories_pass(self):
        r = doctor.check_repositories(self.mkroot("deb https://deb.debian.org/debian trixie main\n"))
        self.assertEqual(r.status, doctor.PASS)

    def test_repositories_http_warns(self):
        r = doctor.check_repositories(self.mkroot("deb http://deb.debian.org/debian trixie main\n"))
        self.assertEqual(r.status, doctor.WARN)

    def test_repositories_trusted_yes_fails(self):
        r = doctor.check_repositories(self.mkroot("deb [trusted=yes] https://x.invalid/ stable main\n"))
        self.assertEqual(r.status, doctor.FAIL)

    def test_repositories_missing_or_empty_fails(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(doctor.check_repositories(d).status, doctor.FAIL)
        self.assertEqual(doctor.check_repositories(self.mkroot("# only comments\n")).status, doctor.FAIL)

    def test_commented_trusted_yes_is_ignored(self):
        r = doctor.check_repositories(self.mkroot("# deb [trusted=yes] https://x.invalid/ a b\ndeb https://deb.debian.org/debian trixie main\n"))
        self.assertEqual(r.status, doctor.PASS)

    def test_unsigned_repo_detail_names_file_and_line(self):
        r = doctor.check_repositories(self.mkroot("deb [ trusted=yes ] file:/root/pkgs ./\n", name="live.list"))
        self.assertEqual(r.status, doctor.WARN)
        self.assertIn("live.list", r.detail)
        self.assertIn("file:/root/pkgs", r.detail)

    def test_unsigned_local_file_repo_is_warning_not_failure(self):
        # Exact layout observed on the first AegisOS live boot (2026-10-03).
        text = ("deb [trusted=yes] file:/run/live/medium trixie main contrib non-free-firmware\n"
                "deb http://deb.debian.org/debian/ trixie main contrib non-free-firmware\n")
        r = doctor.check_repositories(self.mkroot(text))
        self.assertEqual(r.status, doctor.WARN)
        self.assertIn("unsigned local repository", r.detail)
        self.assertIn("plain-HTTP", r.detail)

    def test_unsigned_network_repo_still_fails_even_next_to_local_one(self):
        text = ("deb [trusted=yes] file:/run/live/medium trixie main\n"
                "deb [trusted=yes] http://evil.invalid/debian trixie main\n")
        self.assertEqual(doctor.check_repositories(self.mkroot(text)).status, doctor.FAIL)

    def test_deb822_trusted_yes_fails(self):
        r = doctor.check_repositories(self.mkroot("Types: deb\nURIs: https://x.invalid\nSuites: stable\nTrusted: yes\n", name="x.sources"))
        self.assertEqual(r.status, doctor.FAIL)

    def test_exit_codes(self):
        C = doctor.Check
        self.assertEqual(doctor.exit_code([C("a", doctor.PASS, "")]), 0)
        self.assertEqual(doctor.exit_code([C("a", doctor.PASS, ""), C("b", doctor.WARN, "")]), 1)
        self.assertEqual(doctor.exit_code([C("a", doctor.WARN, ""), C("b", doctor.FAIL, "")]), 2)

    def test_crashing_check_becomes_fail(self):
        def check_boom():
            raise RuntimeError("x")
        res = doctor.run_all([check_boom])
        self.assertEqual(res[0].status, doctor.FAIL)

    def test_manifest_and_dependency_checks_pass_in_repo(self):
        self.assertEqual(doctor.check_manifest().status, doctor.PASS)
        self.assertEqual(doctor.check_dependencies().status, doctor.PASS)

    def test_all_checks_run_and_return_valid_status(self):
        res = doctor.run_all()
        self.assertEqual(len(res), len(doctor.ALL_CHECKS))
        self.assertTrue(all(r.status in (doctor.PASS, doctor.WARN, doctor.FAIL) for r in res))

    def test_disk_thresholds(self):
        self.assertEqual(doctor.check_disk("/", warn_pct=0, fail_pct=101).status, doctor.WARN)
        self.assertEqual(doctor.check_disk("/", warn_pct=101, fail_pct=102).status, doctor.PASS)
        self.assertEqual(doctor.check_disk("/", warn_pct=0, fail_pct=0).status, doctor.FAIL)


class Hardening(unittest.TestCase):
    def fake_proc(self, values):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        for k, v in values.items():
            p = Path(d.name, k.replace(".", "/"))
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(v + "\n")
        return d.name

    def test_audit_detects_difference(self):
        proc = self.fake_proc({"kernel.kptr_restrict": "0", "kernel.dmesg_restrict": "1"})
        by_key = {f.key: f for f in hardening.audit(proc)}
        self.assertFalse(by_key["kernel.kptr_restrict"].ok)
        self.assertTrue(by_key["kernel.dmesg_restrict"].ok)
        self.assertIsNone(by_key["fs.protected_symlinks"].current)

    def test_policy_does_not_touch_ptrace_scope(self):
        self.assertNotIn("kernel.yama.ptrace_scope", hardening.SYSCTL_POLICY)

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as root:
            res = hardening.apply(root=root, dry_run=True)
            self.assertIn("kernel.kptr_restrict = 2", res["content"])
            self.assertFalse(hardening.is_applied(root))

    def test_apply_then_revert_roundtrip(self):
        proc = self.fake_proc({"kernel.kptr_restrict": "0"})
        with tempfile.TemporaryDirectory() as root:
            hardening.apply(root=root, reload=False, proc_root=proc)
            self.assertTrue(hardening.is_applied(root))
            state = json.loads(Path(root, hardening.STATE).read_text())
            self.assertEqual(state["previous_values"]["kernel.kptr_restrict"], "0")
            res = hardening.revert(root=root, reload=False)
            self.assertEqual(len(res["removed"]), 2)
            self.assertFalse(hardening.is_applied(root))

    def test_revert_when_not_applied_is_harmless(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(hardening.revert(root=root, reload=False)["removed"], [])

    def test_status_counts(self):
        proc = self.fake_proc({k: v[0] for k, v in hardening.SYSCTL_POLICY.items()})
        with tempfile.TemporaryDirectory() as root:
            s = hardening.status(root, proc)
            self.assertEqual((s["compliant"], s["total"], s["applied"]), (10, 10, False))


if __name__ == "__main__":
    unittest.main()

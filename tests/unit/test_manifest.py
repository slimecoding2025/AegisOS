import copy
import unittest

from aegis import manifest
from tests import ROOT


def base():
    return {
        "schema_version": 1,
        "defaults": {"bundled": False, "license": "unverified", "homepage": "unverified",
                     "documentation": "unverified", "redistribution": "unverified", "dependencies": [],
                     "package": None},
        "categories": {"network": {"title": "Network Security"}},
        "profiles": {"network": {"description": "x", "categories": ["network"]}},
        "tools": [{"name": "nmap", "category": "network", "tier": "core", "installation_method": "apt",
                   "package": "nmap", "description": "scanner"}],
    }


class RealManifest(unittest.TestCase):
    def test_real_manifest_is_valid(self):
        errors, warnings = manifest.validate(manifest.load_raw(ROOT / "tools" / "manifest.yaml"))
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_nothing_is_marked_verified_or_bundled_without_evidence(self):
        m = manifest.load(ROOT / "tools" / "manifest.yaml")
        self.assertGreater(len(m.tools), 100)
        for t in m.tools:
            self.assertFalse(t.bundled, t.name)
            self.assertEqual(t.license, "unverified", t.name)
            self.assertEqual(t.homepage, "unverified", t.name)

    def test_required_ecosystem_tools_present(self):
        m = manifest.load(ROOT / "tools" / "manifest.yaml")
        for name in ("nmap", "wireshark", "sqlmap", "yara", "ghidra", "aircrack-ng", "john", "trivy", "gnupg", "htop", "cmake"):
            self.assertIsNotNone(m.get(name), name)

    def test_all_requested_profiles_exist_and_have_tools(self):
        m = manifest.load(ROOT / "tools" / "manifest.yaml")
        for p in ("network web osint forensics blue-team soc wireless reverse-engineering "
                  "malware-analysis cloud containers development").split():
            self.assertIn(p, m.profiles)
            self.assertTrue(m.profile_tools(p), p)

    def test_profile_membership_uses_secondary_categories(self):
        m = manifest.load(ROOT / "tools" / "manifest.yaml")
        self.assertIn("yara", [t.name for t in m.profile_tools("soc")])
        self.assertIn("trivy", [t.name for t in m.profile_tools("containers")])

    def test_menu_has_requested_categories(self):
        raw = manifest.load_raw(ROOT / "tools" / "manifest.yaml")
        for c in ("Network Security", "Web Security", "OSINT", "Digital Forensics", "Blue Team", "SOC",
                  "Reverse Engineering", "Wireless", "Cloud Security", "Container Security",
                  "System Administration", "Development", "Utilities"):
            self.assertIn(c, raw["menu_categories"])

    def test_package_list_only_apt_core(self):
        m = manifest.load(ROOT / "tools" / "manifest.yaml")
        pl = manifest.package_list(m, {"core"})
        self.assertIn("nmap", pl)
        self.assertNotIn("rustscan", pl)
        self.assertEqual(pl, sorted(set(pl)))


class HostVerifiedFindings(unittest.TestCase):
    """Results of `aegis manifest check-packages` on a Debian 13.7 live image (2026-10-03)."""

    NOT_IN_DEBIAN_13 = ("amass feroxbuster nikto commix theharvester metagoofil volatility3 zeek ghidra "
                        "radare2 cutter kismet seclists").split()

    def test_unresolved_tools_are_external_with_evidence_note(self):
        m = manifest.load(ROOT / "tools" / "manifest.yaml")
        for name in self.NOT_IN_DEBIAN_13:
            t = m.get(name)
            self.assertEqual(t.installation_method, "external", name)
            self.assertEqual(t.tier, "external", name)
            self.assertIsNone(t.package, name)
            self.assertIn("2026-10-03", t.notes, name)

    def test_verification_log_present(self):
        raw = manifest.load_raw(ROOT / "tools" / "manifest.yaml")
        self.assertTrue(any("95" in x and "13" in x for x in raw["verification_log"]))

    def test_apt_entries_count(self):
        m = manifest.load(ROOT / "tools" / "manifest.yaml")
        self.assertEqual(sum(t.installation_method == "apt" for t in m.tools), 95)


class Validation(unittest.TestCase):
    def test_unknown_tool_field_is_rejected(self):
        raw = base()
        raw["tools"][0]["licence"] = "typo"
        self.assertTrue(any("unknown field 'licence'" in e for e in manifest.validate(raw)[0]))

    def test_notes_must_be_string(self):
        raw = base()
        raw["tools"][0]["notes"] = 5
        self.assertTrue(any("notes must be a string" in e for e in manifest.validate(raw)[0]))

    def test_verification_log_must_be_list_of_strings(self):
        raw = base()
        raw["verification_log"] = "x"
        self.assertTrue(any("verification_log" in e for e in manifest.validate(raw)[0]))

    def errs(self, mutate):
        raw = base()
        mutate(raw)
        return manifest.validate(raw)[0]

    def test_base_is_valid(self):
        self.assertEqual(manifest.validate(base()), ([], []))

    def test_duplicate_name(self):
        e = self.errs(lambda r: r["tools"].append(copy.deepcopy(r["tools"][0])))
        self.assertTrue(any("duplicate" in x for x in e))

    def test_unknown_category_and_tier(self):
        e = self.errs(lambda r: r["tools"][0].update(category="nope", tier="huge"))
        self.assertTrue(any("unknown category" in x for x in e))
        self.assertTrue(any("invalid tier" in x for x in e))

    def test_apt_requires_package_and_others_forbid_it(self):
        e = self.errs(lambda r: r["tools"][0].update(package=None))
        self.assertTrue(any("candidate package" in x for x in e))
        e = self.errs(lambda r: r["tools"][0].update(installation_method="external"))
        self.assertTrue(any("only allowed for apt" in x for x in e))

    def test_bundled_requires_verified_license_and_redistribution(self):
        e = self.errs(lambda r: r["tools"][0].update(bundled=True))
        self.assertTrue(any("verified license" in x for x in e))
        self.assertTrue(any("redistribution" in x for x in e))

    def test_bundled_ok_when_verified(self):
        e = self.errs(lambda r: r["tools"][0].update(bundled=True, license="GPL-2.0-only", redistribution="allowed"))
        self.assertEqual(e, [])

    def test_urls_must_be_https_or_unverified(self):
        e = self.errs(lambda r: r["tools"][0].update(homepage="http://example.invalid"))
        self.assertTrue(any("homepage" in x for x in e))
        e = self.errs(lambda r: r["tools"][0].update(homepage="https://example.org/"))
        self.assertEqual(e, [])

    def test_profile_unknown_category(self):
        e = self.errs(lambda r: r["profiles"]["network"].update(categories=["ghost"]))
        self.assertTrue(any("profile network" in x for x in e))

    def test_bad_schema_version_and_empty_tools(self):
        self.assertTrue(manifest.validate({"schema_version": 2, "categories": {"a": {}}, "tools": []})[0])

    def test_invalid_yaml_raises(self):
        import tempfile, pathlib
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d, "m.yaml")
            p.write_text("tools: [unclosed")
            with self.assertRaises(manifest.ManifestError):
                manifest.load_raw(p)


if __name__ == "__main__":
    unittest.main()

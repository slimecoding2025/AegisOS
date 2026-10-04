import configparser
import re
import unittest
import xml.dom.minidom as minidom

from tests import ROOT


class Config(unittest.TestCase):
    def test_version_is_semver(self):
        self.assertRegex((ROOT / "VERSION").read_text().strip(), r"^\d+\.\d+\.\d+$")

    def test_debian_control_files(self):
        v = (ROOT / "VERSION").read_text().strip()
        for pkg in ("aegis-core", "aegis-cli", "aegis-tools", "aegis-security-center", "aegis-branding"):
            text = (ROOT / "packages" / pkg / "DEBIAN" / "control").read_text()
            self.assertIn(f"Package: {pkg}\n", text)
            self.assertIn("Version: @VERSION@", text)
            for dep in re.findall(r"\(= ([^)]+)\)", text):
                self.assertEqual(dep, "@VERSION@")
        self.assertTrue(v)

    def test_profile_env_targets_trixie_uefi_amd64(self):
        env = (ROOT / "build/profiles/default.env").read_text()
        self.assertIn("AEGIS_DEBIAN_SUITE=trixie", env)
        self.assertIn("AEGIS_BOOTLOADERS=grub-efi", env)
        self.assertIn("AEGIS_ARCH=amd64", env)
        self.assertNotIn("non-free ", env.replace("non-free-firmware", ""))  # plain non-free is not enabled

    def test_lb_config_uses_only_verified_option_names(self):
        text = (ROOT / "build/config/auto/config").read_text()
        used = set(re.findall(r"--([a-z-]+)", text))
        verified = {"distribution", "architectures", "binary-images", "bootloaders", "archive-areas",
                    "debian-installer", "firmware-binary", "bootappend-live", "iso-application", "iso-publisher", "iso-volume"}
        self.assertEqual(used - verified, set())
        self.assertIn("iso-hybrid", text)

    def test_installer_firmware_pool_is_off_to_stay_under_github_asset_limit(self):
        self.assertIn("AEGIS_FIRMWARE_BINARY=false", (ROOT / "build/profiles/default.env").read_text())
        self.assertIn('--firmware-binary "${AEGIS_FIRMWARE_BINARY}"', (ROOT / "build/config/auto/config").read_text())

    def test_package_lists_are_plain_names(self):
        for f in (ROOT / "build/config/package-lists").glob("*.list.chroot"):
            for line in f.read_text().splitlines():
                if line.strip() and not line.startswith("#"):
                    self.assertRegex(line.strip(), r"^[a-z0-9][a-z0-9.+-]+$", f"{f.name}: {line}")

    def test_xml_configs_well_formed(self):
        files = [*ROOT.glob("build/config/includes.chroot/**/*.xml"), *ROOT.glob("build/config/includes.chroot/**/*.menu")]
        self.assertGreaterEqual(len(files), 4)
        for f in files:
            minidom.parse(str(f))

    def test_menu_has_all_categories_with_directory_files(self):
        menu = (ROOT / "build/config/includes.chroot/etc/xdg/menus/applications-merged/aegis.menu").read_text()
        dirs = list((ROOT / "build/config/includes.chroot/usr/share/desktop-directories").glob("*.directory"))
        self.assertEqual(menu.count("<Directory>"), 13)
        self.assertEqual(len(dirs), 13)

    def test_desktop_entries_parse_and_have_required_keys(self):
        files = list((ROOT / "configs/desktop").glob("*/*.desktop"))
        self.assertGreaterEqual(len(files), 4)
        for f in files:
            cp = configparser.ConfigParser(interpolation=None)
            cp.optionxform = str
            cp.read(f)
            e = cp["Desktop Entry"]
            self.assertEqual(e["Type"], "Application")
            self.assertTrue(e["Name"] and e["Exec"])

    def test_branding_assets_are_valid_svg(self):
        for f in (ROOT / "assets/branding/logo.svg", ROOT / "assets/wallpapers/aegis-dark.svg"):
            doc = minidom.parse(str(f))
            self.assertEqual(doc.documentElement.tagName, "svg")

    def test_wallpaper_path_matches_branding_package_install_path(self):
        xml = (ROOT / "build/config/includes.chroot/etc/skel/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml").read_text()
        self.assertIn("/usr/share/backgrounds/aegisos/aegis-dark.svg", xml)
        self.assertIn("backgrounds/aegisos/aegis-dark.svg", (ROOT / "scripts/build-debs.sh").read_text())

    def test_no_stray_brace_directories_and_no_secrets_files(self):
        for p in ROOT.rglob("*"):
            if ".git" in p.parts:
                continue
            self.assertNotIn("{", p.name, str(p))
            self.assertNotIn(p.suffix, {".pem", ".key", ".iso"}, str(p))

    def test_gitignore_blocks_artifacts(self):
        g = (ROOT / ".gitignore").read_text()
        for pat in ("dist/", "*.iso", ".env", "*.key"):
            self.assertIn(pat, g)

    def test_hooks_live_in_live_or_normal_subdirectory(self):
        # Debian Live Manual: hooks must be in config/hooks/live or config/hooks/normal; files placed
        # directly in config/hooks/ are not run by current live-build (this bit us once: os-release hook ignored).
        hooks = ROOT / "build/config/hooks"
        self.assertEqual([p.name for p in hooks.iterdir() if p.is_file()], [])
        found = [*hooks.glob("live/*.hook.chroot"), *hooks.glob("normal/*.hook.chroot")]
        self.assertTrue(found)

    def test_xfce_wallpaper_covers_known_monitor_names_in_skel_and_system_defaults(self):
        for base in ("etc/skel/.config", "etc/xdg"):
            xml = (ROOT / "build/config/includes.chroot" / base / "xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml")
            doc = minidom.parse(str(xml))
            names = {p.getAttribute("name") for p in doc.getElementsByTagName("property")}
            for m in ("monitor0", "monitor1", "monitorVirtual-1", "monitorVirtual1"):
                self.assertIn(m, names, f"{base}: {m}")
            values = [p.getAttribute("value") for p in doc.getElementsByTagName("property") if p.getAttribute("name") == "last-image"]
            self.assertEqual(set(values), {"/usr/share/backgrounds/aegisos/aegis-dark.svg"})
            self.assertEqual(len(values), 8)

    def test_workflows_use_node24_action_majors_and_pinned_runner(self):
        for wf in (ROOT / ".github/workflows").glob("*.yml"):
            t = wf.read_text()
            self.assertNotIn("actions/checkout@v4", t)
            self.assertNotIn("actions/upload-artifact@v4", t)
            self.assertNotIn("ubuntu-latest", t)

    def test_security_hardening_not_applied_by_any_config(self):
        self.assertFalse(list((ROOT / "build/config/includes.chroot").rglob("*sysctl*")))


if __name__ == "__main__":
    unittest.main()


class Website(unittest.TestCase):
    def test_website_files(self):
        import json
        html = (ROOT / "website/index.html").read_text()
        self.assertIn("<title>AegisOS", html)
        self.assertIn("https://github.com/slimecoding2025/AegisOS/releases", html)
        self.assertNotRegex(html, r"<script[^>]+src=")           # no third-party scripts
        self.assertNotIn("cdn.", html)
        json.loads((ROOT / "website/vercel.json").read_text())

    def test_release_workflow_guards(self):
        wf = (ROOT / ".github/workflows/release.yml").read_text()
        self.assertIn("2147483648", wf)
        self.assertIn("--prerelease", wf)
        self.assertIn("vars.AEGIS_PUBLISH_RELEASES == 'true'", wf)

    def test_image_home_url_is_the_real_repository(self):
        hook = (ROOT / "build/config/hooks/live/0100-aegis-os-release.hook.chroot").read_text()
        self.assertIn("github.com/slimecoding2025/AegisOS", hook)

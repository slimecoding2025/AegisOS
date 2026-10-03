import contextlib
import http.client
import io
import json
import threading
import unittest
from http.server import ThreadingHTTPServer

from aegis import __version__, cli, net_cli, security_center
from tests import ROOT


def run(mod, argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            rc = mod.main(argv)
        except SystemExit as e:
            rc = e.code
    return rc, out.getvalue(), err.getvalue()


class CLI(unittest.TestCase):
    def test_version_matches_version_file(self):
        rc, out, _ = run(cli, ["version"])
        self.assertEqual(rc, 0)
        self.assertEqual(out.strip(), f"aegis {(ROOT / 'VERSION').read_text().strip()}")
        self.assertEqual(__version__, (ROOT / "VERSION").read_text().strip())

    def test_search_info_list_category(self):
        rc, out, _ = run(cli, ["search", "nmap"])
        self.assertEqual(rc, 0)
        self.assertIn("nmap", out)
        rc, out, _ = run(cli, ["info", "nmap", "--json"])
        info = json.loads(out.split("\n\nNOTICE")[0])
        self.assertEqual((info["name"], info["license"]), ("nmap", "unverified"))
        self.assertIn(info["availability"], ("ONLINE AVAILABLE", "OFFLINE AVAILABLE", "REQUIRES INTERNET"))
        rc, out, _ = run(cli, ["category", "forensics"])
        self.assertIn("sleuthkit", out)
        rc, out, _ = run(cli, ["list"])
        self.assertIn("138 tool(s)", out)

    def test_unknown_tool_and_profile_fail(self):
        self.assertEqual(run(cli, ["info", "no-such-tool"])[0], 1)
        self.assertEqual(run(cli, ["install", "no-such-tool", "--dry-run"])[0], 1)
        self.assertEqual(run(cli, ["profile", "nope"])[0], 1)
        self.assertEqual(run(cli, ["search", "zzzzqqqq"])[0], 1)

    def test_profile_list_has_all_profiles(self):
        rc, out, _ = run(cli, ["profile"])
        self.assertEqual(rc, 0)
        for p in ("network", "web", "blue-team", "malware-analysis", "containers", "development"):
            self.assertIn(p, out)

    def test_install_external_tool_dry_run_never_calls_apt(self):
        rc, out, _ = run(cli, ["install", "rustscan", "--dry-run"])
        self.assertEqual(rc, 0)
        self.assertIn("not automated", out)
        self.assertNotIn("dry run: apt-get", out)

    def test_install_prints_authorized_use_notice(self):
        _, out, _ = run(cli, ["install", "sqlmap", "--dry-run"])
        self.assertIn("NOTICE", out)

    def test_remove_dry_run_warns_about_shared_package(self):
        rc, out, _ = run(cli, ["remove", "dig", "--dry-run"])
        self.assertEqual(rc, 0)
        self.assertIn("also provides: nslookup", out)

    def test_noninteractive_without_yes_refuses(self):
        rc, _, err = run(cli, ["upgrade"])
        # stdin is not a TTY under test: must refuse (or abort earlier on repo validation), never proceed
        self.assertEqual(rc, 1)

    def test_manifest_validate_and_package_list(self):
        rc, out, _ = run(cli, ["manifest", "validate"])
        self.assertEqual(rc, 0)
        self.assertIn("0 error(s)", out)
        rc, out, _ = run(cli, ["manifest", "package-list", "--tier", "core"])
        self.assertIn("nmap", out.split())
        self.assertEqual(run(cli, ["manifest", "package-list", "--tier", "bogus"])[0], 1)

    def test_hardening_audit_and_dry_run_apply(self):
        rc, out, _ = run(cli, ["hardening", "audit"])
        self.assertEqual(rc, 0)
        self.assertIn("kernel.kptr_restrict", out)
        rc, out, _ = run(cli, ["hardening", "apply", "--dry-run"])
        self.assertEqual(rc, 0)
        self.assertIn("net.ipv4.tcp_syncookies = 1", out)

    def test_doctor_json_and_exit_code(self):
        rc, out, _ = run(cli, ["doctor", "--json"])
        data = json.loads(out)
        self.assertIn(rc, (0, 1, 2))
        names = {d["name"] for d in data}
        for n in ("os", "kernel", "package-manager", "repositories", "dns", "connectivity", "disk",
                  "time-sync", "dependencies", "aegis-components", "manifest", "configuration", "broken-packages"):
            self.assertIn(n, names)

    def test_banner_and_welcome(self):
        _, out, _ = run(cli, ["banner"])
        self.assertIn("Defend. Analyze. Understand.", out)
        self.assertIn(__version__, out)

    def test_net_cli_commands(self):
        for cmd in ("interfaces", "routes", "dns", "connections", "listening", "info"):
            rc, out, _ = run(net_cli, [cmd])
            self.assertEqual(rc, 0, cmd)
        rc, out, _ = run(net_cli, ["--json", "interfaces"])
        self.assertIn("lo", [i["name"] for i in json.loads(out)])


class SecurityCenter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        holder = {}
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), security_center.make_handler(lambda: holder["port"]))
        holder["port"] = cls.port = cls.httpd.server_address[1]
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def request(self, method, path, host=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
        c.putrequest(method, path, skip_host=True)
        c.putheader("Host", host or f"127.0.0.1:{self.port}")
        c.putheader("Content-Length", "0")
        c.endheaders()
        r = c.getresponse()
        return r.status, r.read(), dict(r.getheaders())

    def test_collect_has_real_values(self):
        d = security_center.collect()
        for k in ("aegis_version", "kernel", "cpu", "memory", "disks", "network", "firewall", "security_updates",
                  "services", "listening_ports", "health", "hardening", "aegis_tools"):
            self.assertIn(k, d)
        self.assertEqual(d["aegis_version"], __version__)
        self.assertGreater(d["memory"]["total_bytes"], 0)
        self.assertIn("lo", [i["name"] for i in d["network"]["interfaces"]])

    def test_text_render(self):
        text = security_center.render_text(security_center.collect())
        for label in ("Kernel", "Memory", "Firewall", "Listening", "Hardening"):
            self.assertIn(label, text)

    def test_http_status_endpoint(self):
        status, body, headers = self.request("GET", "/api/status")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["aegis_version"], __version__)
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")

    def test_http_index(self):
        status, body, _ = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"Aegis Security Center", body)

    def test_rejects_foreign_host_header(self):
        self.assertEqual(self.request("GET", "/api/status", host="evil.example")[0], 403)

    def test_read_only(self):
        self.assertEqual(self.request("POST", "/api/status")[0], 405)
        self.assertEqual(self.request("GET", "/nope")[0], 404)


if __name__ == "__main__":
    unittest.main()

import tempfile
import types
import unittest
from pathlib import Path

from aegis import desktop

XRANDR = """Screen 0: minimum 16 x 16, current 1920 x 1080, maximum 16384 x 16384
Virtual1 connected primary 1920x1080+0+0 (normal left inverted right x axis y axis) 0mm x 0mm
   1920x1080     60.00*+
Virtual2 disconnected (normal left inverted right x axis y axis)
HDMI-1 connected 1280x720+1920+0 (normal left inverted right x axis y axis) 600mm x 340mm
bad;name connected 10x10+0+0
"""


def fake_runner(log, xrandr_out=XRANDR, fail_on=None):
    def run(cmd, timeout=60):
        log.append(cmd)
        if cmd[0] == "xrandr":
            return types.SimpleNamespace(returncode=0, stdout=xrandr_out, stderr="")
        rc = 1 if fail_on and fail_on in cmd[4] else 0
        return types.SimpleNamespace(returncode=rc, stdout="", stderr="")
    return run


class Desktop(unittest.TestCase):
    def test_connected_outputs_only_connected_and_safe_names(self):
        self.assertEqual(desktop.connected_outputs(XRANDR), ["Virtual1", "HDMI-1"])

    def test_monitor_keys_include_monitor0_and_names(self):
        self.assertEqual(desktop.monitor_keys(["Virtual1", "HDMI-1", "Virtual1"]),
                         ["monitor0", "monitorVirtual1", "monitorHDMI-1"])

    def test_commands_are_argument_lists_with_expected_paths(self):
        cmds = desktop.commands(["monitorVirtual1"])
        self.assertEqual(cmds[0][4], "/backdrop/screen0/monitorVirtual1/workspace0/last-image")
        self.assertEqual(cmds[0][-1], desktop.WALLPAPER)
        self.assertTrue(all(isinstance(a, str) for c in cmds for a in c))

    def test_apply_runs_commands_and_writes_marker_once(self):
        with tempfile.TemporaryDirectory() as d:
            marker = Path(d, "m")
            log = []
            res = desktop.apply_wallpaper(runner=fake_runner(log), marker=marker, have=lambda c: True)
            self.assertEqual(res["status"], "ok")
            self.assertTrue(marker.exists())
            self.assertIn("monitorVirtual1", " ".join(" ".join(c) for c in log))
            n = len(log)
            res2 = desktop.apply_wallpaper(runner=fake_runner(log), marker=marker, have=lambda c: True)
            self.assertEqual(res2["status"], "skipped")
            self.assertEqual(len(log), n)  # user's later choice is not overwritten
            res3 = desktop.apply_wallpaper(runner=fake_runner(log), marker=marker, have=lambda c: True, force=True)
            self.assertEqual(res3["status"], "ok")

    def test_failure_does_not_write_marker(self):
        with tempfile.TemporaryDirectory() as d:
            marker = Path(d, "m")
            res = desktop.apply_wallpaper(runner=fake_runner([], fail_on="monitor0"), marker=marker, have=lambda c: True)
            self.assertEqual(res["status"], "partial")
            self.assertFalse(marker.exists())

    def test_without_xfconf_nothing_happens(self):
        with tempfile.TemporaryDirectory() as d:
            res = desktop.apply_wallpaper(marker=Path(d, "m"), have=lambda c: False)
            self.assertEqual(res["status"], "unavailable")

    def test_without_xrandr_falls_back_to_monitor0(self):
        with tempfile.TemporaryDirectory() as d:
            res = desktop.apply_wallpaper(runner=fake_runner([]), marker=Path(d, "m"), dry_run=True,
                                          have=lambda c: c == "xfconf-query")
            self.assertEqual(res["outputs"], [])
            self.assertEqual(res["commands"][0][4], "/backdrop/screen0/monitor0/workspace0/last-image")


if __name__ == "__main__":
    unittest.main()

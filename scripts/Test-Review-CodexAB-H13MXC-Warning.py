#!/usr/bin/env python3
"""Offline-only tests for private, nonpersisted local MXC stderr review."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
from unittest import mock
import unittest

SRC = Path(__file__).with_name("Review-CodexAB-H13MXC-Warning.py")
SPEC = importlib.util.spec_from_file_location("h13_private_review", SRC)
p = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p)


class H13PrivateReviewTests(unittest.TestCase):
    def test_default_does_not_launch_or_review(self):
        with mock.patch.object(p, "run_single_review", side_effect=AssertionError("runtime")):
            capture = io.StringIO()
            with contextlib.redirect_stdout(capture):
                self.assertEqual(p.main([]), 0)
        j = json.loads(capture.getvalue())
        self.assertEqual(j["mode"], "PLAN_ONLY_NO_PROCESS")
        self.assertTrue(j["exact_stderr_visible_only_in_private_local_dialog"])
        self.assertFalse(j["raw_stderr_printed_to_terminal"])
        self.assertFalse(j["raw_stderr_written_to_disk"])
        self.assertFalse(j["actual_native_mxc_invoked"])

    def test_warning_opens_exactly_one_local_review_but_never_passes(self):
        shown = []
        j = p.inspect_result(b"MXC_OK\r\n", b"warning: PRIVATE_PATH", 0,
                             display=shown.append)
        self.assertEqual(shown, ["warning: PRIVATE_PATH"])
        self.assertEqual(j["status"], "LOCAL_WARNING_REVIEWED_STILL_STOP")
        self.assertEqual(j["stderr_category"], "GENERAL_WARNING")
        self.assertEqual(j["stdout_marker"], "MARKER_PRESENT")
        self.assertEqual(j["child_exit_class"], "EXIT_ZERO")
        self.assertFalse(j["raw_stderr_shared_or_persisted"])
        self.assertFalse(j["native_filesystem_enforcement_verified"])
        self.assertEqual(j["model_calls_made"], 0)
        self.assertNotIn("PRIVATE_PATH", json.dumps(j))

    def test_security_warning_unchanged(self):
        shown = []
        j = p.inspect_result(b"MXC_OK\n", b"warning: world writable PRIVATE", 0,
                             display=shown.append)
        self.assertEqual(j["stderr_category"], "SECURITY_WARNING")
        self.assertEqual(j["status"], "LOCAL_WARNING_REVIEWED_STILL_STOP")
        self.assertEqual(len(shown), 1)

    def test_no_stderr_reuses_strict_echo_gate(self):
        used = []
        j = p.inspect_result(b"MXC_OK\r\n", b"", 0, display=used.append)
        self.assertEqual(used, [])
        self.assertEqual(j["status"], "MXC_COMPAT_ECHO_PASS_NO_WARNING_NOT_ENFORCEMENT")
        self.assertFalse(j["native_filesystem_enforcement_verified"])
        with self.assertRaisesRegex(p.core.ProbeError, "COMPAT_EXIT_NONZERO"):
            p.inspect_result(b"MXC_OK\r\n", b"", 1, display=used.append)

    def test_invalid_or_oversized_capture_fails_before_gui(self):
        shown = []
        for bad in (None, "PRIVATE", b"x" * (p.core.MAX_CAPTURE + 1)):
            with self.subTest(type=type(bad).__name__):
                with self.assertRaises(p.ReviewError):
                    p.inspect_result(b"MXC_OK", bad, 0, display=shown.append)
        with self.assertRaises(p.core.ProbeError):
            p.inspect_result(b"x" * (p.core.MAX_CAPTURE + 1),
                             b"warning: PRIVATE", 0, display=shown.append)
        self.assertEqual(shown, [])

    def test_actual_mode_runs_one_sandbox_and_no_filesystem_canary(self):
        stdout, stderr, rc = b"MXC_OK\r\n", b"warning: PRIVATE", 0
        with mock.patch.object(p.core, "require_pinned_nonadmin_windows"):
            with mock.patch.object(p.core, "mxc_env_for_isolated_home",
                                   return_value={"CODEX_HOME": "SYNTHETIC",
                                                 "SystemDrive": "C:"}):
                with mock.patch.object(p.core, "run_subprocess",
                                       return_value=(stdout, stderr, rc)) as call:
                    with mock.patch.object(p, "show_only_on_local_screen",
                                           side_effect=AssertionError("DISPLAY_CALL")):
                        # inspect_result has captured its default display at function
                        # definition time, so replace the dialog using a wrapper.
                        original_inspect = p.inspect_result
                        def audited(out, err, code):
                            return original_inspect(out, err, code, display=lambda _: None)
                        with mock.patch.object(p, "inspect_result", side_effect=audited):
                            j = p.run_single_review()
        self.assertEqual(call.call_count, 1)
        self.assertEqual(call.call_args.args[0],
                         p.core.compatibility_command(p.core.h1.CLI))
        self.assertEqual(j["status"], "LOCAL_WARNING_REVIEWED_STILL_STOP")
        self.assertTrue(j["temporary_profile_and_workspace_removed"])

    def test_private_dialog_mock_never_uses_network_or_disk(self):
        with mock.patch.object(p.ctypes, "windll", create=True) as fake:
            fake.user32.MessageBoxW.return_value = 1
            p.show_only_on_local_screen("PRIVATE_ONLY_ON_SCREEN")
            self.assertEqual(fake.user32.MessageBoxW.call_count, 1)
            args = fake.user32.MessageBoxW.call_args.args
            self.assertIn("PRIVATE_ONLY_ON_SCREEN", args[1])
            self.assertIn("DO NOT COPY", args[2])

    def test_failed_dialog_is_fixed_stop(self):
        with mock.patch.object(p.ctypes, "windll", create=True) as fake:
            fake.user32.MessageBoxW.return_value = 0
            with self.assertRaisesRegex(p.ReviewError, "LOCAL_DIALOG_UNAVAILABLE"):
                p.show_only_on_local_screen("PRIVATE")

    def test_cli_never_publishes_raw_warning(self):
        fake = {
            "contract": p.CONTRACT, "status": "LOCAL_WARNING_REVIEWED_STILL_STOP",
            "stderr_category": "GENERAL_WARNING", "model_calls_made": 0,
        }
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(p, "run_single_review", return_value=fake):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                self.assertEqual(p.main(["--execute-one-private-local-review"]), 2)
        self.assertNotIn("PRIVATE", stdout.getvalue() + stderr.getvalue())
        self.assertIn("STOP: H13_NATIVE_WARNING_REQUIRES_OPERATOR_REVIEW", stderr.getvalue())

    def test_unrecognized_exception_never_leaks(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(p, "run_single_review",
                               side_effect=OSError("C:\\PRIVATE\\TOKEN")):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                self.assertEqual(p.main(["--execute-one-private-local-review"]), 2)
        self.assertEqual(stderr.getvalue().strip(),
                         "STOP: H13_PRIVATE_WARNING_REVIEW_FAILED:OTHER_LOCAL_FAILURE")

    def test_file_source_has_no_raw_warning_logging(self):
        source = SRC.read_text(encoding="utf-8")
        self.assertNotIn("logging.", source)
        self.assertNotIn("write_bytes(stderr)", source)
        self.assertNotIn("print(stderr)", source)
        self.assertNotIn("stderr.hex", source)
        self.assertNotIn("turn/start", p.plan().get("mode"))
        self.assertIn("MessageBoxW", source)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Offline safety/contract tests for opt-in H1.3a standalone MXC probe."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest import mock

SRC = Path(__file__).with_name("Probe-CodexAB-H13MXC.py")
SPEC = importlib.util.spec_from_file_location("p11_h13_real", SRC)
p = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p)


class H13StandaloneTests(unittest.TestCase):
    def sample(self):
        return (p.MARKER + '{"inside_ok":true,"outside_denied":true}').encode(), b"", 0, True, True

    def test_default_no_process(self):
        a = p.plan()
        self.assertEqual(a["mode"], "PLAN_ONLY_NO_PROCESS")
        self.assertFalse(a["standalone_mxc_runtime_verified"])
        self.assertFalse(a["appserver_turn_mxc_verified"])
        self.assertEqual(a["model_calls_made"], 0)
        self.assertEqual(p.main([]), 0)

    def test_flags_request_mxc_and_workspace_write_explicitly(self):
        command = p.command_for("PINNED", "PY", "CHILD")
        self.assertEqual(command, [
            "PINNED", "-c", 'windows.sandbox="mxc"',
            "-c", 'sandbox_mode="workspace-write"',
            "sandbox", "PY", "-B", "CHILD",
        ])
        self.assertNotIn("exec", command)
        self.assertNotIn("turn/start", command)
        self.assertNotIn("setup", command)
        self.assertNotIn("uninstall", command)

    def test_synthetic_good_evidence_not_appserver(self):
        r = p.evaluate(*self.sample())
        self.assertEqual(r["status"], "STANDALONE_MXC_FILESYSTEM_NEGATIVE_PASS_NOT_APPSERVER")
        self.assertFalse(r["appserver_turn_mxc_verified"])
        self.assertFalse(r["network_isolation_verified"])
        self.assertFalse(r["child_tree_cleanup_attested"])
        self.assertFalse(r["candidate_merge_authorized"])
        self.assertEqual(r["model_calls_made"], 0)

    def test_outside_allow_is_stop(self):
        sample = (p.MARKER + '{"inside_ok":true,"outside_denied":false}').encode()
        with self.assertRaisesRegex(p.ProbeError, "SANDBOX_OUTSIDE_WRITE_NOT_DENIED"):
            p.evaluate(sample, b"", 3, True, False)

    def test_inside_failure_is_stop(self):
        sample = (p.MARKER + '{"inside_ok":false,"outside_denied":true}').encode()
        with self.assertRaisesRegex(p.ProbeError, "SANDBOX_INSIDE_WRITE_FAILED"):
            p.evaluate(sample, b"", 3, False, True)

    def test_parent_did_not_verify_inside_is_stop(self):
        o, e, rc, _, _ = self.sample()
        with self.assertRaisesRegex(p.ProbeError, "SANDBOX_INSIDE_WRITE_FAILED"):
            p.evaluate(o, e, rc, False, True)

    def test_parent_detects_outside_change(self):
        o, e, rc, _, _ = self.sample()
        with self.assertRaisesRegex(p.ProbeError, "SANDBOX_OUTSIDE_FILE_CHANGED"):
            p.evaluate(o, e, rc, True, False)

    def test_child_nonzero_is_stop(self):
        o, e, rc, a, b = self.sample()
        with self.assertRaisesRegex(p.ProbeError, "SANDBOX_CHILD_FAILED"):
            p.evaluate(o, e, 3, a, b)

    def test_any_stderr_is_stop_no_waiver_for_warning(self):
        o, _, rc, a, b = self.sample()
        with self.assertRaisesRegex(p.ProbeError, "SANDBOX_STDERR_PRESENT"):
            p.evaluate(o, b"PRIVATE_WARNING_PATH", rc, a, b)

    def test_disallow_unknown_json_keys_and_types(self):
        cases = [
            b'{"inside_ok":true,"outside_denied":true,"path":"PRIVATE"}',
            b'{"inside_ok":1,"outside_denied":true}',
            b'{"inside_ok":true,"outside_denied":"true"}',
            b'{"inside_ok":true}',
            b'[]', b"PRIVATE_PATH", b"",
        ]
        for c in cases:
            with self.subTest(c=c):
                with self.assertRaises(p.ProbeError):
                    p.evaluate((p.MARKER.encode() + c), b"", 0, True, True)

    def test_disallow_extra_stdout_or_large_capture(self):
        valid = self.sample()[0]
        for c in (valid + b"\nPRIVATE_EXTRA", b"PRIVATE\n" + valid,
                  b"X" * (p.MAX_CAPTURE + 1)):
            with self.subTest(length=len(c)):
                with self.assertRaisesRegex(p.ProbeError, "SANDBOX_STDOUT_INVALID"):
                    p.evaluate(c, b"", 0, True, True)

    def test_diagnostics_are_fixed_no_secrets(self):
        self.assertEqual(p.safe_reason(p.ProbeError("SANDBOX_STDERR_PRESENT")),
                         "SANDBOX_STDERR_PRESENT")
        for err in (p.ProbeError("PRIVATE_TOKEN"), OSError("C:\\Users\\PRIVATE")):
            self.assertEqual(p.safe_reason(err), "OTHER_LOCAL_FAILURE")

    def test_local_win_checks_before_any_file_or_process(self):
        if p.os.name != "nt":
            with self.assertRaisesRegex(p.ProbeError, "WINDOWS_ONLY"):
                p.run_local()

    def test_no_network_model_or_existing_profile_access(self):
        source = SRC.read_text(encoding="utf-8")
        self.assertNotIn('"method": "turn/start"', source)
        self.assertNotIn('"method": "thread/start"', source)
        self.assertNotIn("danger-full-access", source)
        self.assertNotIn("requests.", source)
        self.assertIn("h1.env_for_isolated_home", source)
        self.assertIn("tempfile.TemporaryDirectory", source)

    def test_child_script_has_both_controls(self):
        self.assertIn("workspace-positive.canary", p.CHILD_CODE)
        self.assertIn("outside-negative.canary", p.CHILD_CODE)
        self.assertIn("outside_denied", p.CHILD_CODE)
        self.assertNotIn("socket", p.CHILD_CODE)

    def test_cli_redacted_failure(self):
        capture = io.StringIO()
        with mock.patch.object(p, "run_local", side_effect=p.ProbeError("SANDBOX_STDERR_PRESENT")):
            with contextlib.redirect_stderr(capture):
                self.assertEqual(p.main(["--execute-local-mxc-probe"]), 2)
        self.assertEqual(capture.getvalue().strip(),
                         "STOP: H13_STANDALONE_MXC_FAILED:SANDBOX_STDERR_PRESENT")

    def test_error_codes_include_no_user_paths(self):
        for name in p.CODES:
            self.assertNotIn("\\", name)
            self.assertNotIn("/", name)


if __name__ == "__main__":
    unittest.main()

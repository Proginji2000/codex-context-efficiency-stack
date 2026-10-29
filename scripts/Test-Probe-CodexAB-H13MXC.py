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
            "PINNED", "-c", "windows.sandbox=mxc",
            "sandbox", "--include-managed-config",
            "--permission-profile", ":workspace", "--",
            "PY", "-B", "CHILD",
        ])
        self.assertEqual(p.compatibility_command("PINNED"), [
            "PINNED", "-c", "windows.sandbox=mxc",
            "sandbox", "--include-managed-config",
            "--permission-profile", ":workspace", "--",
            "cmd.exe", "/d", "/c", "echo", "MXC_OK",
        ])
        self.assertNotIn("exec", command)
        self.assertNotIn("turn/start", command)
        self.assertNotIn("setup", command)
        self.assertNotIn("uninstall", command)

    def test_documented_compatibility_gate_only_accepts_exact_echo(self):
        self.assertTrue(p.evaluate_compatibility(b"MXC_OK\r\n", b"", 0))
        self.assertTrue(p.evaluate_compatibility(b"MXC_OK\n", b"", 0))
        for value in (b"", b"MXC_NOT_OK", b"MXC_OK\nPRIVATE",
                      b"PRIVATE\nMXC_OK"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(p.ProbeError, "COMPAT_STDOUT_INVALID"):
                    p.evaluate_compatibility(value, b"", 0)

    def test_compatibility_nonzero_exit_blocks_child_probe(self):
        with self.assertRaisesRegex(p.ProbeError, "COMPAT_EXIT_NONZERO"):
            p.evaluate_compatibility(b"", b"", 1)

    def test_compatibility_stderr_warning_always_stops(self):
        cases = (
            (b"WARNING: PRIVATE", "GENERAL_WARNING"),
            (b"windows sandbox failed: PRIVATE", "BACKEND_LAUNCH_ERROR"),
            (b"warning: world writable PRIVATE", "SECURITY_WARNING"),
        )
        for raw, category in cases:
            with self.subTest(category=category):
                with self.assertRaises(p.ProbeError) as captured:
                    p.evaluate_compatibility(b"", raw, 1)
                exported = p.safe_reason(captured.exception)
                self.assertEqual(exported,
                    "COMPAT_STDERR_PRESENT:" + category + ":MARKER_ABSENT:EXIT_NONZERO")
                self.assertNotIn("PRIVATE", exported)

    def test_compatibility_success_output_cannot_override_stderr(self):
        with self.assertRaises(p.ProbeError) as captured:
            p.evaluate_compatibility(b"MXC_OK\n", b"WARNING: PRIVATE", 0)
        self.assertEqual(p.safe_reason(captured.exception),
                         "COMPAT_STDERR_PRESENT:GENERAL_WARNING:MARKER_PRESENT:EXIT_ZERO")

    def test_compatibility_rejects_invalid_capture_types_and_size(self):
        for val in (None, "MXC_OK", b"X" * (p.MAX_CAPTURE + 1)):
            with self.subTest(value_type=type(val).__name__):
                with self.assertRaisesRegex(p.ProbeError, "COMPAT_STDOUT_INVALID"):
                    p.evaluate_compatibility(val, b"", 0)
        for val in (None, "WARN", b"X" * (p.MAX_CAPTURE + 1)):
            with self.subTest(stderr_type=type(val).__name__):
                with self.assertRaisesRegex(p.ProbeError, "COMPAT_STDOUT_INVALID"):
                    p.evaluate_compatibility(b"MXC_OK", val, 0)

    def test_compatibility_has_no_model_and_explicit_profile(self):
        cmd = p.compatibility_command("PINNED")
        self.assertIn(":workspace", cmd)
        self.assertNotIn("sandbox_mode", " ".join(cmd))
        self.assertNotIn("danger-full-access", " ".join(cmd))
        self.assertNotIn("exec", cmd)
        self.assertNotIn("turn/start", cmd)

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
        with self.assertRaises(p.ProbeError) as caught:
            p.evaluate(o, b"PRIVATE_WARNING_PATH", rc, a, b)
        self.assertEqual(
            p.safe_reason(caught.exception),
            "SANDBOX_STDERR_PRESENT:UNRECOGNIZED_STDERR:MARKER_PRESENT:EXIT_ZERO",
        )

    def test_categorized_stderr_never_leaks_contents(self):
        cases = (
            (b"windows sandbox failed: C:\\PRIVATE\\secret", "BACKEND_LAUNCH_ERROR"),
            (b"windows sandbox failed to build runtime: PRIVATE", "BACKEND_LAUNCH_ERROR"),
            (b"warning: world writable C:\\PRIVATE", "SECURITY_WARNING"),
            (b"error: unexpected argument '--PRIVATE'", "CLI_USAGE_ERROR"),
            (b"Usage: codex sandbox PRIVATE", "CLI_USAGE_ERROR"),
            (b"failed to parse config C:\\PRIVATE", "CONFIG_ERROR"),
            (b"Traceback (most recent call last): PRIVATE", "CHILD_PYTHON_ERROR"),
            (b"warning: PRIVATE", "GENERAL_WARNING"),
            (b"SecretToken PRIVATE", "UNRECOGNIZED_STDERR"),
        )
        out, _, _, _, _ = self.sample()
        for raw, category in cases:
            with self.subTest(category=category):
                with self.assertRaises(p.ProbeError) as caught:
                    p.evaluate(out, raw, 1, True, True)
                exported = p.safe_reason(caught.exception)
                self.assertEqual(
                    exported,
                    "SANDBOX_STDERR_PRESENT:" + category +
                    ":MARKER_PRESENT:EXIT_NONZERO",
                )
                self.assertNotIn("PRIVATE", exported)
                self.assertNotIn("\\", exported)
                self.assertNotIn("SecretToken", exported)
                self.assertNotIn("--", exported)

    def test_marker_and_return_code_flags_when_child_did_not_run(self):
        with self.assertRaises(p.ProbeError) as caught:
            p.evaluate(b"", b"windows sandbox failed: PRIVATE", 1, False, True)
        self.assertEqual(p.safe_reason(caught.exception),
                         "SANDBOX_STDERR_PRESENT:BACKEND_LAUNCH_ERROR:"
                         "MARKER_ABSENT:EXIT_NONZERO")

    def test_categorized_stderr_must_always_fail_even_with_successful_child(self):
        out, _, rc, a, b = self.sample()
        with self.assertRaises(p.ProbeError) as caught:
            p.evaluate(out, b"warning: PRIVATE", rc, a, b)
        self.assertIn("GENERAL_WARNING", p.safe_reason(caught.exception))

    def test_error_detail_injection_is_redacted(self):
        for data in (
            p.ProbeError("SANDBOX_STDERR_PRESENT", "PRIVATE",
                         "MARKER_PRESENT", "EXIT_ZERO"),
            p.ProbeError("SANDBOX_STDERR_PRESENT", "CLI_USAGE_ERROR",
                         "PRIVATE_PATH", "EXIT_NONZERO"),
            p.ProbeError("SANDBOX_STDERR_PRESENT", "CLI_USAGE_ERROR",
                         "MARKER_PRESENT", "EXIT_NONZERO", "PRIVATE"),
            p.ProbeError("PRIVATE_TOKEN"),
        ):
            self.assertEqual(p.safe_reason(data), "OTHER_LOCAL_FAILURE")

    def test_capture_size_over_limit_is_still_denied(self):
        out, _, rc, a, b = self.sample()
        with self.assertRaisesRegex(p.ProbeError, "SANDBOX_STDERR_PRESENT"):
            p.evaluate(out, b"warning: PRIVATE" * 2000, rc, a, b)

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
        self.assertNotIn("PRIVATE", capture.getvalue())

    def test_error_codes_include_no_user_paths(self):
        for name in p.CODES:
            self.assertNotIn("\\", name)
            self.assertNotIn("/", name)


if __name__ == "__main__":
    unittest.main()

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

    def test_mxc_windows_24h2_and_25h2_documented_thresholds(self):
        for build in (26100, 26200):
            with self.subTest(build=build):
                self.assertEqual(p.assess_windows_build(build, 9278),
                                 "DOCUMENTED_BUILD_THRESHOLD_MET")
                self.assertEqual(p.assess_windows_build(build, 9277),
                                 "BELOW_DOCUMENTED_MINIMUM")
                self.assertEqual(p.assess_windows_build(build, 9400),
                                 "DOCUMENTED_BUILD_THRESHOLD_MET")

    def test_undocumented_build_does_not_claim_mxc_support(self):
        for build in (22631, 26300, 27000):
            with self.subTest(build=build):
                self.assertEqual(p.assess_windows_build(build, 10000),
                                 "OUTSIDE_DOCUMENTED_BUILD_MATRIX")

    def test_invalid_build_inputs_are_fail_closed(self):
        for build, ubr in ((True, 9278), ("26200", 9278), (26200, "9278"),
                           (-1, 9278), (26200, -2), (None, 9278)):
            with self.subTest(build=build, ubr=ubr):
                with self.assertRaisesRegex(p.ProbeError, "WINDOWS_BUILD_QUERY_FAILED"):
                    p.assess_windows_build(build, ubr)

    def test_read_only_build_report_is_not_an_os_capability_attestation(self):
        r = p.windows_build_report(26200, 9278)
        self.assertEqual(r["mode"], "READ_ONLY_OS_BUILD_CHECK")
        self.assertEqual(r["os_threshold_status"], "DOCUMENTED_BUILD_THRESHOLD_MET")
        self.assertFalse(r["mxc_native_capability_verified"])
        self.assertFalse(r["managed_policy_mxc_allowed_verified"])
        self.assertFalse(r["standalone_mxc_runtime_verified"])
        self.assertFalse(r["appserver_turn_mxc_verified"])
        self.assertEqual(r["processes_launched"], 0)
        self.assertEqual(r["model_calls_made"], 0)

    def test_check_windows_build_cli_never_starts_sandbox(self):
        out = io.StringIO()
        with mock.patch.object(p, "query_windows_build", return_value=(26200, 9278)):
            with mock.patch.object(p, "run_local", side_effect=AssertionError("REAL SANDBOX")):
                with contextlib.redirect_stdout(out):
                    self.assertEqual(p.main(["--check-windows-build"]), 0)
        r = json.loads(out.getvalue())
        self.assertEqual(r["windows_build"], 26200)
        self.assertEqual(r["windows_revision"], 9278)
        self.assertFalse(r["standalone_mxc_runtime_verified"])

    def test_check_windows_build_cannot_combine_with_execution(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as e:
                p.main(["--check-windows-build", "--execute-local-mxc-probe"])
        self.assertEqual(e.exception.code, 2)

    def test_pinned_mxc_launcher_failure_subcategories_are_redacted(self):
        cases = (
            (b"MXC launcher: this Windows build cannot enforce native MXC deny paths",
             "MXC_DENY_PATHS_UNAVAILABLE"),
            (b"MXC launcher: invalid MXC launcher request",
             "MXC_INVALID_LAUNCHER_REQUEST"),
            (b"MXC launcher: MXC requires Unicode environment variable values",
             "MXC_ENV_UNICODE_INVALID"),
            (b"MXC launcher: cannot enumerate Windows volumes: PRIVATE",
             "MXC_WINDOWS_VOLUME_ERROR"),
            (b"MXC launcher: cannot locate required Windows platform directory: HRESULT PRIVATE",
             "MXC_PLATFORM_DIRECTORY_ERROR"),
            (b"MXC launcher: cannot initialize COM: HRESULT PRIVATE",
             "MXC_COM_INIT_ERROR"),
            (b"MXC launcher: cannot locate the Windows directory",
             "MXC_WINDOWS_DIRECTORY_ERROR"),
            (b"MXC launcher: MXC requires an absolute policy working directory",
             "MXC_CWD_INVALID"),
            (b"MXC launcher: MXC native launch does not support permissiveLearningMode",
             "MXC_UNSUPPORTED_POLICY_MODE"),
            (b"MXC launcher: waiting for the MXC command: PRIVATE",
             "MXC_CHILD_WAIT_ERROR"),
            (b"MXC launcher: SDK PRIVATE ERROR MESSAGE",
             "MXC_LAUNCHER_FAILURE"),
        )
        for raw, expected in cases:
            with self.subTest(expected=expected):
                # Warnings elsewhere in stderr must NOT hide native errors.
                raw = b"warning: PRIVATE_NONFATAL\n" + raw
                self.assertEqual(p.classify_stderr(raw), expected)
                with self.assertRaises(p.ProbeError) as caught:
                    p.evaluate_compatibility(b"", raw, 1)
                safe = p.safe_reason(caught.exception)
                self.assertEqual(safe, "COMPAT_STDERR_PRESENT:" + expected +
                                 ":MARKER_ABSENT:EXIT_NONZERO")
                self.assertNotIn("PRIVATE", safe)
                self.assertNotIn("HRESULT", safe)

    def test_systemdrive_was_missing_from_prior_h1_isolated_allowlist(self):
        self.assertNotIn("SYSTEMDRIVE", p.h1.SAFE_ENV)
        source = {
            "SystemDrive": "C:", "LOCALAPPDATA": "PRIVATE_LOCAL",
            "SYSTEMROOT": "PRIVATE_WINDOWS", "PATH": "PRIVATE_PATH",
            "AUTH_SECRET": "PRIVATE_TOKEN",
        }
        child_h1 = p.h1.env_for_isolated_home("PRIVATE_TMP", source)
        self.assertNotIn("SystemDrive", child_h1)
        child = p.mxc_env_for_isolated_home("PRIVATE_TMP", source)
        self.assertEqual(child["SystemDrive"], "C:")
        self.assertEqual(child["CODEX_HOME"], "PRIVATE_TMP")
        self.assertEqual(child["PYTHONDONTWRITEBYTECODE"], "1")
        self.assertEqual(child["LOCALAPPDATA"], "PRIVATE_LOCAL")
        self.assertNotIn("AUTH_SECRET", child)
        self.assertEqual(set(child) - set(child_h1), {"SystemDrive"})

    def test_isolated_systemdrive_accepts_case_variant_and_normalizes_letter(self):
        source = {"systemdrive": "c:", "LOCALAPPDATA": "PRIVATE"}
        child = p.mxc_env_for_isolated_home("PRIVATE_TMP", source)
        self.assertEqual(child["SystemDrive"], "C:")
        self.assertEqual(set(child) - set(p.h1.env_for_isolated_home("PRIVATE_TMP", source)),
                         {"SystemDrive"})

    def test_missing_or_invalid_systemdrive_is_stop_before_launch(self):
        for bad in (None, "", "C:\\\\", "C:\\", "\\\\server", "22", "C", 3,
                    "PRIVATETOKEN"):
            source = {"LOCALAPPDATA": "PRIVATE_LOCAL"}
            if bad is not None:
                source["SystemDrive"] = bad
            with self.subTest(bad=repr(bad)):
                with self.assertRaises(p.ProbeError) as caught:
                    p.mxc_env_for_isolated_home("PRIVATE_TMP", source)
                self.assertIn(p.safe_reason(caught.exception),
                              ("MXC_HOST_ENV_REQUIRED_MISSING",
                               "MXC_HOST_SYSTEMDRIVE_INVALID"))

    def test_missing_localappdata_does_not_fall_back_to_real_profile(self):
        source = {"SystemDrive": "C:", "AUTH_SECRET": "PRIVATE"}
        with self.assertRaisesRegex(
                p.ProbeError, "MXC_HOST_ENV_REQUIRED_MISSING"):
            p.mxc_env_for_isolated_home("PRIVATE_TMP", source)

    def test_env_preflight_reports_validity_without_value(self):
        from types import SimpleNamespace
        env = {"SystemDrive": "C:", "LOCALAPPDATA": "PRIVATE_DIR",
               "SystemRoot": "PRIVATE_ROOT"}
        with mock.patch.object(p, "os", SimpleNamespace(name="nt", environ=env)):
            r = p.host_environment_report()
        self.assertTrue(r["system_drive_present"])
        self.assertTrue(r["system_drive_format_valid"])
        self.assertTrue(r["required_mxc_transport_host_env_present"])
        self.assertNotIn("PRIVATE", json.dumps(r))
        env["SystemDrive"] = "invalid-value"
        with mock.patch.object(p, "os", SimpleNamespace(name="nt", environ=env)):
            r2 = p.host_environment_report()
        self.assertTrue(r2["system_drive_present"])
        self.assertFalse(r2["system_drive_format_valid"])
        self.assertTrue(r2["required_mxc_transport_host_env_present"])

    def test_both_runtime_paths_use_derived_mxc_environment(self):
        source = SRC.read_text(encoding="utf-8")
        self.assertEqual(source.count("env = mxc_env_for_isolated_home(home)"), 2)
        self.assertNotIn("env = h1.env_for_isolated_home(home)", source)
        self.assertNotIn("h1.SAFE_ENV.add", source)
        self.assertNotIn("h1.SAFE_ENV =", source)

    def test_mxc_host_transport_env_presence_case_insensitive(self):
        env = {
            "systemdrive": "C:",
            "LoCaLaPpDaTa": "PRIVATE_PATH",
            "SystemRoot": "PRIVATE_WIN",
        }
        self.assertTrue(p._is_host_env_present("SystemDrive", env))
        self.assertTrue(p._is_host_env_present("LOCALAPPDATA", env))
        self.assertFalse(p._is_host_env_present("MISSING", env))
        for bad in (None, "", 123):
            env["systemdrive"] = bad
            self.assertFalse(p._is_host_env_present("SystemDrive", env))

    def test_mxc_host_env_check_readonly_with_no_process(self):
        from types import SimpleNamespace
        env = {"SystemDrive": "C:", "LOCALAPPDATA": "PRIVATE_PATH",
               "SystemRoot": "PRIVATE_WIN"}
        with mock.patch.object(p, "os", SimpleNamespace(name="nt", environ=env)):
            with mock.patch.object(p, "run_local", side_effect=AssertionError("RUNTIME")):
                with mock.patch.object(p, "run_compatibility_only",
                                       side_effect=AssertionError("RUNTIME")):
                    capture = io.StringIO()
                    with contextlib.redirect_stdout(capture):
                        self.assertEqual(p.main(["--check-mxc-host-environment"]), 0)
        result = json.loads(capture.getvalue())
        self.assertEqual(result["mode"], "READ_ONLY_MXC_HOST_ENV_CHECK")
        self.assertTrue(result["system_drive_present"])
        self.assertTrue(result["local_app_data_present"])
        self.assertTrue(result["required_mxc_transport_host_env_present"])
        self.assertEqual(result["processes_launched"], 0)
        self.assertFalse(result["mxc_native_capability_verified"])
        self.assertNotIn("PRIVATE", capture.getvalue())

    def test_mxc_host_env_check_detects_required_missing_without_runtime(self):
        from types import SimpleNamespace
        with mock.patch.object(p, "os", SimpleNamespace(
                name="nt", environ={"SystemRoot": "PRIVATE_PATH"})):
            result = p.host_environment_report()
        self.assertFalse(result["system_drive_present"])
        self.assertFalse(result["local_app_data_present"])
        self.assertFalse(result["required_mxc_transport_host_env_present"])
        self.assertFalse(result["standalone_mxc_runtime_verified"])
        self.assertEqual(result["processes_launched"], 0)

    def test_mxc_env_mode_is_exclusive_with_live_probe(self):
        for flags in (
                ["--check-mxc-host-environment", "--execute-local-mxc-probe"],
                ["--check-mxc-host-environment", "--execute-local-mxc-compat-only"],
                ["--check-mxc-host-environment", "--check-windows-build"]):
            with self.subTest(flags=flags):
                with contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as exc:
                        p.main(flags)
                self.assertEqual(exc.exception.code, 2)

    def test_native_mxc_errors_take_precedence_over_generic_warning(self):
        samples = [
            (b"WARNING: PRIVATE\nMXC launcher: native MXC is unavailable on this Windows build",
             "MXC_NATIVE_UNAVAILABLE"),
            (b"warning: PRIVATE\nMXC launcher: CreateProcessSecurityEnvironment failed",
             "MXC_LAUNCHER_FAILURE"),
            (b"warning: PRIVATE\nPolicy: allow_mxc=false",
             "MXC_POLICY_RESTRICTION"),
            (b"warning: PRIVATE\nFailed to prepare MXC sandbox",
             "MXC_LAUNCHER_FAILURE"),
            (b"warning: PRIVATE", "GENERAL_WARNING"),
        ]
        for raw, expected in samples:
            with self.subTest(expected=expected):
                self.assertEqual(p.classify_stderr(raw), expected)
                with self.assertRaises(p.ProbeError) as caught:
                    p.evaluate_compatibility(b"", raw, 1)
                exported = p.safe_reason(caught.exception)
                self.assertEqual(exported,
                    "COMPAT_STDERR_PRESENT:" + expected +
                    ":MARKER_ABSENT:EXIT_NONZERO")
                self.assertNotIn("PRIVATE", exported)

    def test_no_explicit_build_success_claims_native_mxc_implemented(self):
        source = SRC.read_text(encoding="utf-8")
        self.assertIn("DOCUMENTED_MINIMUM_UBR = 9278", source)
        self.assertIn("mxc_native_capability_verified", source)
        self.assertIn("managed_policy_mxc_allowed_verified", source)

    def test_compat_only_launches_one_sandbox_without_filesystem_canary(self):
        # Fake standalone transport tests: construct the vetted child env
        # without relying on the CI runner's real Windows variables.
        patched = mock.patch.object(
            p, "mxc_env_for_isolated_home",
            return_value={"SystemDrive": "C:", "LOCALAPPDATA": "PRIVATE",
                          "CODEX_HOME": "PRIVATE_TEST_HOME"})
        patched.start()
        self.addCleanup(patched.stop)
        out = io.StringIO()
        with mock.patch.object(p, "require_pinned_nonadmin_windows"):
            with mock.patch.object(
                    p, "run_subprocess", return_value=(b"MXC_OK\r\n", b"", 0)) as run:
                with mock.patch.object(p, "run_local", side_effect=AssertionError("FS TEST")):
                    with contextlib.redirect_stdout(out):
                        self.assertEqual(p.main(["--execute-local-mxc-compat-only"]), 0)
        result = json.loads(out.getvalue())
        self.assertEqual(result["status"], "MXC_COMPAT_STANDALONE_ECHO_PASS_NOT_ENFORCEMENT")
        self.assertFalse(result["filesystem_negative_test_executed"])
        self.assertFalse(result["standalone_filesystem_isolation_verified"])
        self.assertFalse(result["appserver_turn_mxc_verified"])
        self.assertEqual(result["model_calls_made"], 0)
        self.assertTrue(result["temporary_profile_and_workspace_deleted"])
        self.assertEqual(run.call_count, 1)
        command = run.call_args.args[0]
        self.assertEqual(command, p.compatibility_command(p.h1.CLI))
        self.assertNotIn("workspace-positive.canary", " ".join(command))
        self.assertNotIn("outside-negative.canary", " ".join(command))

    def test_compat_only_stderr_fails_and_fs_test_never_starts(self):
        # Fake standalone transport tests: construct the vetted child env
        # without relying on the CI runner's real Windows variables.
        patched = mock.patch.object(
            p, "mxc_env_for_isolated_home",
            return_value={"SystemDrive": "C:", "LOCALAPPDATA": "PRIVATE",
                          "CODEX_HOME": "PRIVATE_TEST_HOME"})
        patched.start()
        self.addCleanup(patched.stop)
        out = io.StringIO()
        err = io.StringIO()
        with mock.patch.object(p, "require_pinned_nonadmin_windows"):
            with mock.patch.object(p, "run_subprocess",
                                   return_value=(b"", b"native MXC is unavailable on this Windows build", 1)) as run:
                with mock.patch.object(p, "run_local", side_effect=AssertionError("FS TEST")):
                    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                        self.assertEqual(p.main(["--execute-local-mxc-compat-only"]), 2)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(err.getvalue().strip(),
            "STOP: H13_STANDALONE_MXC_FAILED:COMPAT_STDERR_PRESENT:"
            "MXC_NATIVE_UNAVAILABLE:MARKER_ABSENT:EXIT_NONZERO")

    def test_compat_only_does_not_retry_on_warning(self):
        # Fake standalone transport tests: construct the vetted child env
        # without relying on the CI runner's real Windows variables.
        patched = mock.patch.object(
            p, "mxc_env_for_isolated_home",
            return_value={"SystemDrive": "C:", "LOCALAPPDATA": "PRIVATE",
                          "CODEX_HOME": "PRIVATE_TEST_HOME"})
        patched.start()
        self.addCleanup(patched.stop)
        with mock.patch.object(p, "require_pinned_nonadmin_windows"):
            with mock.patch.object(p, "run_subprocess",
                                   return_value=(b"", b"warning: PRIVATE", 1)) as run:
                with self.assertRaises(p.ProbeError):
                    p.run_compatibility_only()
        self.assertEqual(run.call_count, 1)

    def test_compat_only_is_mutually_exclusive_with_fs_and_readonly_modes(self):
        for flags in (["--execute-local-mxc-compat-only", "--execute-local-mxc-probe"],
                      ["--execute-local-mxc-compat-only", "--check-windows-build"]):
            with self.subTest(flags=flags):
                with contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as err:
                        p.main(flags)
                self.assertEqual(err.exception.code, 2)

    def test_compat_only_plan_does_not_claim_runtime_pass(self):
        plan = p.plan()
        self.assertTrue(plan["compat_only_diagnostic_available"])
        self.assertFalse(plan["standalone_mxc_runtime_verified"])
        self.assertEqual(plan["mode"], "PLAN_ONLY_NO_PROCESS")


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

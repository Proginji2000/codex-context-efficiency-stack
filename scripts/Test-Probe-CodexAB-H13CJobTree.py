#!/usr/bin/env python3
"""No-native-process synthetic tests for H1.3c controlled Job tree probe."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).with_name("Probe-CodexAB-H13CJobTree.py")
SPEC = importlib.util.spec_from_file_location("h13c", SCRIPT)
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class H13cTests(unittest.TestCase):
    def test_plan_default_never_runs_windows_job(self):
        data = m.plan()
        self.assertEqual(data["mode"], "PLAN_ONLY_NO_PROCESS")
        self.assertFalse(data["real_windows_job_invoked"])
        self.assertFalse(data["codex_automatic_descendant_cleanup_verified"])
        self.assertFalse(data["all_unknown_descendants_attested"])
        self.assertEqual(data["model_calls_made"], 0)
        with mock.patch.object(m, "run_real", side_effect=AssertionError("should not run")):
            o = io.StringIO()
            with contextlib.redirect_stdout(o):
                self.assertEqual(m.main([]), 0)
        self.assertEqual(json.loads(o.getvalue())["mode"], "PLAN_ONLY_NO_PROCESS")

    def test_expected_three_controlled_job_members_exist(self):
        result = m.verify_snapshot([101, 222, 333, 444], 101, 222, 333)
        self.assertTrue(result["root_observed_in_job"])
        self.assertTrue(result["controlled_child_observed_in_job"])
        self.assertTrue(result["controlled_leaf_observed_in_job"])
        self.assertTrue(result["job_snapshot_at_least_three_processes"])

    def test_snapshot_refuses_missing_root(self):
        with self.assertRaisesRegex(m.GateError, "ROOT_NOT_IN_JOB"):
            m.verify_snapshot([222, 333], 101, 222, 333)

    def test_snapshot_refuses_missing_child_or_leaf(self):
        for ids in ([101, 222], [101, 333], [101]):
            with self.subTest(ids=ids):
                with self.assertRaisesRegex(m.GateError, "READY_PROCESS_NOT_IN_JOB"):
                    m.verify_snapshot(ids, 101, 222, 333)

    def test_snapshot_refuses_pid_reuse_and_injected_values(self):
        for pids in ([101, 101, 222, 333], ["101", 222, 333],
                     [True, 222, 333], [0, 222, 333], [None]):
            with self.subTest(pids=pids):
                with self.assertRaises(m.GateError):
                    m.verify_snapshot(pids, 101, 222, 333)
        for expected in ((101, 101, 333), (101, 222, 222), (-1, 222, 333)):
            with self.subTest(expected=expected):
                with self.assertRaisesRegex(m.GateError, "READY_TIMEOUT_OR_INVALID"):
                    m.verify_snapshot([101, 222, 333], *expected)

    def test_snapshot_rejects_overflow(self):
        pids = list(range(1, m.MAX_JOB_PIDS + 2))
        with self.assertRaisesRegex(m.GateError, "JOB_PROCESS_QUERY_FAILED"):
            m.verify_snapshot(pids, 1, 2, 3)

    def test_cleanup_requires_all_three_signaled_handles(self):
        valid = {"root": True, "child": True, "leaf": True}
        result = m.verify_cleanup(valid, [])
        self.assertTrue(result["job_empty_after_harness_termination"])
        for name in valid:
            broken = dict(valid)
            broken[name] = False
            with self.subTest(name=name):
                with self.assertRaisesRegex(m.GateError, "JOB_PROCESS_STILL_ALIVE"):
                    m.verify_cleanup(broken, [])
        for x in (True, 1, "true", None):
            with self.subTest(x=x):
                with self.assertRaises(m.GateError):
                    m.verify_cleanup({"root": x, "child": True, "leaf": True}, [])

    def test_cleanup_requires_empty_job(self):
        with self.assertRaisesRegex(m.GateError, "JOB_NOT_EMPTY_AFTER_TERMINATE"):
            m.verify_cleanup({"root": True, "child": True, "leaf": True}, [444])

    def test_cleanup_rejects_missing_or_extra_evidence(self):
        for x in ({}, {"root": True, "leaf": True},
                  {"root": True, "child": True, "leaf": True, "unknown": True}):
            with self.subTest(keys=tuple(x.keys())):
                with self.assertRaisesRegex(m.GateError, "JOB_PROCESS_STILL_ALIVE"):
                    m.verify_cleanup(x, [])

    def test_report_never_claims_codex_self_cleanup_or_worker_attestation(self):
        good = m.report(
            m.verify_snapshot([101, 222, 333], 101, 222, 333),
            m.verify_cleanup({"root": True, "child": True, "leaf": True}, []),
        )
        self.assertEqual(good["termination_actor"], "test_harness_terminate_job_object")
        self.assertFalse(good["codex_automatic_descendant_cleanup_verified"])
        self.assertFalse(good["complete_child_tree_cleanup_independently_attested"])
        self.assertFalse(good["unknown_descendant_escapes_independently_excluded"])
        self.assertFalse(good["worker_provenance_verified"])
        self.assertFalse(good["appserver_turn_mxc_verified"])
        self.assertFalse(good["network_isolation_verified"])
        self.assertFalse(good["candidate_merge_authorized"])
        self.assertFalse(good["turn_start_sent"])
        self.assertEqual(good["model_calls_made"], 0)

    def test_ready_file_is_exact_allowlist(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "ready.json"
            path.write_text('{"child_pid":222,"leaf_pid":333}', encoding="ascii")
            self.assertEqual(m.ready_pids(path), {"child_pid": 222, "leaf_pid": 333})
            bad = (
                '{}', '[]', '{"child_pid":"222","leaf_pid":333}',
                '{"child_pid":true,"leaf_pid":333}', '{"child_pid":222,"leaf_pid":222}',
                '{"child_pid":222,"leaf_pid":333,"secret":"PRIVATE"}',
                '{"child_pid":-1,"leaf_pid":333}', '{"child_pid":222}',
            )
            for contents in bad:
                with self.subTest(contents=contents):
                    path.write_text(contents, encoding="ascii")
                    with self.assertRaisesRegex(m.GateError, "READY_TIMEOUT_OR_INVALID"):
                        m.ready_pids(path)

    def test_ready_file_missing_and_huge_fails(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "ready.json"
            with self.assertRaisesRegex(m.GateError, "READY_TIMEOUT_OR_INVALID"):
                m.ready_pids(path)
            path.write_text("X" * (m.MAX_READY_BYTES + 10), encoding="ascii")
            with self.assertRaisesRegex(m.GateError, "READY_TIMEOUT_OR_INVALID"):
                m.ready_pids(path)

    def test_only_documented_pinned_mxc_cli_command(self):
        cmd = m.core.command_for("PINNED", "PYTHON", "CHILD")
        self.assertEqual(cmd, ["PINNED", "-c", "windows.sandbox=mxc",
                               "sandbox", "--include-managed-config",
                               "--permission-profile", ":workspace", "--",
                               "PYTHON", "-B", "CHILD"])
        self.assertNotIn("turn/start", " ".join(cmd))
        self.assertNotIn("exec", cmd)

    def test_child_and_leaf_are_synthetic_and_do_not_network(self):
        for source in (m.RUNNER, m.LEAF, m.CHILD):
            self.assertNotIn("socket", source)
            self.assertNotIn("requests", source)
            self.assertNotIn("urllib", source)
            self.assertNotIn("auth.json", source)
        self.assertIn("subprocess.Popen", m.CHILD)
        self.assertIn("h13c-ready.json", m.CHILD)

    def test_job_kill_on_close_and_suspended_before_assignment_source(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE", source)
        self.assertIn("CREATE_SUSPENDED", source)
        self.assertIn("AssignProcessToJobObject", source)
        self.assertIn("ResumeThread", source)
        self.assertLess(source.index("k.AssignProcessToJobObject(job, info.hProcess)"),
                        source.index("k.ResumeThread(info.hThread)"))
        self.assertIn("TerminateJobObject", source)
        self.assertNotIn("CREATE_BREAKAWAY_FROM_JOB", source)

    def test_safe_errors_never_echo_user_paths_or_pids(self):
        self.assertEqual(m.safe_error(m.GateError("JOB_CREATE_FAILED")), "JOB_CREATE_FAILED")
        for failure in (m.GateError("C:\\SECRET"), OSError("PID=1234 secret"),
                        ValueError("PRIVATE_PATH")):
            self.assertEqual(m.safe_error(failure), "UNCLASSIFIED_LOCAL_FAILURE")

    def test_real_entry_is_windows_only_and_no_accidental_spawn_on_linux(self):
        if m.os.name != "nt":
            with self.assertRaisesRegex(m.core.ProbeError, "WINDOWS_ONLY"):
                m.run_real()

    def test_failure_exit_only_fixed_marker(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(m, "run_real", side_effect=m.GateError("READY_TIMEOUT_OR_INVALID")):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                self.assertEqual(m.main(["--execute-local-job-tree-probe"]), 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue().strip(),
                         "STOP: H13C_JOB_TREE_FAILED:READY_TIMEOUT_OR_INVALID")


if __name__ == "__main__":
    unittest.main()

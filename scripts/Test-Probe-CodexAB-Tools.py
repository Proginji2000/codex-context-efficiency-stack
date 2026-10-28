#!/usr/bin/env python3
"""Offline synthetic test for the single-use read-only Codex tool probe."""
import importlib.util
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

SOURCE = Path(__file__).with_name("Probe-CodexAB-Tools.py")
spec = importlib.util.spec_from_file_location("codex_ab_probe", SOURCE)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class ProbeTests(unittest.TestCase):
    def test_v2_wait_without_spawn_is_not_promotion_to_delegation(self):
        stream = (
            '{"type":"item.started","item":{"type":"collab_tool_call",'
            '"tool":"wait","status":"in_progress",'
            '"receiver_thread_ids":[],"prompt":"SECRET_TASK_BRIEF"}}\n'
            '{"type":"item.completed","item":{"type":"collab_tool_call",'
            '"tool":"wait","status":"completed",'
            '"receiver_thread_ids":[],"agents_states":{'
            '"SECRET_ID":{"status":"errored","message":"SECRET_MESSAGE"}}}}\n'
        )
        result = probe.collab_event_summary(stream)
        self.assertEqual(
            result["observed_events_by_tool_and_status"]["wait"],
            {"in_progress": 1, "completed": 1, "failed": 0})
        self.assertEqual(
            result["observed_events_by_tool_and_status"]["spawn_agent"],
            {"in_progress": 0, "completed": 0, "failed": 0})
        self.assertEqual(result["max_receiver_count_by_tool"]["wait"], 0)
        for secret in ("SECRET_TASK_BRIEF", "SECRET_ID", "SECRET_MESSAGE"):
            self.assertNotIn(secret, json.dumps(result))

    def test_collab_failed_spawn_is_not_success(self):
        stream = (
            '{"type":"item.completed","item":{"type":"collab_tool_call",'
            '"tool":"spawn_agent","status":"failed",'
            '"receiver_thread_ids":[],"prompt":"PRIVATE"}}\n'
        )
        result = probe.collab_event_summary(stream)
        self.assertEqual(
            result["observed_events_by_tool_and_status"]["spawn_agent"]["failed"], 1)
        self.assertEqual(
            result["observed_events_by_tool_and_status"]["spawn_agent"]["completed"], 0)
        self.assertNotIn("PRIVATE", json.dumps(result))

    def test_stderr_classes_do_not_include_sensitive_error_text(self):
        cases = {
            "Error spawning codex-code-mode-host.exe at SECRET_PATH": "CODE_MODE_HOST_MENTION",
            "access is denied to PRIVATE_DIRECTORY": "PERMISSION_MENTION",
            "agent thread limit reached for SECRET_AGENT": "AGENT_LIMIT_MENTION",
            "misc warning PRIVATE_KEY_SENTINEL": "OTHER_OR_NONFATAL_WARNING",
            "": "NONE",
        }
        for content, expected in cases.items():
            category = probe.classify_stderr(content)
            self.assertEqual(category, expected)
            self.assertNotIn("PRIVATE", category)
            self.assertNotIn("SECRET", category)

    def test_one_time_execute_optin_gate(self):
        with self.assertRaises(ValueError):
            probe.probe(Namespace(
                execute=False, timeout=90, pilot="not-used",
                output="not-used", repo="not-used"))

    def test_read_only_marker_is_redacted_and_worker_unverified(self):
        with tempfile.TemporaryDirectory() as dirname:
            work = Path(dirname) / "workspace"
            marker = "deadbeef" * 4
            probe.init_probe_workspace(work, marker)
            stream = (
                '{"type":"turn.started"}\n'
                '{"type":"item.completed","item":{"type":"agent_message",'
                '"text":"PRIVATE_ANNOTATION ' + marker + '"}}\n'
                '{"type":"turn.completed","usage":{'
                '"input_tokens":20,"cached_input_tokens":10,"output_tokens":2}}\n'
            )
            report = probe.summarize(
                stream, "SECRET_STDERR", 0, marker, 0.9, work, False)
            self.assertTrue(report["marker_seen_in_final"])
            self.assertTrue(report["disposable_workspace_unchanged"])
            self.assertFalse(report["delegation_verified"])
            self.assertEqual(report["usage"]["input_tokens"], 20)
            self.assertNotIn(marker, json.dumps(report))
            self.assertNotIn("PRIVATE_ANNOTATION", json.dumps(report))
            self.assertNotIn("SECRET_STDERR", json.dumps(report))

    def test_empty_or_blocked_response_reports_no_proof_of_tools(self):
        with tempfile.TemporaryDirectory() as dirname:
            work = Path(dirname) / "workspace"
            marker = "a" * 32
            probe.init_probe_workspace(work, marker)
            output = '{"type":"item.completed","item":{"type":"agent_message","text":"BLOCKED"}}\n'
            info = probe.summarize(
                output, "", 0, marker, 2, work, False)
            self.assertFalse(info["marker_seen_in_final"])
            self.assertEqual(info["result_class"], "BLOCKED_OR_UNVERIFIED")
            self.assertFalse(info["delegation_event_observed"])

    def test_one_model_call_only_without_leaking_fixture(self):
        with tempfile.TemporaryDirectory() as dirname:
            base = Path(dirname)
            pilot = base / "pilot"
            home = pilot / "baseline-home"
            home.mkdir(parents=True)
            config = b"[agents]\nenabled = true\n"
            (home / "config.toml").write_bytes(config)
            result_dir = base / "new-probe"
            class Proc:
                returncode = 0
                stderr = "SENSITIVE STDERR CONTENT"
                @property
                def stdout(self):
                    return self._out
                def __init__(self, out):
                    self._out = out

            invoked = []
            def fake_cli(command, *, env, timeout):
                invoked.append(command)
                self.assertEqual(command[0], "exec")
                self.assertIn("--ephemeral", command)
                self.assertEqual(command[command.index("--sandbox") + 1],
                                 "read-only")
                self.assertEqual(timeout, 90)
                self.assertTrue(
                    Path(env["CODEX_HOME"]).samefile(home)
                )
                work = Path(command[command.index("-C") + 1])
                token = (work / "marker.txt").read_text(encoding="ascii").strip()
                return Proc(
                    '{"type":"item.completed","item":{"type":"agent_message",'
                    '"text":"' + token + '"}}\n'
                    '{"type":"turn.completed","usage":{'
                    '"input_tokens":1,"cached_input_tokens":0,"output_tokens":1}}\n'
                )
            config_hash = probe.runner.digest(config)
            with (patch.object(probe.runner, "state", return_value={
                    "model": "gpt-6-luna", "sandbox": "workspace-write",
                    "config_sha256": config_hash}),
                  patch.object(probe.runner, "call_codex", side_effect=fake_cli),
                  patch("sys.stdout")):
                rc = probe.probe(Namespace(
                    execute=True, timeout=90, pilot=str(pilot),
                    output=str(result_dir), repo=str(base / "stack-repo")
                ))
            self.assertEqual(rc, 0)
            self.assertEqual(len(invoked), 1)
            info = json.loads((result_dir / "sanitized-probe-result.json").read_text())
            self.assertTrue(info["marker_seen_in_final"])
            self.assertFalse(info["delegation_verified"])
            self.assertNotIn("SENSITIVE", json.dumps(info))
            marker = (result_dir / "workspace" / "marker.txt").read_text().strip()
            self.assertNotIn(marker, json.dumps(info))
            self.assertEqual(info["model_invocations"], 1)

    def test_no_auto_retry_on_failed_subprocess(self):
        with tempfile.TemporaryDirectory() as dirname:
            base = Path(dirname)
            pilot = base / "pilot"
            home = pilot / "baseline-home"
            home.mkdir(parents=True)
            cfg = b"[agents]\nenabled=true\n"
            (home / "config.toml").write_bytes(cfg)
            class Proc:
                stdout = '{"type":"error","message":"PRIVATE_ERR"}\n'
                stderr = "PRIVATE_STDERR"
                returncode = 77
            with (patch.object(probe.runner, "state", return_value={
                    "model": "gpt-6-luna", "sandbox": "workspace-write",
                    "config_sha256": probe.runner.digest(cfg)}),
                  patch.object(probe.runner, "call_codex", return_value=Proc()) as mocked,
                  patch("sys.stdout")):
                result = probe.probe(Namespace(
                    execute=True, timeout=90, pilot=str(pilot),
                    output=str(base / "test-out"), repo=str(base / "repo")
                ))
            self.assertEqual(result, 1)
            mocked.assert_called_once()
            report = json.loads((base / "test-out" / "sanitized-probe-result.json").read_text())
            self.assertEqual(report["codex_returncode"], 77)
            self.assertTrue(report["stderr_present"])
            self.assertNotIn("PRIVATE", json.dumps(report))


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""No-model synthetic subprocess protocol tests for H1 stdio-only preflight."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import contextlib
import io
import queue

MODULE = Path(__file__).with_name("Probe-CodexAB-AppServerH1.py")
SPEC = importlib.util.spec_from_file_location("p11_h1", MODULE)
h = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(h)

FAKE = r'''
import json
import os
import sys
import time
mode = sys.argv[1]
line = sys.stdin.readline()
req = json.loads(line)
if req.get("method") != "initialize" or req.get("id") != 1:
    sys.exit(15)
if mode == "hang":
    time.sleep(3)
    sys.exit(0)
if mode == "notjson":
    sys.stdout.write("PRIVATE-SENSITIVE-JUNK\n")
    sys.stdout.flush()
    time.sleep(1)
    sys.exit(0)
payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "userAgent": "fake test",
        "platformFamily": "windows" if os.name == "nt" else "unix",
        "platformOs": "windows" if os.name == "nt" else "linux",
        "codexHome": os.environ["CODEX_HOME"],
    },
}
if mode == "bad-home":
    payload["result"]["codexHome"] = "/FAKE-WRONG-HOME"
elif mode == "error":
    payload.pop("result")
    payload["error"] = {"code": -1, "message": "PRIVATE"}
elif mode == "wrong-platform":
    payload["result"]["platformOs"] = "not-windows-or-linux"
elif mode == "missing-field":
    payload["result"].pop("userAgent")
elif mode == "wrong-id":
    payload["id"] = 99
sys.stdout.write(json.dumps(payload) + "\n")
sys.stdout.flush()
if mode == "wrong-id":
    time.sleep(1)
    sys.exit(0)
notice = sys.stdin.readline()
if notice:
    msg = json.loads(notice)
    if msg.get("method") != "initialized" or "id" in msg:
        sys.exit(20)
time.sleep(.02)
'''


class H1StdioTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="h1-synth-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / "isolated-home"
        self.home.mkdir()
        self.fake = self.root / "fake.py"
        self.fake.write_text(FAKE, encoding="utf-8")
        self.env = h.env_for_isolated_home(self.home)

    def run_fake(self, mode, timeout=2):
        return h.exchange([sys.executable, "-B", str(self.fake), mode],
                          self.env, str(self.root), timeout=timeout)

    def test_default_never_starts_a_process(self):
        plan = h.plan()
        self.assertEqual(plan["mode"], "PLAN_ONLY_NO_PROCESS")
        self.assertEqual(plan["model_calls_made"], 0)
        self.assertEqual(plan["messages_to_send"], ["initialize", "initialized"])
        self.assertFalse(plan["thread_start_sent"])
        self.assertFalse(plan["turn_start_sent"])

    def test_plan_cli_only_and_no_output_file(self):
        files = sorted(p.name for p in self.root.iterdir())
        self.assertEqual(h.main([]), 0)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), files)

    def test_env_does_not_inherit_tokens_or_old_home(self):
        env = h.env_for_isolated_home(self.home, {
            "PATH": "safe", "CODEX_HOME": "PRIVATE_OLD_PROFILE",
            "OPENAI_API_KEY": "PRIVATE_KEY", "GITHUB_TOKEN": "PRIVATE_GH",
            "ANTHROPIC_API_KEY": "PRIVATE", "HTTPS_PROXY": "PRIVATE_PROXY",
            "SYSTEMROOT": "system",
        })
        self.assertEqual(env["CODEX_HOME"], str(self.home))
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertNotIn("GITHUB_TOKEN", env)
        self.assertNotIn("ANTHROPIC_API_KEY", env)
        self.assertNotIn("HTTPS_PROXY", env)
        self.assertEqual(env["PATH"], "safe")

    def test_good_fake_handshake(self):
        response = self.run_fake("ok")
        self.assertEqual(response, {"handshake": "PASS", "initialized_sent": True})

    def test_schema_missing_field_fails_closed(self):
        with self.assertRaisesRegex(h.PreflightError, "INITIALIZE_REPLY_SCHEMA_MISMATCH"):
            self.run_fake("missing-field")

    def test_wrong_home_fails_closed(self):
        with self.assertRaisesRegex(h.PreflightError, "ISOLATED_HOME_MISMATCH"):
            self.run_fake("bad-home")

    def test_server_rpc_error_fails_closed(self):
        with self.assertRaisesRegex(h.PreflightError, "INITIALIZE_RPC_REJECTED"):
            self.run_fake("error")

    def test_wrong_platform_fails_closed(self):
        with self.assertRaisesRegex(h.PreflightError, "PLATFORM_MISMATCH"):
            self.run_fake("wrong-platform")

    def test_malformed_json_is_not_echoed(self):
        with self.assertRaisesRegex(h.PreflightError, "INVALID_JSON_RESPONSE"):
            self.run_fake("notjson")

    def test_timeout_is_bounded(self):
        with self.assertRaisesRegex(h.PreflightError, "INITIALIZE_RESPONSE_TIMEOUT"):
            self.run_fake("hang", timeout=0.25)

    def test_rpc_wrong_id_is_rejected(self):
        with self.assertRaisesRegex(h.PreflightError, "RPC_ID_MISMATCH"):
            self.run_fake("wrong-id", timeout=1.6)

    def test_disallow_unexpected_notification(self):
        q = __import__("queue").Queue()
        q.put(("line", b'{"jsonrpc":"2.0","method":"thread/started","params":{}}'))
        with self.assertRaisesRegex(h.PreflightError, "UNEXPECTED_STDIO_NOTIFICATION"):
            h._wait_response(q, timeout=1)

    def test_large_line_rejected(self):
        q = __import__("queue").Queue()
        q.put(("too_large", None))
        with self.assertRaisesRegex(h.PreflightError, "INVALID_STDIO_RESPONSE"):
            h._wait_response(q, timeout=1)

    def test_invalid_response_envelope_rejected(self):
        q = __import__("queue").Queue()
        q.put(("line", b'{"jsonrpc":"2.0","id":1,"result":null}'))
        with self.assertRaisesRegex(h.PreflightError, "INITIALIZE_RPC_REJECTED"):
            h._wait_response(q, timeout=1)

    def test_early_child_exit_has_safe_distinct_code(self):
        class ExitedProcess:
            def poll(self):
                return 1
        q = queue.Queue()
        with self.assertRaisesRegex(h.PreflightError, "SERVER_EXITED_BEFORE_INITIALIZE"):
            h._wait_response(q, timeout=1, process=ExitedProcess())

    def test_fixed_diagnostic_does_not_echo_arbitrary_data(self):
        self.assertEqual(h.safe_error_code(h.PreflightError("CLI_VERSION_PROBE_FAILED")),
                         "CLI_VERSION_PROBE_FAILED")
        self.assertEqual(h.safe_error_code(h.PreflightError("PRIVATE_API_TOKEN")),
                         "OTHER_LOCAL_PREFLIGHT_FAILURE")
        self.assertEqual(h.safe_error_code(OSError("C:\\PRIVATE\\auth.json")),
                         "OTHER_LOCAL_PREFLIGHT_FAILURE")

    def test_main_reports_allowlisted_failure_only(self):
        stderr = io.StringIO()
        with mock.patch.object(h, "run_local_preflight",
                               side_effect=h.PreflightError("SERVER_EXITED_BEFORE_INITIALIZE")):
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(h.main(["--execute-local-preflight"]), 2)
        self.assertEqual(stderr.getvalue().strip(),
                         "STOP: H1_LOCAL_PREFLIGHT_FAILED:SERVER_EXITED_BEFORE_INITIALIZE")

    def test_main_redacts_unexpected_failure_text(self):
        stderr = io.StringIO()
        with mock.patch.object(h, "run_local_preflight",
                               side_effect=OSError("PRIVATE_KEY_OR_LOCAL_PATH")):
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(h.main(["--execute-local-preflight"]), 2)
        self.assertEqual(stderr.getvalue().strip(),
                         "STOP: H1_LOCAL_PREFLIGHT_FAILED:OTHER_LOCAL_PREFLIGHT_FAILURE")

    def test_no_cli_source_or_model_execution_in_mock_tests(self):
        source = MODULE.read_text(encoding="utf-8")
        self.assertIn('"turn_start_sent": False', source)
        self.assertIn('"model_calls_made": 0', source)
        self.assertNotIn('"method": "turn/start"', source)
        self.assertNotIn('"method": "thread/start"', source)
        self.assertNotIn("danger-full-access", source)


if __name__ == "__main__":
    unittest.main()

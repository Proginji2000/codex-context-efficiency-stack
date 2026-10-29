#!/usr/bin/env python3
"""Synthetic tests for H1.2 real-thread probe, using a FAKE local subprocess.

No Codex CLI, network, secrets, existing CODEX_HOME or model calls.
"""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).with_name("Probe-CodexAB-H12RealThread.py")
SPEC = importlib.util.spec_from_file_location("p11_h12_real", SCRIPT)
app = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(app)

FAKE_SERVER = r'''
import json, os, sys, time
mode = sys.argv[1]
def recv():
    line = sys.stdin.readline()
    if not line: sys.exit(18)
    return json.loads(line)
def send(msg):
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()
req = recv()
if req.get("method") != "initialize" or req.get("id") != 1: sys.exit(12)
send({"id":1,"result":{"userAgent":"FAKE","platformFamily":
    "windows" if os.name=="nt" else "unix",
    "platformOs":"windows" if os.name=="nt" else "linux",
    "codexHome":os.environ["CODEX_HOME"]}})
if recv().get("method") != "initialized": sys.exit(13)
req = recv()
if req.get("method") != "thread/start": sys.exit(14)
if req.get("params",{}).get("approvalPolicy") != "never": sys.exit(15)
if req.get("params",{}).get("sandbox") != "workspace-write": sys.exit(16)
if req.get("params",{}).get("ephemeral") is not True: sys.exit(17)
if mode == "timeout":
    time.sleep(3)
    sys.exit(0)
if mode == "bad-json":
    sys.stdout.write("PRIVATE_SERVER_OUTPUT\n")
    sys.stdout.flush()
    time.sleep(.1)
    sys.exit(0)
if mode == "bad-id":
    send({"id":89,"result":{"private":"secret"}})
    time.sleep(.1)
    sys.exit(0)
if mode == "bad-version":
    send({"jsonrpc":"1.0","id":2,"result":{}})
    sys.exit(0)
if mode == "rpc-error":
    send({"id":2,"error":{"code":-1,"message":"PRIVATE ERROR"}})
    sys.exit(0)
if mode == "unknown-notification":
    send({"method":"auth/secret","params":{"key":"PRIVATE"}})
    sys.exit(0)
if mode == "notification":
    send({"method":"thread/started","params":{"threadId":"PRIVATE"}})
p = req["params"]
send({"id":2,"result":{
    "approvalPolicy":p["approvalPolicy"],"model":p["model"],
    "reasoningEffort":"medium","cwd":p["cwd"],
    "sandbox":{"type":"workspaceWrite","writableRoots":[p["cwd"]],
               "networkAccess":False,"excludeTmpdirEnvVar":True,
               "excludeSlashTmp":True},
    "thread":{"id":"PRIVATE_WORKER_ID","ephemeral":True,"turns":[]},
    "instructionSources":[]
}})
time.sleep(.02)
'''


class RealH12OfflineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="p11-h12-fake-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / "codex-home"
        self.workspace = self.root / "workspace"
        self.home.mkdir()
        self.workspace.mkdir()
        self.fake = self.root / "fake-stdio.py"
        self.fake.write_text(FAKE_SERVER, encoding="utf-8")
        self.env = app.h1.env_for_isolated_home(self.home)

    def execute_fake(self, mode="good", timeout=3):
        # Original policy checker intentionally verifies WINDOWS paths only;
        # on Linux CI, stub that single cross-platform checker, and test its
        # real logic separately in Test-Check-CodexAB-H12ThreadPolicy.py.
        if os.name == "nt":
            return app.perform_exchange(
                [sys.executable, "-B", str(self.fake), mode],
                self.env, self.root, self.home, self.workspace,
                init_timeout=3, thread_timeout=timeout,
            )
        fixed = app.policy.validate(
            app.policy.request_for_workspace(app.policy.SYNTHETIC_WORKSPACE),
            app.policy.synthetic_response(
                app.policy.SYNTHETIC_WORKSPACE, app.policy.SYNTHETIC_HOME),
            app.policy.SYNTHETIC_WORKSPACE, app.policy.SYNTHETIC_HOME)
        with mock.patch.object(app.policy, "validate", return_value=fixed):
            return app.perform_exchange(
                [sys.executable, "-B", str(self.fake), mode],
                self.env, self.root, self.home, self.workspace,
                init_timeout=3, thread_timeout=timeout,
            )

    def test_default_plan_starts_no_process(self):
        report = app.plan()
        self.assertEqual(report["mode"], "PLAN_ONLY_NO_PROCESS")
        self.assertEqual(report["model_calls_made"], 0)
        self.assertEqual(report["real_messages_sent"], 0)
        self.assertEqual(report["messages_planned"],
                         ["initialize", "initialized", "thread/start"])
        self.assertFalse(report["turn_start_sent"])

    def test_successful_fake_local_thread_only(self):
        result = self.execute_fake("good")
        self.assertEqual(result["status"], "THREAD_START_DECLARED_POLICY_PASS_UNATTESTED")
        self.assertTrue(result["real_thread_created"])
        self.assertEqual(result["model_calls_made"], 0)
        self.assertFalse(result["turn_start_sent"])
        self.assertFalse(result["runtime_mxc_effectiveness_verified"])
        self.assertFalse(result["candidate_merge_authorized"])
        output = json.dumps(result)
        for secret in ("PRIVATE", "fake-stdio", "C:\\", "secret"):
            self.assertNotIn(secret, output)

    def test_known_notification_before_reply(self):
        self.assertTrue(self.execute_fake("notification")["real_thread_created"])

    def test_wrong_reply_id_is_rejected(self):
        with self.assertRaisesRegex(app.GateError, "THREAD_RPC_ID_MISMATCH"):
            self.execute_fake("bad-id")

    def test_malformed_response_is_rejected_without_leak(self):
        with self.assertRaisesRegex(app.GateError, "THREAD_MESSAGE_INVALID"):
            self.execute_fake("bad-json")

    def test_invalid_protocol_version_is_rejected(self):
        with self.assertRaisesRegex(app.GateError, "THREAD_MESSAGE_INVALID"):
            self.execute_fake("bad-version")

    def test_rpc_error_is_rejected_without_leak(self):
        with self.assertRaisesRegex(app.GateError, "THREAD_RPC_REJECTED"):
            self.execute_fake("rpc-error")

    def test_unknown_notification_is_rejected(self):
        with self.assertRaisesRegex(app.GateError, "THREAD_NOTIFICATION_UNEXPECTED"):
            self.execute_fake("unknown-notification")

    def test_bounded_timeout(self):
        with self.assertRaisesRegex(app.GateError, "THREAD_RESPONSE_TIMEOUT"):
            self.execute_fake("timeout", timeout=0.3)

    def test_reject_bad_echo_fail_closed(self):
        with mock.patch.object(app.policy, "validate", side_effect=app.policy.PolicyError(
                "UNEXPECTED_WRITABLE_ROOT")):
            with self.assertRaisesRegex(app.GateError, "THREAD_ECHO_VALIDATION_FAILED"):
                app.perform_exchange([sys.executable, "-B", str(self.fake), "good"],
                                     self.env, self.root, self.home, self.workspace,
                                     init_timeout=3, thread_timeout=3)

    def test_fixed_error_classifications(self):
        self.assertEqual(app._safe_code(app.GateError("THREAD_RPC_REJECTED")),
                         "THREAD_RPC_REJECTED")
        self.assertEqual(app._safe_code(app.GateError("PRIVATE_KEY")),
                         "EXTERNAL_SCRIPT_FAILURE")
        self.assertEqual(app._safe_code(OSError("C:\\Users\\private")),
                         "EXTERNAL_SCRIPT_FAILURE")

    def test_no_model_or_turn_call_embedded_in_source(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn('"method": "turn/start"', text)
        self.assertNotIn('"method": "command/exec"', text)
        self.assertNotIn("danger-full-access", text)

    def test_cli_redacts_unexpected_local_errors(self):
        stderr = io.StringIO()
        with mock.patch.object(app, "run_local",
                               side_effect=OSError("PRIVATE_AUTH_INFORMATION")):
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(app.main(["--execute-local-thread-probe"]), 2)
        self.assertEqual(stderr.getvalue().strip(),
                         "STOP: H12_REAL_THREAD_PROBE_FAILED:EXTERNAL_SCRIPT_FAILURE")

    def test_cli_fails_closed_on_known_local_error(self):
        stderr = io.StringIO()
        with mock.patch.object(app, "run_local",
                               side_effect=app.GateError("PINNED_VERSION_MISMATCH")):
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(app.main(["--execute-local-thread-probe"]), 2)
        self.assertEqual(stderr.getvalue().strip(),
                         "STOP: H12_REAL_THREAD_PROBE_FAILED:PINNED_VERSION_MISMATCH")

    def test_unknown_event_without_id_rejected(self):
        inbox = queue.Queue()
        inbox.put(("line", b'{"method":"unlisted/event","params":{"private":"secret"}}'))
        with self.assertRaisesRegex(app.GateError, "THREAD_NOTIFICATION_UNEXPECTED"):
            app._receive_thread_response(inbox, timeout=1)

    def test_bounded_queue_rejects_oversized_payload(self):
        inbox = queue.Queue()
        inbox.put(("too_large", None))
        with self.assertRaisesRegex(app.GateError, "THREAD_RESPONSE_TOO_LARGE"):
            app._receive_thread_response(inbox, timeout=1)

    def test_wrong_response_type_rejected(self):
        inbox = queue.Queue()
        inbox.put(("line", b'{"id":2,"result":null}'))
        with self.assertRaisesRegex(app.GateError, "THREAD_MESSAGE_INVALID"):
            app._receive_thread_response(inbox, timeout=1)

    def test_local_env_isolation_is_reused(self):
        assert "OPENAI_API_KEY" not in app.h1.env_for_isolated_home(
            self.home, {"OPENAI_API_KEY": "PRIVATE", "PATH": "safe"})
        self.assertEqual(self.env["CODEX_HOME"], str(self.home))


if __name__ == "__main__":
    unittest.main()

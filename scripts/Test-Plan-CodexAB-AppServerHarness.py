#!/usr/bin/env python3
"""Offline contract and negative-path tests for P1.1 app-server mock harness."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

SRC = Path(__file__).with_name("Plan-CodexAB-AppServerHarness.py")
spec = importlib.util.spec_from_file_location("p11_harness", SRC)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)


class AppServerHarnessTests(unittest.TestCase):
    def test_plan_twelve_not_authorized_in_balanced_order(self):
        plan = h.plan()
        self.assertEqual(plan["planned_runs_not_authorized"], 12)
        self.assertEqual(plan["case_count"], 3)
        self.assertEqual(plan["model_calls"], 0)
        self.assertFalse(plan["live_execution_implemented"])
        for case in h.cases():
            subset = [r for r in plan["runs"] if r["case_id"] == case["id"]]
            self.assertEqual([r["arm"] for r in subset],
                             ["candidate", "baseline", "baseline", "candidate"])
            self.assertEqual(len({r["prompt_contract"] for r in subset}), 1)

    def test_mock_all_cases_succeed_without_real_calls(self):
        for case in h.cases():
            result = h.simulate(case["id"])
            self.assertEqual(result["status"], "SYNTHETIC_PROTOCOL_SIMULATION_PASS")
            self.assertEqual(result["request_sequence"],
                             ["initialize", "thread/start", "turn/start"])
            self.assertEqual(result["model_calls"], 0)
            self.assertEqual(result["files_written"], 0)
            self.assertFalse(result["real_app_server_connected"])
            self.assertFalse(result["effective_mxc_policy_verified_in_runtime"])
            self.assertFalse(result["worker_delegation_independently_verified_in_runtime"])

    def test_initialize_matches_0165_protocol(self):
        request = h.initialize_request()
        self.assertEqual(request["method"], "initialize")
        self.assertEqual(request["params"]["capabilities"], None)
        self.assertEqual(request["jsonrpc"], "2.0")
        self.assertEqual(request["params"]["clientInfo"]["name"], "codex-ab-harness-mock")

    def test_thread_model_approval_sandbox(self):
        req = h.thread_request(h.cases()[0])
        self.assertEqual(req["params"]["approvalPolicy"], "never")
        self.assertEqual(req["params"]["sandbox"], "workspace-write")
        self.assertEqual(req["params"]["model"], "gpt-6-luna")
        self.assertTrue(req["params"]["ephemeral"])
        self.assertEqual(req["params"]["config"]["windows"]["sandbox"], "mxc")
        self.assertEqual(req["params"]["config"]["model_reasoning_effort"], "medium")

    def test_turn_no_escalation(self):
        request = h.turn_request(h.cases()[0], "SYNTHETIC")
        self.assertEqual(request["params"]["approvalPolicy"], "never")
        self.assertEqual(request["params"]["effort"], "medium")
        self.assertNotIn("sandboxPolicy", request["params"])

    def test_mock_endpoint_disallows_random_methods_and_order(self):
        server = h.MockEndpoint()
        with self.assertRaisesRegex(h.HarnessError, "MOCK_ONLY_METHOD"):
            server.call(h.thread_request(h.cases()[0]))
        with self.assertRaisesRegex(h.HarnessError, "MOCK_ONLY_METHOD"):
            server.call(h.request(3, "turn/start", {}))
        with self.assertRaisesRegex(h.HarnessError, "MOCK_ONLY_METHOD"):
            server.call(h.request(9, "command/exec", {}))

    def test_rpc_mismatch_and_error_fail_closed(self):
        req = h.initialize_request()
        with self.assertRaisesRegex(h.HarnessError, "RPC_ID_OR_ERROR"):
            h.rpc_result(req, {"jsonrpc": "2.0", "id": 999, "result": {}})
        with self.assertRaisesRegex(h.HarnessError, "RPC_ID_OR_ERROR"):
            h.rpc_result(req, {"jsonrpc": "2.0", "id": 1, "error": {"code": -1}})

    def test_thread_policy_mismatch_denied(self):
        server = h.MockEndpoint()
        server.call(h.initialize_request())
        req = h.thread_request(h.cases()[0])
        response = server.call(req)
        response["result"]["approvalPolicy"] = "on-request"
        with self.assertRaisesRegex(h.HarnessError, "POLICY_ECHO_MISMATCH"):
            h.assert_thread_policy(req, response)

    def test_thread_sandbox_network_or_scope_mismatch_denied(self):
        for bad_field, bad_value in (("networkAccess", True),
                                     ("writableRoots", ["/OUT-OF-BOUNDS"]),
                                     ("type", "dangerFullAccess")):
            server = h.MockEndpoint()
            server.call(h.initialize_request())
            req = h.thread_request(h.cases()[0])
            response = server.call(req)
            response["result"]["sandbox"][bad_field] = bad_value
            with self.assertRaisesRegex(h.HarnessError, "SANDBOX_ECHO_MISMATCH"):
                h.assert_thread_policy(req, response)

    def test_bad_thread_request_rejected(self):
        server = h.MockEndpoint()
        server.call(h.initialize_request())
        req = h.thread_request(h.cases()[0])
        req["params"]["approvalPolicy"] = "on-request"
        with self.assertRaisesRegex(h.HarnessError, "INVALID_THREAD_REQUEST"):
            h.assert_thread_policy(req, server.call(req))

    def test_mock_events_require_single_worker_and_completed_turn(self):
        server = h.MockEndpoint()
        server.call(h.initialize_request())
        server.call(h.thread_request(h.cases()[0]))
        server.call(h.turn_request(h.cases()[0], server.thread_id))
        events = server.synthetic_events()
        report = h.require_worker_events(events)
        self.assertEqual(report["spawn_completed"], 1)
        with self.assertRaisesRegex(h.HarnessError, "WORKER_LIFECYCLE_INCOMPLETE"):
            h.require_worker_events(events[:-1])
        events[-1]["params"]["turn"]["status"] = "failed"
        with self.assertRaisesRegex(h.HarnessError, "WORKER_LIFECYCLE_INCOMPLETE"):
            h.require_worker_events(events)

    def test_missing_start_or_agent_event_rejected(self):
        server = h.MockEndpoint()
        server.call(h.initialize_request())
        server.call(h.thread_request(h.cases()[0]))
        server.call(h.turn_request(h.cases()[0], server.thread_id))
        events = server.synthetic_events()
        with self.assertRaisesRegex(h.HarnessError, "WORKER_LIFECYCLE_INCOMPLETE"):
            h.require_worker_events(events[1:])
        with self.assertRaisesRegex(h.HarnessError, "WORKER_LIFECYCLE_INCOMPLETE"):
            h.require_worker_events(events[:3] + events[4:])

    def test_non_mock_endpoint_must_be_refused(self):
        class FakeNetworkTransport:
            pass
        with self.assertRaisesRegex(h.HarnessError, "LIVE_ENDPOINT_FORBIDDEN"):
            h.simulate("arith-control", FakeNetworkTransport())

    def test_unknown_fixture_is_not_silently_used(self):
        with self.assertRaisesRegex(h.HarnessError, "UNKNOWN_CASE"):
            h.simulate("UNTRUSTED")

    def test_cli_requires_no_paths_and_writes_no_files(self):
        with tempfile.TemporaryDirectory() as temp:
            before = set(Path(temp).iterdir())
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(h.main([]), 0)
                self.assertEqual(h.main(["--simulate", "device-reconcile"]), 0)
            self.assertEqual(before, set(Path(temp).iterdir()))
            output = stdout.getvalue()
            self.assertIn("OFFLINE_PLAN_ONLY", output)
            self.assertIn("SYNTHETIC_PROTOCOL_SIMULATION_PASS", output)
            self.assertNotIn("auth.json", output)


if __name__ == "__main__":
    unittest.main()

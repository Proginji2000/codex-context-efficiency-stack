#!/usr/bin/env python3
"""Offline H1.3d negative network attribution acceptance tests. No IO."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest import mock

PATH = Path(__file__).with_name("Plan-CodexAB-H13DNetwork.py")
SPEC = importlib.util.spec_from_file_location("h13d", PATH)
p = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p)


class H13dNetworkDecisionTests(unittest.TestCase):
    def sample(self):
        v = p.fabricated_sample()
        v["source"] = "real_independent_observation"
        return v

    def test_no_process_no_network_default(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(p.main([]), 0)
        report = json.loads(out.getvalue())
        self.assertEqual(report["mode"], "PLAN_ONLY_NO_NETWORK_OR_PROCESS")
        self.assertFalse(report["real_test_implemented"])
        self.assertFalse(report["real_network_egress_verified"])

    def test_simulated_sample_explicitly_rejected_as_runtime(self):
        self.assertEqual(p.fabricated_sample()["source"], "fabricated")
        with self.assertRaisesRegex(p.EvidenceError, "SYNTHETIC_EVIDENCE_NOT_RUNTIME"):
            p.evaluate(p.fabricated_sample())
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(p.main(["--simulate"]), 0)
        j = json.loads(output.getvalue())
        self.assertEqual(j["status"], "H13D_FABRICATED_INPUT_REJECTED_PASS")
        self.assertFalse(j["real_network_egress_verified"])

    def test_full_hypothetical_inputs_do_not_claim_this_tool_ran_network(self):
        v = self.sample()
        r = p.evaluate(v)
        self.assertEqual(r["status"], "H13D_EVIDENCE_CONDITIONS_SATISFIED_NOT_RUNTIME")
        self.assertFalse(r["actual_network_io_run_by_this_tool"])
        self.assertFalse(r["network_egress_real_verified"])
        self.assertFalse(r["candidate_merge_authorized"])

    def test_missing_or_extra_fields_fail_closed(self):
        v = self.sample()
        v.pop("managed_proxy_mode_verified")
        with self.assertRaisesRegex(p.EvidenceError, "EVIDENCE_SHAPE_INVALID"):
            p.evaluate(v)
        v = self.sample()
        v["secret"] = "PRIVATE"
        with self.assertRaisesRegex(p.EvidenceError, "EVIDENCE_SHAPE_INVALID"):
            p.evaluate(v)
        with self.assertRaisesRegex(p.EvidenceError, "EVIDENCE_SHAPE_INVALID"):
            p.evaluate([])

    def test_flags_must_be_real_booleans(self):
        v = self.sample()
        for name in p.FIELDS - {"source", "sandbox_connect_result"}:
            v = self.sample()
            v[name] = 1
            with self.subTest(flag=name):
                with self.assertRaisesRegex(p.EvidenceError, "EVIDENCE_SHAPE_INVALID"):
                    p.evaluate(v)

    def test_policy_backend_and_proxy_must_be_verified(self):
        scenarios = (
            ("windows_mxc_selected", "MXC_BACKEND_UNATTESTED"),
            ("network_policy_declared_deny", "NETWORK_POLICY_NOT_DENY"),
            ("managed_proxy_mode_verified", "NETWORK_PROXY_TOPOLOGY_UNVERIFIED"),
        )
        for flag, reason in scenarios:
            v = self.sample()
            v[flag] = False
            with self.subTest(flag=flag):
                with self.assertRaisesRegex(p.EvidenceError, reason):
                    p.evaluate(v)

    def test_owned_numeric_non_loopback_endpoint_and_host_control_required(self):
        scenarios = (
            ("endpoint_owned_and_controlled", "NETWORK_ENDPOINT_NOT_CONTROLLED"),
            ("endpoint_numeric_non_loopback", "NETWORK_ENDPOINT_NOT_CONTROLLED"),
            ("host_can_connect_same_endpoint", "HOST_POSITIVE_CONTROL_FAILED"),
        )
        for flag, reason in scenarios:
            v = self.sample()
            v[flag] = False
            with self.subTest(flag=flag):
                with self.assertRaisesRegex(p.EvidenceError, reason):
                    p.evaluate(v)

    def test_non_observed_attempt_is_not_denial(self):
        v = self.sample()
        v["sandbox_attempt_observed"] = False
        with self.assertRaisesRegex(p.EvidenceError, "SANDBOX_ATTEMPT_NOT_OBSERVED"):
            p.evaluate(v)

    def test_proxy_fallback_cannot_be_counted_as_denial(self):
        v = self.sample()
        v["sandbox_used_proxy_or_fallback"] = True
        with self.assertRaisesRegex(p.EvidenceError, "SANDBOX_USED_UNCONTROLLED_NETWORK_PATH"):
            p.evaluate(v)

    def test_any_confirmed_connection_is_fail_even_when_caller_says_denied(self):
        v = self.sample()
        v["endpoint_observed_sandbox_connection"] = True
        with self.assertRaisesRegex(p.EvidenceError, "NETWORK_ESCAPE_OBSERVED"):
            p.evaluate(v)

    def test_dns_timeout_unreachable_and_refused_do_not_prove_policy_deny(self):
        for outcome in sorted(p.UNACCEPTABLE):
            v = self.sample()
            v["sandbox_connect_result"] = outcome
            with self.subTest(outcome=outcome):
                with self.assertRaisesRegex(p.EvidenceError, "NETWORK_DENIAL_NOT_ATTRIBUTABLE"):
                    p.evaluate(v)

    def test_os_block_evidence_is_independently_required(self):
        v = self.sample()
        v["independent_os_block_evidence"] = False
        with self.assertRaisesRegex(p.EvidenceError, "NETWORK_OS_DENY_UNATTESTED"):
            p.evaluate(v)

    def test_invalid_and_ambiguous_result_types_rejected(self):
        for result in (None, True, 3, "", "blocked", "network_error"):
            v = self.sample()
            v["sandbox_connect_result"] = result
            with self.subTest(result=result):
                with self.assertRaisesRegex(p.EvidenceError, "SANDBOX_CONNECT_RESULT_INVALID"):
                    p.evaluate(v)

    def test_no_socket_subprocess_or_model_in_source(self):
        source = PATH.read_text(encoding="utf-8")
        for dangerous in ("import socket", "import requests", "import urllib",
                          "subprocess.Popen", "subprocess.run", "turn/start",
                          "http.client"):
            with self.subTest(dangerous=dangerous):
                self.assertNotIn(dangerous, source)


if __name__ == "__main__":
    unittest.main()

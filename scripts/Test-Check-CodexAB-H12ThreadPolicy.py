#!/usr/bin/env python3
"""Pure synthetic H1.2 policy echo tests; never connect to Codex."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

SRC = Path(__file__).with_name("Check-CodexAB-H12ThreadPolicy.py")
SPEC = importlib.util.spec_from_file_location("p11_h12", SRC)
h = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(h)


class ThreadPolicyTests(unittest.TestCase):
    def setUp(self):
        self.w = h.SYNTHETIC_WORKSPACE
        self.home = h.SYNTHETIC_HOME
        self.req = h.request_for_workspace(self.w)
        self.reply = h.synthetic_response(self.w, self.home)

    def check(self, reply=None, request=None):
        return h.validate(request or self.req, reply or self.reply, self.w, self.home)

    def test_default_plan_does_not_allow_execution(self):
        p = h.plan()
        self.assertEqual(p["mode"], "OFFLINE_PLAN_ONLY")
        self.assertEqual(p["model_calls_made"], 0)
        self.assertFalse(p["next_proposed_messages_executed"])
        self.assertFalse(p["turn_start_allowed"])
        self.assertTrue(p["requires_separate_local_execution_authorization"])

    def test_synthetic_echo_is_not_mxc_attestation(self):
        r = self.check()
        self.assertEqual(r["approval_echo"], "never")
        self.assertFalse(r["network_access_echo"])
        self.assertFalse(r["windows_mxc_runtime_verified"])
        self.assertFalse(r["real_thread_created"])
        self.assertFalse(r["candidate_merge_authorized"])

    def test_codex_versionless_response_and_optional_valid_field(self):
        self.assertEqual(self.check()["status"], "SYNTHETIC_THREAD_POLICY_ECHO_PASS")
        self.reply["jsonrpc"] = "2.0"
        self.assertEqual(self.check()["status"], "SYNTHETIC_THREAD_POLICY_ECHO_PASS")

    def test_invalid_wire_version(self):
        self.reply["jsonrpc"] = "1.0"
        with self.assertRaisesRegex(h.PolicyError, "INVALID_WIRE_VERSION"):
            self.check()

    def test_reject_approval_policy_escalation(self):
        self.reply["result"]["approvalPolicy"] = "on-request"
        with self.assertRaisesRegex(h.PolicyError, "POLICY_ECHO_MISMATCH"):
            self.check()

    def test_reject_model_or_effort_mismatch(self):
        self.reply["result"]["model"] = "unapproved-model"
        with self.assertRaisesRegex(h.PolicyError, "POLICY_ECHO_MISMATCH"):
            self.check()
        self.reply["result"]["model"] = h.MODEL
        self.reply["result"]["reasoningEffort"] = "high"
        with self.assertRaisesRegex(h.PolicyError, "REASONING_ECHO_MISMATCH"):
            self.check()

    def test_reject_network_enabled(self):
        self.reply["result"]["sandbox"]["networkAccess"] = True
        with self.assertRaisesRegex(h.PolicyError, "SANDBOX_NETWORK_UNPROVEN"):
            self.check()

    def test_reject_danger_full_access(self):
        self.reply["result"]["sandbox"] = {"type": "dangerFullAccess"}
        with self.assertRaisesRegex(h.PolicyError, "SANDBOX_TYPE_MISMATCH"):
            self.check()

    def test_reject_unapproved_root_even_when_workspace_present(self):
        self.reply["result"]["sandbox"]["writableRoots"].append(r"C:\Users\PRIVATE")
        with self.assertRaisesRegex(h.PolicyError, "UNEXPECTED_WRITABLE_ROOT"):
            self.check()

    def test_reject_missing_workspace_root(self):
        self.reply["result"]["sandbox"]["writableRoots"] = [self.home]
        with self.assertRaisesRegex(h.PolicyError, "WRITABLE_ROOTS_MISMATCH"):
            self.check()

    def test_reject_duplicate_roots_with_case_changes(self):
        self.reply["result"]["sandbox"]["writableRoots"] = [self.w, self.w.lower()]
        with self.assertRaisesRegex(h.PolicyError, "WRITABLE_ROOTS_MISMATCH"):
            self.check()

    def test_reject_non_ephemeral_or_turns_preexisting(self):
        self.reply["result"]["thread"]["ephemeral"] = False
        with self.assertRaisesRegex(h.PolicyError, "THREAD_NOT_EPHEMERAL"):
            self.check()
        self.reply["result"]["thread"]["ephemeral"] = True
        self.reply["result"]["thread"]["turns"] = [{"private": "text"}]
        with self.assertRaisesRegex(h.PolicyError, "TURNS_ALREADY_PRESENT"):
            self.check()

    def test_reject_foreign_instruction_sources(self):
        self.reply["result"]["instructionSources"] = [r"C:\Users\Private\AGENTS.md"]
        with self.assertRaisesRegex(h.PolicyError, "INSTRUCTION_OUTSIDE_ISOLATION"):
            self.check()
        self.reply["result"]["instructionSources"] = [self.w + r"\AGENTS.md"]
        self.assertEqual(self.check()["instruction_source_count"], 1)

    def test_reject_bad_cwd(self):
        self.reply["result"]["cwd"] = self.home
        with self.assertRaisesRegex(h.PolicyError, "CWD_ECHO_MISMATCH"):
            self.check()

    def test_reject_nonabsolute_unc_or_overlapping_paths(self):
        for value in ("relative", r"\\attacker\share", ""):
            with self.assertRaises(h.PolicyError):
                h.canonical_windows_path(value)
        with self.assertRaisesRegex(h.PolicyError, "HOME_AND_WORKSPACE_OVERLAP"):
            h.validate(self.req, self.reply, self.w, self.w + r"\home")

    def test_reject_response_error_or_mismatched_id(self):
        self.reply["id"] = 3
        with self.assertRaisesRegex(h.PolicyError, "INVALID_RPC_RESPONSE"):
            self.check()
        self.reply["id"] = 2
        self.reply["error"] = {"message": "PRIVATE"}
        with self.assertRaisesRegex(h.PolicyError, "RPC_REJECTED"):
            self.check()

    def test_reject_mutated_request(self):
        altered = copy.deepcopy(self.req)
        altered["params"]["config"]["windows"]["sandbox"] = "danger-full-access"
        with self.assertRaisesRegex(h.PolicyError, "POLICY_REQUEST_MISMATCH"):
            self.check(request=altered)

    def test_no_sensitive_input_values_are_returned(self):
        self.reply["result"]["thread"]["id"] = "PRIVATE_THREAD_ID"
        self.reply["result"]["thread"]["sessionId"] = "PRIVATE_SESSION_ID"
        report = json.dumps(self.check())
        for sentinel in ("PRIVATE", "C:\\", "sessionId", "SYNTHETIC-THREAD"):
            self.assertNotIn(sentinel, report)

    def test_cli_only_exposes_offline_modes(self):
        source = SRC.read_text(encoding="utf-8")
        self.assertNotIn("subprocess", source)
        self.assertNotIn("socket.", source)
        self.assertNotIn("--execute", source)
        self.assertEqual(h.main(["--simulate"]), 0)


if __name__ == "__main__":
    unittest.main()

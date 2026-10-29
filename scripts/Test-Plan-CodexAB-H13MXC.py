#!/usr/bin/env python3
"""H1.3 pure synthetic contract tests; no sandbox or Codex execution."""
import copy
import importlib.util
import io
import contextlib
import json
from pathlib import Path
import sys
import unittest

SRC = Path(__file__).with_name("Plan-CodexAB-H13MXC.py")
SPEC = importlib.util.spec_from_file_location("p11_h13", SRC)
p = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p)


class H13MatrixTests(unittest.TestCase):
    def test_plan_has_zero_effects(self):
        plan = p.plan()
        self.assertEqual(plan["mode"], "PLAN_ONLY_NO_PROCESS")
        self.assertFalse(plan["user_approved_runtime_run"])
        self.assertFalse(plan["proposed_runtime_launcher_implemented"])
        self.assertEqual(plan["model_calls_made"], 0)
        self.assertFalse(plan["turn_start_sent"])
        self.assertFalse(plan["thread_start_sent"])

    def test_source_is_production_runtime_distinct(self):
        plan = p.plan()
        self.assertEqual(plan["scope"], "standalone_cli_sandbox_not_appserver_turn")
        self.assertEqual(plan["official_cli_entry"], "codex sandbox")
        self.assertEqual(plan["official_backend_selection"], "windows.sandbox=mxc")
        self.assertFalse(plan["standalone_runtime_mxc_verified"])
        self.assertFalse(plan["appserver_turn_runtime_mxc_verified"])
        self.assertFalse(plan["network_isolation_verified"])

    def test_future_gates_are_explicit(self):
        gates = p.plan()["future_gates"]
        self.assertEqual(len(gates), 4)
        self.assertIn("H1.3a_standalone_mxc_runtime_negative_test", gates)
        self.assertTrue(any("requires_separate_approval" in s for s in gates))

    def test_synthetic_matrix_pass_not_runtime(self):
        result = p.evaluate_synthetic_evidence(p.simulate_evidence())
        self.assertEqual(result["status"], "SYNTHETIC_H13_MATRIX_PASS_NOT_RUNTIME")
        self.assertTrue(result["all_inputs_fabricated"])
        self.assertFalse(result["real_mxc_process_launched"])
        self.assertFalse(result["standalone_runtime_mxc_verified"])
        self.assertFalse(result["appserver_turn_runtime_mxc_verified"])
        self.assertFalse(result["worker_provenance_verified"])

    def test_all_security_predicates_fail_closed(self):
        fixture = p.simulate_evidence()
        for field in p.REQUIRED:
            with self.subTest(field=field):
                altered = copy.deepcopy(fixture)
                altered[field] = False
                with self.assertRaisesRegex(p.MatrixError, "EVIDENCE_PREDICATE_FAILED"):
                    p.evaluate_synthetic_evidence(altered)

    def test_non_bool_truthy_is_denied(self):
        for value in ("true", 1, [], {}):
            with self.subTest(value=repr(value)):
                altered = p.simulate_evidence()
                altered["no_model_call"] = value
                with self.assertRaisesRegex(p.MatrixError, "EVIDENCE_PREDICATE_FAILED"):
                    p.evaluate_synthetic_evidence(altered)

    def test_missing_extra_or_wrong_type_fails(self):
        original = p.simulate_evidence()
        for bad in (None, [], "unsafe", {}, {**original, "surprise": True}):
            with self.subTest(type=type(bad).__name__):
                with self.assertRaises(p.MatrixError):
                    p.evaluate_synthetic_evidence(bad)
        missing = p.simulate_evidence()
        del missing["no_global_config_mutation"]
        with self.assertRaisesRegex(p.MatrixError, "EVIDENCE_SCHEMA_MISMATCH"):
            p.evaluate_synthetic_evidence(missing)

    def test_real_source_cannot_be_passed_as_fake(self):
        sample = p.simulate_evidence()
        sample["source"] = "REAL_OS"
        with self.assertRaisesRegex(p.MatrixError, "SOURCE_NOT_SYNTHETIC"):
            p.evaluate_synthetic_evidence(sample)

    def test_default_cli_is_not_runtime(self):
        self.assertEqual(p.main([]), 0)
        self.assertEqual(p.main(["--simulate"]), 0)

    def test_pure_no_capability_to_launch(self):
        text = SRC.read_text(encoding="utf-8")
        for forbidden in ("import subprocess", "import socket", "os.system",
                          "subprocess.run", "subprocess.Popen", "--execute-local"):
            self.assertNotIn(forbidden, text)

    def test_error_output_is_fixed_no_paths(self):
        capture = io.StringIO()
        with contextlib.redirect_stderr(capture):
            with self.assertRaises(SystemExit):
                p.main(["--execute-local-mxc"])
        self.assertNotIn("C:\\", capture.getvalue())


if __name__ == "__main__":
    unittest.main()

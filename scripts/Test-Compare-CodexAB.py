#!/usr/bin/env python3
"""Synthetic-only regression tests for Compare-CodexAB.py."""

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("Compare-CodexAB.py")
spec = importlib.util.spec_from_file_location("codex_ab", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

CONTROLS = {
    "cli_version": "0.164.0",
    "model": "luna-medium",
    "reasoning_effort": "medium",
    "sandbox": "workspace-write",
    "repo_head": "50fa713ca6fa753a11eb435eb4b6f76cd447b57",
    "mcp_profile": "all",
    "prompt_sha256": "c" * 64,
}


def fixture(pair_count=3):
    runs = []
    for pair in range(1, pair_count + 1):
        for arm in ("baseline", "candidate"):
            candidate = arm == "candidate"
            runs.append({
                "pair": pair, "arm": arm, "controls": dict(CONTROLS),
                "agents_sha": "b" * 40 if candidate else "a" * 40,
                "case_id": "test-case-01",
                "success": True, "delegated": True, "parent_orchestrated": True,
                "safety_pass": True, "retries": 0,
                "elapsed_s": 8.0 if candidate else 10.0,
                "usage": {
                    "complete_turns": 1, "turns_with_usage": 1,
                    "failed_turns": 0, "input_tokens": 750 if candidate else 1000,
                    "cached_input_tokens": 250 if candidate else 200,
                    "output_tokens": 30,
                },
            })
    return {"schema_version": 1, "runs": runs}


class TestCodexAB(unittest.TestCase):
    def test_complete_candidate_is_only_for_manual_review(self):
        report = module.analyze(fixture())
        self.assertEqual(report["status"], "manual_review_candidate")
        self.assertFalse(report["merge_authorized"])
        self.assertEqual(report["pair_count"], 3)
        self.assertEqual(report["uncached_input_change_pct"], -37.5)

    def test_smaller_sample_is_insufficient(self):
        report = module.analyze(fixture(2))
        self.assertEqual(report["status"], "insufficient_repetitions")

    def test_behavior_regression_is_not_hidden_by_savings(self):
        doc = fixture()
        doc["runs"][1]["parent_orchestrated"] = False
        report = module.analyze(doc)
        self.assertEqual(report["status"], "behavior_or_usage_regression")

    def test_missing_counters_cannot_be_treated_as_zero(self):
        doc = fixture()
        doc["runs"][1]["usage"]["turns_with_usage"] = 0
        self.assertEqual(module.analyze(doc)["status"], "behavior_or_usage_regression")

    def test_control_mismatch_is_rejected(self):
        doc = fixture()
        doc["runs"][1]["controls"]["model"] = "different-model"
        with self.assertRaises(ValueError):
            module.analyze(doc)

    def test_duplicate_and_partial_pairs_are_rejected(self):
        doc = fixture()
        doc["runs"].append(copy.deepcopy(doc["runs"][0]))
        with self.assertRaises(ValueError):
            module.analyze(doc)
        doc = fixture()
        doc["runs"].pop()
        with self.assertRaises(ValueError):
            module.analyze(doc)

    def test_bad_usage_and_variant_fingerprints_are_rejected(self):
        doc = fixture()
        doc["runs"][0]["usage"]["cached_input_tokens"] = 2000
        with self.assertRaises(ValueError):
            module.analyze(doc)
        doc = fixture()
        doc["runs"][1]["agents_sha"] = "a" * 40
        with self.assertRaises(ValueError):
            module.analyze(doc)

    def test_no_private_input_echoed_on_invalid_cli_file(self):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "sanitized.json"
            file.write_text('{"prompt":"PRIVATE_SENTINEL_DO_NOT_LOG"}', encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), "--input", str(file)],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(proc.returncode, 2)
            self.assertNotIn("PRIVATE_SENTINEL_DO_NOT_LOG", proc.stderr + proc.stdout)


if __name__ == "__main__":
    unittest.main()

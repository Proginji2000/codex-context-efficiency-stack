#!/usr/bin/env python3
"""Synthetic, strictly offline TUI results summary tests; no Codex or external data."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).with_name("Summarize-CodexAB-TUI-Repeats.py")
SPEC = importlib.util.spec_from_file_location("codex_tui_report", MODULE)
app = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(app)


class TuiReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name) / "v3"
        self.log = Path(self.tmp.name) / "terminal.txt"
        self.events = []
        for pair, arm in app.planned_arms(4, 2):
            path = Path(str(self.base) + f"-pair{pair:02d}-{arm}")
            path.mkdir()
            report = {
                "schema_version": 1,
                "arm": arm,
                "prompt_contract": app.DEFAULT_CONTRACT,
                "execution_surface": "codex-interactive-tui-not-exec",
                "model": "gpt-6-luna",
                "sandbox": "workspace-write",
                "approval_policy_override_requested": "never",
                "windows_sandbox_override_requested": "mxc",
                "python_test_fallback_hint_requested": True,
                "codex_cli_exit_code": 0,
                "functional_and_scope_pass": True,
                "worker_delegation_independently_verified": False,
                "policy_effectiveness": "not_runtime_attested",
                "elapsed_s": {(4, 'candidate'): 160.411, (4, 'baseline'): 72.378,
                              (5, 'baseline'): 128.465, (5, 'candidate'): 69.156}[(pair, arm)],
                "verification": dict.fromkeys(app.REQUIRED_CHECKS, True),
            }
            report["verification"].update({"unittest_exit_code": 0, "tracked_modified_file_count": 1})
            (path / "sanitized-tui-result.json").write_text(json.dumps(report), encoding="utf-8")
            self.events.append((pair, arm, path))
        nums = [(26090,25381,71680,709,237),(37957,36996,110336,961,163),
                (15344,14857,88704,487,29),(23906,22970,114304,936,262)]
        lines = ["Private sentinel: SHOULD_NEVER_APPEAR_IN_OUTPUT"]
        for (pair, arm, _), (total, inp, cached, out, reasoning) in zip(self.events, nums):
            lines.extend([f"BEGIN_INTERACTIVE_CANARY: p{pair:02d}:{arm}",
                          f"Token usage: total={total:,} input={inp:,} (+ {cached:,} cached) output={out:,} (reasoning {reasoning})".replace(",", "\u202f"),
                          f"INDEPENDENT_CANARY_PASS: p{pair:02d}:{arm}"])
        self.log.write_text("\n".join(lines), encoding="utf-8")

    def test_four_v3_pass_and_private_log_not_emitted(self):
        res = app.analyze(str(self.base), terminal_log=str(self.log))
        self.assertEqual(res["run_count"], 4)
        self.assertEqual([r["arm"] for r in res["runs"]], ["candidate","baseline","baseline","candidate"])
        self.assertEqual(res["totals"]["baseline"]["reported_tokens"], 53301)
        self.assertEqual(res["totals"]["candidate"]["reported_tokens"], 49996)
        self.assertEqual(res["pairs"][0]["candidate_delta_pct"], -31.26)
        self.assertEqual(res["pairs"][1]["candidate_delta_pct"], 55.8)
        self.assertEqual(res["candidate_combined_token_delta_pct_descriptive_only"], -6.2)
        self.assertEqual(res["totals"]["candidate"]["elapsed_s"], 229.567)
        self.assertFalse(res["merge_authorized"])
        self.assertNotIn("PRIVATE", json.dumps(res))
        self.assertNotIn("cached_input_tokens", json.dumps(res))

    def test_default_has_no_token_claim_and_no_writes(self):
        before = {p: p.read_bytes() for _,_,path in self.events for p in path.iterdir()}
        res = app.analyze(str(self.base))
        self.assertIsNone(res["candidate_combined_token_delta_pct_descriptive_only"])
        self.assertEqual(res["token_source"], "not_available")
        self.assertEqual(before, {p: p.read_bytes() for _,_,path in self.events for p in path.iterdir()})

    def test_failed_acceptance_rejected(self):
        path = self.events[1][2] / "sanitized-tui-result.json"
        content = json.loads(path.read_text())
        content["verification"]["git_diff_check_pass"] = False
        path.write_text(json.dumps(content))
        with self.assertRaisesRegex(app.EvidenceError, "REPORT_QUALITY_GATES_FAILED"):
            app.analyze(str(self.base))

    def test_contract_mismatch_rejected(self):
        path = self.events[0][2] / "sanitized-tui-result.json"
        data = json.loads(path.read_text())
        data["prompt_contract"] = "p1.1-git-diff-selfcheck-v2"
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(app.EvidenceError, "REPORT_CONTRACT_OR_ACCEPTANCE_MISMATCH"):
            app.analyze(str(self.base))

    def test_missing_and_duplicate_usage_rejected(self):
        source = self.log.read_text(encoding="utf-8")
        self.log.write_text(source.replace("Token usage:", "NOT usage:", 1))
        with self.assertRaisesRegex(app.EvidenceError, "TERMINAL_PASS_INVALID"):
            app.analyze(str(self.base), terminal_log=str(self.log))
        self.log.write_text(source.replace("INDEPENDENT_CANARY_PASS: p04:candidate", "Token usage: total=3 input=2 (+ 2 cached) output=1\nINDEPENDENT_CANARY_PASS: p04:candidate", 1))
        with self.assertRaisesRegex(app.EvidenceError, "TERMINAL_USAGE_INVALID"):
            app.analyze(str(self.base), terminal_log=str(self.log))

    def test_usage_accounting_mismatch_rejected(self):
        self.log.write_text(self.log.read_text(encoding="utf-8").replace("total=26\u202f090", "total=26\u202f091"))
        with self.assertRaisesRegex(app.EvidenceError, "TERMINAL_USAGE_INCONSISTENT"):
            app.analyze(str(self.base), terminal_log=str(self.log))

    def test_missing_run_and_output_symlink_rejected(self):
        self.events[0][2].rename(self.events[0][2].with_name("hidden"))
        with self.assertRaisesRegex(app.EvidenceError, "MISSING_OR_LINKED_OUTPUT"):
            app.analyze(str(self.base))

    def test_cli_safe_failure_without_path_echo(self):
        code = app.main(["--output-base", str(self.base), "--contract", "p1.1-other-v4"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Offline synthetic tests: never call Codex, login, network or existing sessions."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).with_name("Run-CodexAB.py")
spec = importlib.util.spec_from_file_location("codex_ab_runner", SOURCE)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class RunnerTests(unittest.TestCase):
    def test_jsonl_counts_without_leaking_message(self):
        events = (
            '{"type":"turn.started"}\n'
            '{"type":"item.completed","item":{"type":"agent_message","text":"PRIVATE_CONTENT"}}\n'
            '{"type":"item.completed","item":{"type":"collab_tool_call",'
            '"tool":"spawn_agent","status":"completed","receiver_thread_ids":["some-child"]}}\n'
            '{"type":"turn.completed","usage":{"input_tokens":120,'
            '"cached_input_tokens":80,"output_tokens":7}}\n'
        )
        usage, delegated, valid, retries = runner.parse_events(events)
        self.assertTrue(delegated)
        self.assertTrue(valid)
        self.assertEqual(retries, 0)
        self.assertEqual(usage["complete_turns"], 1)
        self.assertEqual(usage["input_tokens"], 120)
        self.assertEqual(usage["cached_input_tokens"], 80)
        self.assertNotIn("PRIVATE_CONTENT", str(usage))

    def test_missing_spawn_is_unverified_not_success(self):
        usage, delegated, valid, retries = runner.parse_events(
            '{"type":"item.completed","item":{"type":"collab_tool_call",'
            '"tool":"wait","receiver_thread_ids":[]}}\n'
            '{"type":"turn.completed","usage":{"input_tokens":7,'
            '"cached_input_tokens":0,"output_tokens":1}}'
        )
        self.assertFalse(delegated)
        self.assertTrue(valid)

    def test_bad_usage_never_becomes_valid_zero(self):
        usage, delegated, valid, retries = runner.parse_events(
            '{"type":"turn.completed","usage":{"input_tokens":4,'
            '"cached_input_tokens":8,"output_tokens":1}}'
        )
        self.assertFalse(valid)
        self.assertEqual(usage["turns_with_usage"], 0)

    def test_disposable_repo_determinism_and_test_failure(self):
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            first, second = root / "first", root / "second"
            self.assertEqual(runner.make_fixture(first), runner.make_fixture(second))
            self.assertFalse(runner.verify(first))
            (first / "total.py").write_text(
                "def total(lignes):\n    return sum(prix * quantite for prix, quantite in lignes)\n",
                encoding="utf-8"
            )
            self.assertTrue(runner.verify(first))
            with self.assertRaises(FileExistsError):
                runner.make_fixture(first)

    def test_prepared_instructions_cannot_silently_change(self):
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            for arm in runner.ARMS:
                folder = root / (arm + "-home")
                folder.mkdir()
                (folder / "AGENTS.md").write_text(arm, encoding="utf-8")
            runner.save_json(root / "benchmark-state.json", {
                "schema_version": 1,
                "candidate_commit": runner.COMMIT,
                "baseline_sha256": runner.digest(b"baseline"),
                "candidate_sha256": runner.digest(b"candidate"),
                "cli_version": "irrelevant"
            })
            # Patch only the local CLI version getter, never inspect user config.
            original = runner.call
            try:
                class Stub:
                    stdout = "irrelevant\n"
                runner.call = lambda *a, **kw: Stub()
                runner.state(root)
                (root / "candidate-home" / "AGENTS.md").write_text(
                    "changed", encoding="utf-8"
                )
                with self.assertRaises(ValueError):
                    runner.state(root)
            finally:
                runner.call = original

    def test_codex_home_isolation_drops_inherited_auth_and_db_paths(self):
        import os
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            with patch.dict(os.environ, {
                "CODEX_SQLITE_HOME": "UNSAFE_SHARED_DB",
                "OPENAI_API_KEY": "PRIVATE_KEY_SENTINEL",
                "CODEX_API_KEY": "PRIVATE_KEY_SENTINEL",
                "CODEX_ACCESS_TOKEN": "PRIVATE_KEY_SENTINEL",
                "OPENAI_BASE_URL": "https://example.invalid",
            }):
                env = runner.home_env(root, "baseline")
                self.assertEqual(env["CODEX_HOME"], str(root / "baseline-home"))
                for name in ("CODEX_SQLITE_HOME", "OPENAI_API_KEY",
                             "CODEX_API_KEY", "CODEX_ACCESS_TOKEN", "OPENAI_BASE_URL"):
                    self.assertNotIn(name, env)
                self.assertEqual(os.environ["OPENAI_API_KEY"], "PRIVATE_KEY_SENTINEL")

    def test_execute_opt_in_gate(self):
        from argparse import Namespace
        with self.assertRaises(ValueError):
            runner.run(Namespace(output="unused", execute=False, pairs=1, timeout=10))


if __name__ == "__main__":
    unittest.main()

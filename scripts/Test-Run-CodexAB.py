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

    def test_existing_output_yields_safe_precise_error(self):
        from argparse import Namespace
        with tempfile.TemporaryDirectory() as dirname:
            with self.assertRaisesRegex(runner.PrepareError, "OUTPUT_ALREADY_EXISTS"):
                runner.prepare(Namespace(
                    repo=str(Path(__file__).resolve().parent.parent),
                    output=dirname, baseline=None, candidate_file=None
                ))

    def test_missing_global_agents_keeps_output_uncreated(self):
        from argparse import Namespace
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            target = root / "not-created"
            with self.assertRaisesRegex(runner.PrepareError, "BASELINE_UNAVAILABLE"):
                runner.prepare(Namespace(
                    repo=str(Path(__file__).resolve().parent.parent),
                    output=str(target), baseline=str(root / "missing-AGENTS.md"),
                    candidate_file=None
                ))
            self.assertFalse(target.exists())

    def test_pinned_git_candidate_preferred_without_https(self):
        from argparse import Namespace
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as dirname:
            work = Path(dirname)
            repo = work / "repo"
            (repo / "templates" / "agents").mkdir(parents=True)
            (repo / "templates" / "config.routing.snippet.toml").write_text(
                "[agents]\nenabled = true\n", encoding="utf-8")
            for role in runner.ROLES:
                (repo / "templates" / "agents" / (role + ".toml")).write_text(
                    "model = 'gpt-6-luna'\n", encoding="utf-8")
            baseline = work / "original-AGENTS.md"
            baseline.write_bytes(b"baseline-only\n")
            output = work / "pilot"
            class LocalObject:
                returncode = 0
                stdout = b"candidate-from-pinned-commit\n"
            class CliVersion:
                returncode = 0
                stdout = "codex-cli 0.164.0\n"
            with (patch.object(runner.subprocess, "run", return_value=LocalObject()),
                  patch.object(runner.shutil, "which", return_value="codex.exe"),
                  patch.object(runner, "call", return_value=CliVersion()),
                  patch.object(runner.urllib.request, "urlopen",
                               side_effect=AssertionError("HTTPS must not be used"))):
                runner.prepare(Namespace(
                    repo=str(repo), output=str(output),
                    baseline=str(baseline), candidate_file=None
                ))
            self.assertEqual(
                (output / "candidate-home" / "AGENTS.md").read_bytes(),
                b"candidate-from-pinned-commit\n"
            )
            self.assertEqual(
                (output / "baseline-home" / "AGENTS.md").read_bytes(),
                b"baseline-only\n"
            )
            self.assertTrue((output / "benchmark-state.json").is_file())

    def test_execute_opt_in_gate(self):
        from argparse import Namespace
        with self.assertRaises(ValueError):
            runner.run(Namespace(output="unused", execute=False, pairs=1, timeout=10))


if __name__ == "__main__":
    unittest.main()

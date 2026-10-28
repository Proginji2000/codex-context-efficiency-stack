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
            original = runner.call_codex
            try:
                class Stub:
                    stdout = "irrelevant\n"
                runner.call_codex = lambda *a, **kw: Stub()
                runner.state(root)
                (root / "candidate-home" / "AGENTS.md").write_text(
                    "changed", encoding="utf-8"
                )
                with self.assertRaises(ValueError):
                    runner.state(root)
            finally:
                runner.call_codex = original

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

    def test_resolve_windows_npm_posix_shim_to_sibling_cmd(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            posix_shim = root / "codex"
            posix_shim.write_text("#!/bin/sh\n", encoding="utf-8")
            cmd = root / "codex.cmd"
            cmd.write_text("@echo off\r\n", encoding="utf-8")
            with patch.object(runner.shutil, "which", side_effect=lambda key: (
                str(posix_shim) if key == "codex" else None
            )):
                self.assertEqual(
                    runner.resolve_codex_executable(windows=True), str(cmd)
                )

    def test_resolve_windows_powershell_ps1_to_sibling_cmd(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            ps1 = root / "codex.ps1"
            ps1.write_text("Write-Output test\n", encoding="utf-8")
            cmd = root / "codex.cmd"
            cmd.write_text("@echo off\r\n", encoding="utf-8")
            with patch.object(runner.shutil, "which", return_value=str(ps1)):
                self.assertEqual(
                    runner.resolve_codex_executable(windows=True), str(cmd)
                )

    @unittest.skipUnless(__import__("os").name == "nt", "Windows native launcher regression")
    def test_windows_explicit_cmd_can_launch_version_without_shell(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as dirname:
            cmd = Path(dirname) / "codex.cmd"
            cmd.write_bytes(b"@echo off\r\necho codex-cli-synthetic 0.164.0\r\n")
            with patch.object(runner, "resolve_codex_executable",
                              return_value=str(cmd)):
                proc = runner.call_codex(["--version"])
            self.assertEqual(proc.returncode, 0)
            self.assertIn("codex-cli-synthetic", proc.stdout)

    def test_equivalent_arithmetic_passes_functional_gate(self):
        with tempfile.TemporaryDirectory() as dirname:
            work = Path(dirname) / "equivalent"
            runner.make_fixture(work)
            (work / "total.py").write_text(
                "def total(lignes):\n    return sum(quantite * prix for prix, quantite in lignes)\n",
                encoding="utf-8")
            detail = runner.verification_detail(work)
            self.assertTrue(detail["unittest_pass"])
            self.assertTrue(detail["functional_and_scope_pass"])
            self.assertFalse(detail["old_literal_expression_present"])
            self.assertFalse(detail["old_gate_would_pass"])
            self.assertTrue(runner.verify(work))

    def test_inspect_failed_trial_no_codex_no_source_echo(self):
        from argparse import Namespace
        from contextlib import redirect_stdout
        from io import StringIO
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            runner.make_fixture(root / "workspaces" / "pair-1-baseline")
            fixture = {
                "schema_version": 1,
                "runs": [{
                    "pair": 1, "arm": "baseline",
                    "success": False, "delegated": False,
                    "elapsed_s": 12.0,
                    "usage": {
                        "input_tokens": 114680, "cached_input_tokens": 100000,
                        "output_tokens": 234, "complete_turns": 1
                    },
                }],
            }
            (root / "anonymized-results.json").write_text(
                json.dumps(fixture), encoding="utf-8")
            output = StringIO()
            with (patch.object(runner, "call_codex",
                               side_effect=AssertionError("No model invocation allowed")),
                  redirect_stdout(output)):
                self.assertEqual(
                    runner.inspect(Namespace(output=str(root))), 0)
            report = json.loads(output.getvalue())
            first = report["runs"][0]
            self.assertEqual(first["uncached_input_tokens"], 14680)
            self.assertEqual(first["input_tokens"], 114680)
            self.assertFalse(first["verification"]["unittest_pass"])
            self.assertFalse(first["recorded_success"])
            self.assertNotIn("total(lignes)", output.getvalue())
            self.assertNotIn("auth.json", output.getvalue())

    def test_inspect_rejects_workspace_symlink(self):
        from argparse import Namespace
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            (root / "workspaces").mkdir()
            try:
                (root / "workspaces" / "pair-1-baseline").symlink_to(
                    root, target_is_directory=True)
            except OSError:
                self.skipTest("Symlinks unavailable on this Windows test runner")
            (root / "anonymized-results.json").write_text(json.dumps({
                "schema_version": 1, "runs": [{
                    "pair": 1, "arm": "baseline",
                    "usage": {"input_tokens": 1, "cached_input_tokens": 0,
                              "output_tokens": 1}
                }]
            }), encoding="utf-8")
            with self.assertRaises(ValueError):
                runner.inspect(Namespace(output=str(root)))

    def test_inspect_distinguishes_no_edits_from_other_edits(self):
        with tempfile.TemporaryDirectory() as dirname:
            work = Path(dirname) / "test"
            runner.make_fixture(work)
            before = runner.verification_detail(work)
            self.assertEqual(before["tracked_modified_file_count"], 0)
            self.assertFalse(before["total_py_changed"])
            self.assertFalse(before["unexpected_tracked_modifications"])
            (work / "tests" / "test_total.py").write_text(
                "import unittest\nfrom total import total\n", encoding="utf-8"
            )
            after = runner.verification_detail(work)
            self.assertEqual(after["tracked_modified_file_count"], 1)
            self.assertFalse(after["total_py_changed"])
            self.assertTrue(after["unexpected_tracked_modifications"])

    def test_safe_cli_metadata_does_not_echo_commands_secrets_or_errors(self):
        raw = (
            '{"type":"item.started","item":{"type":"command_execution",'
            '"command":"echo PRIVATE_COMMAND_SENTINEL"}}\n'
            '{"type":"item.completed","item":{"type":"command_execution",'
            '"command":"echo PRIVATE_COMMAND_SENTINEL",'
            '"aggregated_output":"PRIVATE_OUTPUT_SENTINEL"}}\n'
            '{"type":"item.completed","item":{"type":"file_change",'
            '"changes":[{"path":"PRIVATE_PATH_SENTINEL"}]}}\n'
            '{"type":"item.completed","item":{"type":"collab_tool_call",'
            '"receiver_thread_ids":["PRIVATE_THREAD_SENTINEL"]}}\n'
            '{"type":"error","message":"PRIVATE_ERROR_SENTINEL"}\n'
        )
        result = runner.summarize_cli_events(
            raw, "PRIVATE_STDERR_SENTINEL", 17)
        self.assertEqual(result["cli_exit_code"], 17)
        self.assertTrue(result["stderr_present"])
        self.assertEqual(result["events"]["command_started"], 1)
        self.assertEqual(result["events"]["command_completed"], 1)
        self.assertEqual(result["events"]["file_changes_completed"], 1)
        self.assertEqual(result["events"]["subagent_events_seen"], 1)
        self.assertEqual(result["events"]["error_events_seen"], 1)
        serialized = json.dumps(result)
        for secret in ("PRIVATE_COMMAND_SENTINEL", "PRIVATE_OUTPUT_SENTINEL",
                       "PRIVATE_PATH_SENTINEL", "PRIVATE_THREAD_SENTINEL",
                       "PRIVATE_ERROR_SENTINEL", "PRIVATE_STDERR_SENTINEL"):
            self.assertNotIn(secret, serialized)

    def test_timeout_diagnostic_is_explicit_without_fake_exit_code(self):
        data = runner.summarize_cli_events("", "", None, timed_out=True)
        self.assertTrue(data["timed_out"])
        self.assertIsNone(data["cli_exit_code"])
        self.assertFalse(data["stderr_present"])

    def test_execute_opt_in_gate(self):
        from argparse import Namespace
        with self.assertRaises(ValueError):
            runner.run(Namespace(output="unused", execute=False, pairs=1, timeout=10))


if __name__ == "__main__":
    unittest.main()

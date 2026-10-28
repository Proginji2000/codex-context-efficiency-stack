#!/usr/bin/env python3
"""Offline-only Codex TUI canary tests; never invoke a Codex model."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from types import SimpleNamespace
from unittest.mock import patch

SOURCE = Path(__file__).with_name("Run-CodexAB-TUI-Canary.py")
SPEC = importlib.util.spec_from_file_location("codex_ab_tui_canary", SOURCE)
app = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(app)


class TuiCanaryTests(unittest.TestCase):
    def test_safe_error_codes_do_not_reflect_private_exception_text(self):
        self.assertEqual(
            app.classified_error(ValueError("ISOLATED_CONFIG_HASH_MISMATCH")),
            "ISOLATED_CONFIG_HASH_MISMATCH",
        )
        self.assertEqual(
            app.classified_error(ValueError("AGENTS fingerprint mismatch: experiment must stop")),
            "AGENTS_FINGERPRINT_MISMATCH",
        )
        self.assertEqual(
            app.classified_error(ValueError("private-key=SECRET_CANARY")),
            "UNCLASSIFIED_PREFLIGHT_FAILURE",
        )
        self.assertEqual(
            app.classified_error(FileNotFoundError("C:/PRIVATE/path")),
            "REQUIRED_FILE_NOT_FOUND",
        )

    def test_diagnose_is_readonly_and_reports_mismatch_without_leakage(self):
        import io
        with tempfile.TemporaryDirectory() as name:
            pilot = Path(name) / "pilot"
            baseline = pilot / "baseline-home"
            candidate = pilot / "candidate-home"
            baseline.mkdir(parents=True)
            candidate.mkdir()
            b_agents = b"BASELINE_PRIVATE_AGENTS"
            c_agents = b"CANDIDATE_PRIVATE_AGENTS"
            b_config = b"[agents]\nenabled = true\n"
            (baseline / "AGENTS.md").write_bytes(b_agents)
            (candidate / "AGENTS.md").write_bytes(c_agents)
            (baseline / "config.toml").write_bytes(b_config)
            (pilot / "benchmark-state.json").write_text(
                json.dumps({
                    "schema_version": 1,
                    "candidate_commit": app.runner.COMMIT,
                    "baseline_sha256": app.runner.digest(b_agents),
                    "candidate_sha256": app.runner.digest(c_agents),
                    "config_sha256": app.runner.digest(b"OLDER_CONFIG"),
                    "cli_version": "codex-cli 0.164.0",
                }), encoding="utf-8",
            )
            result = io.StringIO()
            with (patch.object(
                        app.runner, "call_codex",
                        return_value=SimpleNamespace(
                            returncode=0, stdout="codex-cli 0.164.0\n")),
                  patch("sys.stdout", result)):
                exit_code = app.diagnose(Namespace(pilot=str(pilot)))
            self.assertEqual(exit_code, 0)
            report = json.loads(result.getvalue())
            self.assertTrue(report["experiment_state_valid"])
            self.assertTrue(report["baseline_agents_match"])
            self.assertTrue(report["candidate_agents_match"])
            self.assertFalse(report["routing_config_match"])
            self.assertTrue(report["cli_version_matches"])
            self.assertTrue(report["toml_parseable"])
            self.assertFalse(report["preflight_ready"])
            self.assertEqual(report["model_calls_made"], 0)
            for secret in ("BASELINE_PRIVATE_AGENTS", "CANDIDATE_PRIVATE_AGENTS", "OLDER_CONFIG"):
                self.assertNotIn(secret, result.getvalue())
            self.assertNotIn(str(pilot), result.getvalue())

    def test_diagnose_missing_state_is_safe_no_exception_details(self):
        import io
        with tempfile.TemporaryDirectory() as name:
            pilot = Path(name) / "pilot"
            pilot.mkdir()
            result = io.StringIO()
            with (patch.object(app.runner, "call_codex",
                               side_effect=AssertionError("No subprocess needed")),
                  patch("sys.stdout", result)):
                exit_code = app.diagnose(Namespace(pilot=str(pilot)))
            self.assertEqual(exit_code, 0)
            report = json.loads(result.getvalue())
            self.assertFalse(report["preflight_ready"])
            self.assertEqual(report["diagnostic_error_code"], "REQUIRED_FILE_NOT_FOUND")
            self.assertNotIn(str(pilot), result.getvalue())

    def test_optin_required_before_files_or_codex(self):
        with patch.object(app.runner, "state", side_effect=AssertionError("called")):
            with self.assertRaisesRegex(ValueError, "EXPLICIT_EXECUTE_REQUIRED"):
                app.run(Namespace(
                    pilot="unused", output="unused", repo="unused",
                    execute=False,
                ))

    def test_no_overwrite_or_path_inside_pilot(self):
        with tempfile.TemporaryDirectory() as name:
            base = Path(name)
            pilot = base / "pilot"
            repo = base / "repo"
            pilot.mkdir()
            repo.mkdir()
            occupied = base / "occupied"
            occupied.mkdir()
            for candidate in (occupied, pilot / "new", repo / "new",
                              pilot, repo):
                with self.assertRaisesRegex(ValueError, "UNSAFE_OR_EXISTING_OUTPUT"):
                    app.validate_paths(pilot, candidate, repo)

    def test_single_tui_command_sandbox_home_and_success(self):
        with tempfile.TemporaryDirectory() as name:
            base = Path(name)
            repo = base / "repo"
            repo.mkdir()
            pilot = base / "pilot"
            home = pilot / "baseline-home"
            home.mkdir(parents=True)
            (home / "config.toml").write_text(
                "[agents]\nenabled=true\n", encoding="utf-8")
            (home / "auth.json").write_text(
                "PRIVATE_AUTH_SENTINEL", encoding="utf-8")
            out = base / "canary"
            original = subprocess.run
            executed = []
            def fake_subprocess(cmd, **kwargs):
                if cmd[0] == "git" or cmd[0] == sys.executable:
                    return original(cmd, **kwargs)
                executed.append(cmd)
                self.assertEqual(cmd[0], "fake-codex.cmd")
                self.assertIn("--model", cmd)
                self.assertEqual(cmd[cmd.index("--model") + 1], "gpt-6-luna")
                self.assertEqual(
                    cmd[cmd.index("--sandbox") + 1], "workspace-write")
                self.assertEqual(
                    cmd[cmd.index("--ask-for-approval") + 1], "on-request")
                self.assertEqual(
                    Path(kwargs["env"]["CODEX_HOME"]).resolve(), home.resolve())
                self.assertIn("Delegate this exact task", " ".join(cmd))
                work = Path(kwargs["cwd"])
                self.assertEqual(
                    work.resolve(),
                    Path(cmd[cmd.index("--cd") + 1]).resolve())
                (work / "total.py").write_text(
                    "def total(lignes):\n"
                    "    return sum(prix * quantite for prix, quantite in lignes)\n",
                    encoding="utf-8")
                return SimpleNamespace(returncode=0)

            with (patch.object(app.runner, "state", return_value={
                    "model": "gpt-6-luna",
                    "reasoning_effort": "medium",
                    "sandbox": "workspace-write",
                    "config_sha256": app.runner.digest((home / "config.toml").read_bytes()),
                }),
                  patch.object(app.runner, "call_codex",
                               return_value=SimpleNamespace(returncode=0)),
                  patch.object(app.runner, "resolve_codex_executable",
                               return_value="fake-codex.cmd"),
                  patch.object(app.subprocess, "run",
                               side_effect=fake_subprocess),
                  patch("sys.stdout")):
                status = app.run(Namespace(
                    pilot=str(pilot), output=str(out), repo=str(repo),
                    execute=True,
                ))
            self.assertEqual(status, 0)
            self.assertEqual(len(executed), 1)
            report = json.loads(
                (out / "sanitized-tui-result.json").read_text(encoding="utf-8")
            )
            self.assertTrue(report["functional_and_scope_pass"])
            self.assertFalse(report["worker_delegation_independently_verified"])
            self.assertEqual(report["codex_cli_exit_code"], 0)
            self.assertNotIn("PRIVATE_AUTH_SENTINEL", json.dumps(report))
            self.assertNotIn("raw_model_output", json.dumps(report))
            self.assertTrue((out / "run-started.json").exists())

    def test_no_edit_is_failure_and_not_mislabeled_delegation(self):
        with tempfile.TemporaryDirectory() as name:
            base = Path(name)
            repo = base / "repo"
            repo.mkdir()
            pilot = base / "pilot"
            home = pilot / "baseline-home"
            home.mkdir(parents=True)
            (home / "config.toml").write_text(
                "[agents]\nenabled=true\n", encoding="utf-8")
            out = base / "canary"
            original = subprocess.run
            def fake_subprocess(cmd, **kwargs):
                if cmd[0] == "git" or cmd[0] == sys.executable:
                    return original(cmd, **kwargs)
                return SimpleNamespace(returncode=0)
            with (patch.object(app.runner, "state", return_value={
                    "model": "gpt-6-luna", "reasoning_effort": "medium",
                    "sandbox": "workspace-write",
                    "config_sha256": app.runner.digest((home / "config.toml").read_bytes()),
                }),
                  patch.object(app.runner, "call_codex",
                               return_value=SimpleNamespace(returncode=0)),
                  patch.object(app.runner, "resolve_codex_executable",
                               return_value="fake-codex.cmd"),
                  patch.object(app.subprocess, "run",
                               side_effect=fake_subprocess),
                  patch("sys.stdout")):
                status = app.run(Namespace(
                    pilot=str(pilot), output=str(out), repo=str(repo),
                    execute=True,
                ))
            self.assertEqual(status, 1)
            report = json.loads(
                (out / "sanitized-tui-result.json").read_text(encoding="utf-8")
            )
            self.assertFalse(report["functional_and_scope_pass"])
            self.assertEqual(
                report["verification"]["tracked_modified_file_count"], 0)

    def test_never_approval_override_single_tui_no_admin_flags(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            repo = root / "repo"
            repo.mkdir()
            pilot = root / "pilot"
            home = pilot / "baseline-home"
            home.mkdir(parents=True)
            (home / "config.toml").write_text(
                "approval_policy = 'on-request'\n"
                "[windows]\nsandbox = 'elevated'\n", encoding="utf-8")
            # The sandbox choice is *read*, never changed or promoted.
            before = (home / "config.toml").read_bytes()
            output = root / "isolated-never"
            original = subprocess.run
            calls = []

            def fake_subprocess(cmd, **kwargs):
                if cmd[0] == "git" or cmd[0] == sys.executable:
                    return original(cmd, **kwargs)
                calls.append(cmd)
                self.assertEqual(
                    cmd[cmd.index("--ask-for-approval") + 1], "never")
                self.assertEqual(
                    cmd[cmd.index("--sandbox") + 1], "workspace-write")
                self.assertNotIn("--yolo", cmd)
                self.assertNotIn("danger-full-access", cmd)
                self.assertNotIn("admin", cmd)
                self.assertEqual(
                    Path(kwargs["env"]["CODEX_HOME"]).resolve(), home.resolve())
                self.assertIn("report BLOCKED", cmd[-1])
                work = Path(kwargs["cwd"])
                (work / "total.py").write_text(
                    "def total(lignes):\n"
                    "    return sum(prix * quantite for prix, quantite in lignes)\n",
                    encoding="utf-8")
                return SimpleNamespace(returncode=0)

            with (patch.object(app.runner, "state", return_value={
                    "model": "gpt-6-luna",
                    "reasoning_effort": "medium",
                    "sandbox": "workspace-write",
                    "config_sha256": app.runner.digest(before),
                }),
                  patch.object(app.runner, "call_codex",
                               return_value=SimpleNamespace(returncode=0)),
                  patch.object(app.runner, "resolve_codex_executable",
                               return_value="fake-codex.cmd"),
                  patch.object(app.subprocess, "run", side_effect=fake_subprocess),
                  patch("sys.stdout")):
                status = app.run(Namespace(
                    pilot=str(pilot), output=str(output), repo=str(repo),
                    execute=True, approval="never"))

            self.assertEqual(status, 0)
            self.assertEqual(len(calls), 1)
            self.assertEqual((home / "config.toml").read_bytes(), before)
            report = json.loads(
                (output / "sanitized-tui-result.json").read_text(encoding="utf-8"))
            self.assertEqual(report["approval_policy_override_requested"], "never")
            self.assertEqual(
                report["declared_policy"]["approval_policy"], "on-request")
            self.assertEqual(
                report["declared_policy"]["windows_sandbox"], "elevated")
            self.assertEqual(report["policy_effectiveness"], "not_runtime_attested")
            self.assertFalse(report["worker_delegation_independently_verified"])

    def test_readonly_policy_preflight_reports_no_runtime_attestation(self):
        with tempfile.TemporaryDirectory() as name:
            base = Path(name)
            home = base / "pilot" / "baseline-home"
            home.mkdir(parents=True)
            config = b"[agents]\nenabled=true\n"
            (home / "config.toml").write_bytes(config)
            import io
            printed = io.StringIO()
            with (patch.object(app.runner, "state", return_value={
                    "model": "gpt-6-luna",
                    "reasoning_effort": "medium",
                    "sandbox": "workspace-write",
                    "config_sha256": app.runner.digest(config),
                }),
                patch.object(app.runner, "call_codex",
                             side_effect=AssertionError("preflight must not login")),
                patch("sys.stdout", printed)):
                outcome = app.policy(Namespace(pilot=str(base / "pilot")))
            self.assertEqual(outcome, 0)
            payload = json.loads(printed.getvalue())
            self.assertEqual(payload["model_calls_made"], 0)
            self.assertFalse(payload["effective_runtime_permissions_verified"])
            self.assertEqual(payload["declared_policy"]["windows_sandbox"],
                             "not_declared")
            self.assertEqual(payload["planned_cli_override"]["approval"], "never")

    def test_no_approval_fails_closed_if_sandbox_disabled(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            repo = root / "repo"
            repo.mkdir()
            home = root / "pilot" / "baseline-home"
            home.mkdir(parents=True)
            (home / "config.toml").write_text(
                "[windows]\nsandbox='disabled'\n", encoding="utf-8")
            with (patch.object(app.runner, "state", return_value={
                    "model": "gpt-6-luna",
                    "reasoning_effort": "medium",
                    "sandbox": "workspace-write",
                    "config_sha256": app.runner.digest((home / "config.toml").read_bytes()),
                }),
                  patch.object(app.runner, "call_codex",
                               side_effect=AssertionError("Codex should not start"))):
                with self.assertRaisesRegex(ValueError, "WINDOWS_SANDBOX_DISABLED"):
                    app.run(Namespace(
                        pilot=str(root / "pilot"), output=str(root / "out"),
                        repo=str(repo), execute=True, approval="never"))

    def test_inspect_offline_does_not_launch_codex(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name) / "old-run"
            root.mkdir()
            work = root / "workspace"
            app.runner.make_fixture(work)
            (root / "run-started.json").write_text(
                '{"schema_version":1}', encoding="utf-8")
            with (patch.object(app.runner, "call_codex",
                               side_effect=AssertionError("No Codex allowed")),
                  patch("sys.stdout")):
                status = app.inspect(Namespace(output=str(root)))
            self.assertEqual(status, 0)


if __name__ == "__main__":
    unittest.main()

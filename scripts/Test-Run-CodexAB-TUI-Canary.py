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
    def test_redacted_drift_reports_fixed_categories_without_dynamic_keys(self):
        old = {
            "tool_output_token_limit": 4000,
            "agents": {"luna-medium": {"config_file": "agents/luna-medium.toml"}},
        }
        new = {
            "tool_output_token_limit": 4000,
            "agents": {"luna-medium": {"config_file": "agents/luna-medium.toml"}},
            "windows": {"sandbox": "elevated"},
            "projects": {"C:/PRIVATE/SECRET_PROJECT_PATH": {"trust_level": "trusted"}},
            "notice": {"hidden_SECRET_NOTICE": True},
            "mcp_servers": {"PRIVATE_MCP_NAME": {"token": "PRIVATE_TOKEN"}},
            "private_secret_key_CANNOT_LEAK": "private_secret_value_CANNOT_LEAK",
        }
        categories = app.safe_config_drift_categories(old, new)
        self.assertEqual(categories, sorted([
            "windows.sandbox", "projects[*]", "notice[*]",
            "mcp_servers[*]", "other_config_key",
        ]))
        output = json.dumps(categories)
        for private in (
            "SECRET_PROJECT_PATH", "hidden_SECRET_NOTICE", "PRIVATE_MCP_NAME",
            "PRIVATE_TOKEN", "private_secret_key_CANNOT_LEAK",
            "private_secret_value_CANNOT_LEAK",
        ):
            self.assertNotIn(private, output)

    def test_readonly_diagnose_emits_only_categories_when_reference_is_intact(self):
        import io
        with tempfile.TemporaryDirectory() as name:
            pilot = Path(name) / "pilot"
            base = pilot / "baseline-home"
            cand = pilot / "candidate-home"
            base.mkdir(parents=True)
            cand.mkdir()
            original = b"tool_output_token_limit = 4000\n[agents]\nenabled = true\n"
            changed = (
                original
                + b'[windows]\nsandbox = "elevated"\n'
                + b'[projects."C:/PRIVATE/DO_NOT_SHOW"]\ntrust_level = "trusted"\n'
            )
            (base / "config.toml").write_bytes(changed)
            (cand / "config.toml").write_bytes(original)
            (base / "AGENTS.md").write_bytes(b"baseline")
            (cand / "AGENTS.md").write_bytes(b"candidate")
            data = {
                "schema_version": 1,
                "candidate_commit": app.runner.COMMIT,
                "baseline_sha256": app.runner.digest(b"baseline"),
                "candidate_sha256": app.runner.digest(b"candidate"),
                "config_sha256": app.runner.digest(original),
                "cli_version": "codex-cli 0.164.0",
            }
            (pilot / "benchmark-state.json").write_text(
                json.dumps(data), encoding="utf-8")
            output = io.StringIO()
            with (patch.object(
                        app.runner, "call_codex",
                        return_value=SimpleNamespace(returncode=0,
                                                     stdout="codex-cli 0.164.0\n")),
                  patch("sys.stdout", output)):
                status = app.diagnose(Namespace(pilot=str(pilot)))
            self.assertEqual(status, 0)
            report = json.loads(output.getvalue())
            self.assertEqual(report["redacted_config_drift_categories"],
                             ["projects[*]", "windows.sandbox"])
            self.assertFalse(report["preflight_ready"])
            self.assertFalse(report["mxc_sandbox_drift_eligible"])
            self.assertEqual(report["model_calls_made"], 0)
            self.assertNotIn("DO_NOT_SHOW", output.getvalue())
            self.assertNotIn(str(pilot), output.getvalue())

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

    def test_config_drift_classification_is_boolean_and_readonly(self):
        import io
        with tempfile.TemporaryDirectory() as name:
            root = Path(name) / "pilot"
            baseline = root / "baseline-home"
            candidate = root / "candidate-home"
            baseline.mkdir(parents=True)
            candidate.mkdir()
            base_agents = b"SECRET_BASE_AGENTS"
            cand_agents = b"SECRET_CAND_AGENTS"
            original_config = b"tool_output_token_limit = 4000\n"
            changed_config = b"tool_output_token_limit = 4500\n"
            (baseline / "AGENTS.md").write_bytes(base_agents)
            (candidate / "AGENTS.md").write_bytes(cand_agents)
            (baseline / "config.toml").write_bytes(changed_config)
            (candidate / "config.toml").write_bytes(original_config)
            state_data = {
                "schema_version": 1, "candidate_commit": app.runner.COMMIT,
                "baseline_sha256": app.runner.digest(base_agents),
                "candidate_sha256": app.runner.digest(cand_agents),
                "config_sha256": app.runner.digest(original_config),
                "cli_version": "codex-cli 0.164.0",
            }
            (root / "benchmark-state.json").write_text(
                json.dumps(state_data), encoding="utf-8")
            def inspect():
                output = io.StringIO()
                with (patch.object(app.runner, "call_codex",
                       return_value=SimpleNamespace(
                           returncode=0, stdout="codex-cli 0.164.0\n")),
                      patch("sys.stdout", output)):
                    self.assertEqual(
                        app.diagnose(Namespace(pilot=str(root))), 0)
                report = json.loads(output.getvalue())
                for secret in ("SECRET_BASE_AGENTS", "SECRET_CAND_AGENTS",
                               "tool_output_token_limit", str(root)):
                    self.assertNotIn(secret, output.getvalue())
                self.assertEqual(report["model_calls_made"], 0)
                return report
            report = inspect()
            self.assertFalse(report["routing_config_match"])
            self.assertFalse(report["baseline_candidate_config_bytes_match"])
            self.assertFalse(report["baseline_candidate_config_semantics_match"])
            self.assertTrue(report["candidate_config_matches_record"])
            self.assertFalse(report["preflight_ready"])

            # Shared drift is NOT a justification for accepting either file.
            (candidate / "config.toml").write_bytes(changed_config)
            report = inspect()
            self.assertTrue(report["baseline_candidate_config_bytes_match"])
            self.assertTrue(report["baseline_candidate_config_semantics_match"])
            self.assertFalse(report["candidate_config_matches_record"])
            self.assertFalse(report["preflight_ready"])

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

    @unittest.skipUnless(os.name == "nt", "MXC override only supported on Windows")
    def test_explicit_mxc_override_is_one_shot_and_keeps_config_unchanged(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            repo = root / "repo"
            repo.mkdir()
            pilot = root / "pilot"
            home = pilot / "baseline-home"
            home.mkdir(parents=True)
            config = b"[agents]\nenabled=true\n"
            (home / "config.toml").write_bytes(config)
            output = root / "mxc"
            calls = []
            original = subprocess.run

            def fake_subprocess(cmd, **kwargs):
                if cmd[0] == "git" or cmd[0] == sys.executable:
                    return original(cmd, **kwargs)
                calls.append(cmd)
                self.assertIn("windows.sandbox=mxc", cmd)
                self.assertEqual(cmd.count("windows.sandbox=mxc"), 1)
                self.assertEqual(cmd[cmd.index("--sandbox") + 1],
                                 "workspace-write")
                self.assertEqual(cmd[cmd.index("--ask-for-approval") + 1],
                                 "never")
                self.assertEqual(cmd[0], "fake-codex.cmd")
                self.assertNotIn("--yolo", cmd)
                self.assertNotIn("danger-full-access", cmd)
                self.assertEqual(Path(kwargs["env"]["CODEX_HOME"]).resolve(),
                                 home.resolve())
                work = Path(kwargs["cwd"])
                (work / "total.py").write_text(
                    "def total(lignes):\n"
                    "    return sum(prix * quantite for prix, quantite in lignes)\n",
                    encoding="utf-8")
                return SimpleNamespace(returncode=0)

            with (patch.object(app.runner, "state", return_value={
                    "model": "gpt-6-luna", "reasoning_effort": "medium",
                    "sandbox": "workspace-write",
                    "config_sha256": app.runner.digest(config),
                }),
                  patch.object(app.runner, "call_codex",
                               return_value=SimpleNamespace(returncode=0)),
                  patch.object(app.runner, "resolve_codex_executable",
                               return_value="fake-codex.cmd"),
                  patch.object(app.subprocess, "run", side_effect=fake_subprocess),
                  patch("sys.stdout")):
                status = app.run(Namespace(
                    pilot=str(pilot), output=str(output), repo=str(repo),
                    execute=True, approval="never", windows_sandbox="mxc"))

            self.assertEqual(status, 0)
            self.assertEqual(len(calls), 1)
            self.assertEqual((home / "config.toml").read_bytes(), config)
            result = json.loads(
                (output / "sanitized-tui-result.json").read_text(encoding="utf-8"))
            self.assertEqual(result["windows_sandbox_override_requested"], "mxc")
            self.assertEqual(result["approval_policy_override_requested"], "never")
            self.assertTrue(result["functional_and_scope_pass"])
            self.assertFalse(result["worker_delegation_independently_verified"])

    def test_sandbox_key_drift_validator_preserves_candidate_and_baseline(self):
        with tempfile.TemporaryDirectory() as name:
            pilot = Path(name) / "pilot"
            original_home = pilot / "candidate-home"
            changed_home = pilot / "baseline-home"
            original_home.mkdir(parents=True)
            changed_home.mkdir()
            original = b"tool_output_token_limit = 4000\n[agents]\nenabled = true\n"
            changed = original + b'[windows]\nsandbox = "elevated"\n'
            (original_home / "config.toml").write_bytes(original)
            (changed_home / "config.toml").write_bytes(changed)
            expected = {"config_sha256": app.runner.digest(original)}
            before = ((original_home / "config.toml").read_bytes(),
                      (changed_home / "config.toml").read_bytes())
            with self.assertRaisesRegex(
                    ValueError, "ISOLATED_CONFIG_HASH_MISMATCH"):
                app.validate_baseline_config_snapshot(pilot, expected)
            self.assertEqual(
                app.validate_baseline_config_snapshot(
                    pilot, expected, allow_sandbox_key_drift=True),
                "opt_in_sandbox_key_or_format_drift")
            self.assertEqual(
                ((original_home / "config.toml").read_bytes(),
                 (changed_home / "config.toml").read_bytes()), before)

    def test_unsafe_config_drift_fails_closed_and_does_not_rebaseline(self):
        with tempfile.TemporaryDirectory() as name:
            pilot = Path(name) / "pilot"
            original_home = pilot / "candidate-home"
            changed_home = pilot / "baseline-home"
            original_home.mkdir(parents=True)
            changed_home.mkdir()
            original = b"tool_output_token_limit = 4000\n[agents]\nenabled = true\n"
            expected = {"config_sha256": app.runner.digest(original)}
            (original_home / "config.toml").write_bytes(original)
            for bad in (
                original.replace(b"true", b"false"),
                original + b'[windows]\nsandbox = "unelevated"\n',
                original + b'[windows]\nsandbox = "disabled"\n',
                original + b'[windows]\nsandbox = "mxc"\n[projects.x]\ntrust_level = "trusted"\n',
                original + b'approval_policy = "never"\n',
            ):
                (changed_home / "config.toml").write_bytes(bad)
                with self.assertRaisesRegex(
                        ValueError, "ISOLATED_CONFIG_DRIFT_NOT_ALLOWLISTED"):
                    app.validate_baseline_config_snapshot(
                        pilot, expected, allow_sandbox_key_drift=True)
            (changed_home / "config.toml").write_bytes(
                original + b'[windows]\nsandbox = "mxc"\n')
            (original_home / "config.toml").write_bytes(
                original.replace(b"4000", b"6000"))
            with self.assertRaisesRegex(
                    ValueError, "ORIGINAL_CANDIDATE_CONFIG_CHANGED"):
                app.validate_baseline_config_snapshot(
                    pilot, expected, allow_sandbox_key_drift=True)

    @unittest.skipUnless(os.name == "nt", "MXC canary runs only on Windows")
    def test_one_shot_mxc_tui_accepts_only_sandbox_drift_with_explicit_optin(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            repo = root / "repo"
            repo.mkdir()
            pilot = root / "pilot"
            home = pilot / "baseline-home"
            candidate = pilot / "candidate-home"
            home.mkdir(parents=True)
            candidate.mkdir()
            clean = b"tool_output_token_limit = 4000\n[agents]\nenabled = true\n"
            (candidate / "config.toml").write_bytes(clean)
            changed = clean + b'[windows]\nsandbox = "elevated"\n'
            (home / "config.toml").write_bytes(changed)
            original = subprocess.run
            launches = []

            def fake_run(cmd, **kwargs):
                if cmd[0] in ("git", sys.executable):
                    return original(cmd, **kwargs)
                launches.append(cmd)
                self.assertEqual(cmd[cmd.index("--ask-for-approval") + 1],
                                 "never")
                self.assertEqual(cmd[cmd.index("--sandbox") + 1],
                                 "workspace-write")
                self.assertIn("windows.sandbox=mxc", cmd)
                self.assertNotIn("danger-full-access", cmd)
                workspace = Path(kwargs["cwd"])
                (workspace / "total.py").write_text(
                    "def total(lignes):\n"
                    "    return sum(prix * quantite for prix, quantite in lignes)\n",
                    encoding="utf-8")
                return SimpleNamespace(returncode=0)

            with (patch.object(app.runner, "state", return_value={
                    "model": "gpt-6-luna", "reasoning_effort": "medium",
                    "sandbox": "workspace-write",
                    "config_sha256": app.runner.digest(clean),
                }),
                  patch.object(app.runner, "call_codex",
                               return_value=SimpleNamespace(returncode=0)),
                  patch.object(app.runner, "resolve_codex_executable",
                               return_value="fake-codex.cmd"),
                  patch.object(app.subprocess, "run", side_effect=fake_run),
                  patch("sys.stdout")):
                status = app.run(Namespace(
                    pilot=str(pilot), output=str(root / "canary"), repo=str(repo),
                    approval="never", windows_sandbox="mxc",
                    accept_sandbox_key_drift=True, execute=True))
            self.assertEqual(status, 0)
            self.assertEqual(len(launches), 1)
            self.assertEqual((home / "config.toml").read_bytes(), changed)
            self.assertEqual((candidate / "config.toml").read_bytes(), clean)
            report = json.loads(
                (root / "canary" / "sanitized-tui-result.json").read_text(encoding="utf-8"))
            self.assertEqual(report["baseline_config_snapshot_check"],
                             "opt_in_sandbox_key_or_format_drift")
            self.assertTrue(report["functional_and_scope_pass"])

    def test_drift_flag_without_never_mxc_refused_before_model_call(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            repo = root / "repo"
            repo.mkdir()
            pilot = root / "pilot"
            pilot.mkdir()
            with patch.object(app.runner, "state", return_value={}):
                for approval, sandbox in (("on-request", "mxc"),
                                          ("never", None)):
                    with self.assertRaisesRegex(
                            ValueError, "CONFIG_DRIFT_FLAG_REQUIRES_MXC_NEVER"):
                        app.run(Namespace(
                            pilot=str(pilot), output=str(root / "never-created"),
                            repo=str(repo), execute=True, approval=approval,
                            windows_sandbox=sandbox, accept_sandbox_key_drift=True))
            self.assertFalse((root / "never-created").exists())

    def test_invalid_windows_sandbox_override_fails_before_launch(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            repo = root / "repo"
            repo.mkdir()
            pilot = root / "pilot"
            home = pilot / "baseline-home"
            home.mkdir(parents=True)
            (home / "config.toml").write_text("[agents]\nenabled=true\n",
                                               encoding="utf-8")
            with (patch.object(app.runner, "state", return_value={
                    "model": "gpt-6-luna", "reasoning_effort": "medium",
                    "sandbox": "workspace-write",
                }), patch.object(app.runner, "call_codex",
                                 side_effect=AssertionError("no CLI calls"))):
                with self.assertRaisesRegex(
                        ValueError, "WINDOWS_SANDBOX_OVERRIDE_UNSUPPORTED"):
                    app.run(Namespace(
                        pilot=str(pilot), output=str(root / "out"),
                        repo=str(repo), execute=True, approval="never",
                        windows_sandbox="disabled"))
            self.assertFalse((root / "out").exists())

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

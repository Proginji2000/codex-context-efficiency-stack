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

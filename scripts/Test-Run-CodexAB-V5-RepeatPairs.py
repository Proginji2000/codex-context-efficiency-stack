#!/usr/bin/env python3
"""Synthetic, offline-only repeat A/B qualification tests (zero Codex model calls)."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from argparse import Namespace
from types import SimpleNamespace
from unittest.mock import Mock, patch

SOURCE = Path(__file__).with_name("Run-CodexAB-V5-RepeatPairs.py")
SPEC = importlib.util.spec_from_file_location("codex_repeat_pairs", SOURCE)
app = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(app)


class RepeatPairsTests(unittest.TestCase):
    def create(self, root):
        pilot = root / "pilot"
        repo = root / "repo"
        (pilot / "baseline-home").mkdir(parents=True)
        (pilot / "candidate-home").mkdir(parents=True)
        repo.mkdir()
        data = b"tool_output_token_limit = 4000\n"
        for arm in ("baseline", "candidate"):
            (pilot / (arm + "-home") / "config.toml").write_bytes(data)
        state = {"config_sha256": hashlib.sha256(data).hexdigest()}
        runner = SimpleNamespace(
            digest=lambda b: hashlib.sha256(b).hexdigest(),
            read_file=lambda path: path.read_bytes(),
        )
        tui = SimpleNamespace(runner=runner)
        return pilot, repo, state, tui

    def args(self, pilot, repo, out_base, **values):
        params = dict(
            pilot=str(pilot), repo=str(repo), output_base=str(out_base),
            codex_cli="C:/Dev/codex-cli-0165/node_modules/.bin/codex.cmd",
            start_pair=2, pairs=2, execute=True, audited_restore=True,
        )
        params.update(values)
        return Namespace(**params)

    def test_pair02_reversed_pair03_original_order(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            pilot, repo, _, _ = self.create(root)
            _, _, planned = app.paths(pilot, repo, root / "trial", (2, 3))
            self.assertEqual([(pair, arm) for pair, arm, _ in planned], [
                (2, "candidate"), (2, "baseline"),
                (3, "baseline"), (3, "candidate"),
            ])
            self.assertEqual(len(set(str(o) for _, _, o in planned)), 4)

    def test_one_arm_drift_detected_and_both_drift_fail_closed(self):
        with tempfile.TemporaryDirectory() as name:
            pilot, repo, state, tui = self.create(Path(name))
            self.assertIsNone(app.restoration_target(tui, pilot, state))
            (pilot / "candidate-home" / "config.toml").write_bytes(b"changed\n")
            self.assertEqual(app.restoration_target(tui, pilot, state), "candidate")
            (pilot / "candidate-home" / "config.toml").write_bytes(
                b"tool_output_token_limit = 4000\n")
            (pilot / "baseline-home" / "config.toml").write_bytes(b"changed\n")
            self.assertEqual(app.restoration_target(tui, pilot, state), "baseline")
            (pilot / "candidate-home" / "config.toml").write_bytes(b"changed\n")
            with self.assertRaisesRegex(ValueError, "BOTH_CONFIGS_DRIFTED"):
                app.restoration_target(tui, pilot, state)

    def test_plan_no_restoration_and_no_model(self):
        with tempfile.TemporaryDirectory() as name:
            pilot, repo, state, tui = self.create(Path(name))
            calls = []
            tui.validate_paths = Mock()
            with (patch.object(app, "contexts", return_value=(tui, None, None)),
                  patch.object(app, "check_cli_and_homes", return_value=state),
                  patch.object(app, "restoration_target", return_value="candidate"),
                  patch.object(app, "preflight", side_effect=AssertionError("NO_PREFLIGHT")),
                  patch.object(app, "restore_one", side_effect=AssertionError("NO_RESTORE")),
                  contextlib.redirect_stdout(io.StringIO()) as out):
                rc = app.run(self.args(pilot, repo, Path(name) / "trial",
                                       execute=False))
            self.assertEqual(rc, 0)
            self.assertIn("PLAN_ONLY: no model calls", out.getvalue())
            self.assertEqual(tui.validate_paths.call_count, 4)

    def test_explicit_restore_optin_mandatory_before_model(self):
        with tempfile.TemporaryDirectory() as name:
            pilot, repo, state, tui = self.create(Path(name))
            tui.validate_paths = Mock()
            tui.run = Mock(side_effect=AssertionError("MODEL_MUST_NOT_RUN"))
            with (patch.object(app, "contexts", return_value=(tui, None, None)),
                  patch.object(app, "check_cli_and_homes", return_value=state),
                  patch.object(app, "restoration_target", return_value=None),
                  contextlib.redirect_stdout(io.StringIO())):
                with self.assertRaisesRegex(ValueError, "EXPLICIT_AUDITED_RESTORE_REQUIRED"):
                    app.run(self.args(pilot, repo, Path(name) / "trial",
                                          audited_restore=False))
            tui.run.assert_not_called()

    def test_four_legs_strict_sequence_and_only_four_model_calls(self):
        with tempfile.TemporaryDirectory() as name:
            pilot, repo, state, tui = self.create(Path(name))
            call_log = []
            tui.validate_paths = Mock()
            def fake_run(namespace):
                call_log.append(("run", namespace.arm, Path(namespace.output).name,
                                 namespace.approval, namespace.windows_sandbox,
                                 namespace.python_test_fallback_hint))
                return 0
            tui.run = fake_run
            def fake_preflight(_tui, _pilot):
                call_log.append(("preflight",))
            def fake_restore(_tui, _restorers, _pilot, _state, pair, arm, allowed):
                self.assertTrue(allowed)
                call_log.append(("restore", pair, arm))
            with (patch.object(app, "contexts", return_value=(tui, None, None)),
                  patch.object(app, "check_cli_and_homes", return_value=state),
                  patch.object(app, "restoration_target", return_value=None),
                  patch.object(app, "restore_one", side_effect=fake_restore),
                  patch.object(app, "preflight", side_effect=fake_preflight),
                  patch.object(app, "verify_report", side_effect=lambda t, out, arm: {
                      "arm": arm, "pass": True}),
                  contextlib.redirect_stdout(io.StringIO()) as out):
                rc = app.run(self.args(pilot, repo, Path(name) / "trial"))
            self.assertEqual(rc, 0)
            arms = [v[1] for v in call_log if v[0] == "run"]
            self.assertEqual(arms, ["candidate", "baseline", "baseline", "candidate"])
            self.assertEqual(sum(v[0] == "preflight" for v in call_log), 4)
            self.assertEqual(sum(v[0] == "restore" for v in call_log), 4)
            for item in call_log:
                if item[0] == "run":
                    self.assertEqual(item[3:], ("never", "mxc", True))
            self.assertIn("EXPERIMENTAL_REPEATS_PASS", out.getvalue())

    def test_first_trial_failure_stops_all_following_runs(self):
        with tempfile.TemporaryDirectory() as name:
            pilot, repo, state, tui = self.create(Path(name))
            tui.validate_paths = Mock()
            tui.run = Mock(return_value=1)
            with (patch.object(app, "contexts", return_value=(tui, None, None)),
                  patch.object(app, "check_cli_and_homes", return_value=state),
                  patch.object(app, "restoration_target", return_value=None),
                  patch.object(app, "restore_one"),
                  patch.object(app, "preflight"),
                  patch.object(app, "verify_report", side_effect=AssertionError("NO_VERIFICATION")),
                  contextlib.redirect_stdout(io.StringIO())):
                with self.assertRaisesRegex(ValueError, "RUN_FAILED_P02_CANDIDATE"):
                    app.run(self.args(pilot, repo, Path(name) / "trial"))
            tui.run.assert_called_once()

    def test_existing_second_output_blocks_entire_batch_before_model(self):
        with tempfile.TemporaryDirectory() as name:
            pilot, repo, state, tui = self.create(Path(name))
            already = Path(name) / "trial-pair03-candidate"
            already.mkdir()
            def validate(_pilot, output, _repo):
                if Path(output).exists():
                    raise ValueError("UNSAFE_OR_EXISTING_OUTPUT")
            tui.validate_paths = Mock(side_effect=validate)
            tui.run = Mock(side_effect=AssertionError("NO_MODEL"))
            with (patch.object(app, "contexts", return_value=(tui, None, None)),
                  patch.object(app, "check_cli_and_homes", return_value=state),
                  patch.object(app, "restoration_target", return_value=None),
                  contextlib.redirect_stdout(io.StringIO())):
                with self.assertRaisesRegex(ValueError, "UNSAFE_OR_EXISTING_OUTPUT"):
                    app.run(self.args(pilot, repo, Path(name) / "trial"))
            tui.run.assert_not_called()

    def test_final_report_rechecked_independently_without_model(self):
        with tempfile.TemporaryDirectory() as name:
            output = Path(name) / "out"
            output.mkdir()
            details = {k: True for k in app.REQUIRED_CHECKS}
            details["unittest_exit_code"] = 0
            report = {
                "arm": "candidate", "prompt_contract": app.CONTRACT,
                "model": "gpt-6-luna",
                "windows_sandbox_override_requested": "mxc",
                "approval_policy_override_requested": "never",
                "codex_cli_exit_code": 0,
                "functional_and_scope_pass": True,
                "verification": details.copy(), "elapsed_s": 50,
            }
            (output / "sanitized-tui-result.json").write_text(json.dumps(report))
            runner = SimpleNamespace(verification_detail=Mock(return_value=details))
            tui = SimpleNamespace(runner=runner)
            record = app.verify_report(tui, output, "candidate")
            self.assertTrue(record["pass"])
            report["verification"]["git_diff_check_pass"] = False
            (output / "sanitized-tui-result.json").write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, "REPORT_REINSPECTION_MISMATCH"):
                app.verify_report(tui, output, "candidate")
            self.assertEqual(runner.verification_detail.call_count, 2)

    def test_version_mismatch_rejected_before_home_access(self):
        with tempfile.TemporaryDirectory() as dirname:
            cli = Path(dirname) / "codex.cmd"
            cli.write_text("placeholder")
            fake = SimpleNamespace(
                runner=SimpleNamespace(
                    resolve_codex_executable=Mock(return_value=str(cli)),
                    call_codex=Mock(return_value=SimpleNamespace(
                        returncode=0, stdout="codex-cli 0.164.0\n")),
                    state=Mock(),
                ))
            with self.assertRaisesRegex(ValueError, "PINNED_CLI_VERSION_MISMATCH"):
                app.check_cli_and_homes(fake, Path("unreadable"), cli)
            fake.runner.state.assert_not_called()

    def test_cli_path_mismatch_stops_before_running_models(self):
        with tempfile.TemporaryDirectory() as dirname:
            cli = Path(dirname) / "codex.cmd"
            cli.write_text("placeholder")
            wrong = Path(dirname) / "untrusted.cmd"
            wrong.write_text("other")
            fake = SimpleNamespace(runner=SimpleNamespace(
                resolve_codex_executable=Mock(return_value=str(wrong)),
                call_codex=Mock(side_effect=AssertionError("NO_CLI_CALL")),
            ))
            with self.assertRaisesRegex(ValueError, "ISOLATED_CLI_PATH_MISMATCH"):
                app.check_cli_and_homes(fake, Path("unused"), cli)
            fake.runner.call_codex.assert_not_called()


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Deterministic offline tests; never run a Codex model or copy auth."""
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

P = Path(__file__).with_name("Restore-CodexAB-IsolatedBaseline.py")
SPEC = importlib.util.spec_from_file_location("codex_ab_restore", P)
app = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(app)


class RestoreTests(unittest.TestCase):
    def fixture(self, root):
        pilot = root / "pilot"
        baseline = pilot / "baseline-home"
        candidate = pilot / "candidate-home"
        baseline.mkdir(parents=True)
        candidate.mkdir()
        canonical = b"tool_output_token_limit = 4000\n[agents]\nenabled = true\n"
        changed = (
            canonical + b'[windows]\nsandbox = "elevated"\n'
            + b'[projects."C:/PRIVATE/WORKSPACE"]\ntrust_level = "trusted"\n'
            + b'[notice]\nhide_model_migration_prompt = "private-marker"\n'
        )
        (baseline / "config.toml").write_bytes(changed)
        (candidate / "config.toml").write_bytes(canonical)
        (baseline / "auth.json").write_bytes(b"NEVER_COPIED_PRIVATE_AUTH")
        (baseline / "AGENTS.md").write_bytes(b"original-baseline-agents")
        (candidate / "AGENTS.md").write_bytes(b"candidate-agents")
        state = {
            "model": "gpt-6-luna",
            "schema_version": 1,
            "config_sha256": app.runner.digest(canonical),
        }
        return pilot, baseline, candidate, canonical, changed, state

    def test_requires_optin_before_reading_files(self):
        with patch.object(app.runner, "state", side_effect=AssertionError("called")):
            with self.assertRaisesRegex(ValueError, "EXPLICIT_RESTORE_REQUIRED"):
                app.restore("missing", "backup-test", execute=False)

    def test_backup_then_restore_original_config_without_losing_auth(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            pilot, baseline, candidate, canonical, changed, state = self.fixture(root)
            buf = io.StringIO()
            with (patch.object(app.runner, "state", return_value=state),
                  patch("sys.stdout", buf)):
                code = app.restore(pilot, "backup-mxc-recovery", execute=True)
            self.assertEqual(code, 0)
            self.assertEqual((baseline / "config.toml").read_bytes(), canonical)
            self.assertEqual((candidate / "config.toml").read_bytes(), canonical)
            self.assertEqual((baseline / "auth.json").read_bytes(),
                             b"NEVER_COPIED_PRIVATE_AUTH")
            self.assertEqual((baseline / "AGENTS.md").read_bytes(),
                             b"original-baseline-agents")
            backup = pilot / "audit-backups" / "backup-mxc-recovery"
            self.assertEqual(
                (backup / "baseline-config-before-restore.toml").read_bytes(),
                changed)
            report = json.loads(buf.getvalue())
            self.assertEqual(report["status"], "RESTORED")
            self.assertEqual(report["codex_model_calls"], 0)
            self.assertFalse(report["credentials_copied"])
            audit = json.loads((backup / "restore-audit.json").read_text())
            self.assertEqual(audit["previous_baseline_sha256"],
                             app.runner.digest(changed))
            self.assertEqual(audit["restored_sha256"],
                             app.runner.digest(canonical))
            for private in ("PRIVATE/WORKSPACE", "private-marker",
                            "NEVER_COPIED_PRIVATE_AUTH", str(root)):
                self.assertNotIn(private, buf.getvalue())
            with patch.object(app.runner, "state", return_value=state):
                with self.assertRaisesRegex(ValueError, "BACKUP_ALREADY_EXISTS"):
                    app.restore(pilot, "backup-mxc-recovery", execute=True)

    def test_refuses_changed_candidate_and_does_not_touch_baseline(self):
        with tempfile.TemporaryDirectory() as name:
            pilot, baseline, candidate, canonical, changed, state = self.fixture(
                Path(name))
            (candidate / "config.toml").write_text(
                'approval_policy = "never"\n', encoding="utf-8")
            with patch.object(app.runner, "state", return_value=state):
                with self.assertRaisesRegex(ValueError, "ORIGINAL_CONFIG_MISMATCH"):
                    app.restore(pilot, "backup-should-not-exist", execute=True)
            self.assertEqual((baseline / "config.toml").read_bytes(), changed)
            self.assertFalse((pilot / "audit-backups").exists())

    def test_rejects_invalid_label_and_unparseable_baseline(self):
        with tempfile.TemporaryDirectory() as name:
            pilot, baseline, candidate, canonical, changed, state = self.fixture(
                Path(name))
            with patch.object(app.runner, "state", return_value=state):
                for label in ("../outside", "backup-PRIVATE/path", "other"):
                    with self.assertRaisesRegex(ValueError, "INVALID_BACKUP_LABEL"):
                        app.restore(pilot, label, execute=True)
                (baseline / "config.toml").write_bytes(b"bad = [not-valid")
                with self.assertRaisesRegex(
                        ValueError, "BASELINE_CONFIG_NOT_PARSEABLE"):
                    app.restore(pilot, "backup-invalid", execute=True)
            self.assertFalse((pilot / "audit-backups").exists())


if __name__ == "__main__":
    unittest.main()

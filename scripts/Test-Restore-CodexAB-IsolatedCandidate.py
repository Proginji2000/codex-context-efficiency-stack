#!/usr/bin/env python3
"""Offline candidate-only TOML restore tests: no Codex model calls or auth writes."""
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

P = Path(__file__).with_name("Restore-CodexAB-IsolatedCandidate.py")
SPEC = importlib.util.spec_from_file_location("codex_ab_candidate_restore", P)
app = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(app)


class CandidateRestoreTests(unittest.TestCase):
    def fixture(self, root):
        pilot = root / "pilot"
        baseline = pilot / "baseline-home"
        candidate = pilot / "candidate-home"
        baseline.mkdir(parents=True)
        candidate.mkdir()
        original = b"tool_output_token_limit = 4000\n[agents]\nenabled = true\n"
        changed = (original
                   + b'[projects."C:/PRIVATE/CANDIDATE"]\ntrust_level = "trusted"\n'
                   + b'[notice]\nhidden_private_marker = true\n')
        (baseline / "config.toml").write_bytes(original)
        (candidate / "config.toml").write_bytes(changed)
        (candidate / "auth.json").write_bytes(b"PRIVATE_CANDIDATE_AUTH_UNTOUCHED")
        (baseline / "auth.json").write_bytes(b"PRIVATE_BASELINE_AUTH_UNTOUCHED")
        (baseline / "AGENTS.md").write_bytes(b"BASELINE_AGENT_UNTOUCHED")
        (candidate / "AGENTS.md").write_bytes(b"CANDIDATE_AGENT_UNTOUCHED")
        state = {"schema_version": 1, "model": "gpt-6-luna",
                 "config_sha256": app.runner.digest(original)}
        return pilot, baseline, candidate, original, changed, state

    def test_explicit_execute_required_without_any_reads(self):
        with patch.object(app.runner, "state", side_effect=AssertionError("NO_READ")):
            with self.assertRaisesRegex(ValueError, "EXPLICIT_RESTORE_REQUIRED"):
                app.restore("unused", "backup-one", execute=False)

    def test_archives_candidate_and_preserves_credentials(self):
        with tempfile.TemporaryDirectory() as dirname:
            pilot, baseline, candidate, original, changed, state = self.fixture(Path(dirname))
            out = io.StringIO()
            with (patch.object(app.runner, "state", return_value=state),
                  patch("sys.stdout", out)):
                self.assertEqual(app.restore(pilot, "backup-candidate-v1", execute=True), 0)
            self.assertEqual((baseline / "config.toml").read_bytes(), original)
            self.assertEqual((candidate / "config.toml").read_bytes(), original)
            self.assertEqual((candidate / "auth.json").read_bytes(),
                             b"PRIVATE_CANDIDATE_AUTH_UNTOUCHED")
            self.assertEqual((baseline / "auth.json").read_bytes(),
                             b"PRIVATE_BASELINE_AUTH_UNTOUCHED")
            self.assertEqual((candidate / "AGENTS.md").read_bytes(),
                             b"CANDIDATE_AGENT_UNTOUCHED")
            self.assertEqual((baseline / "AGENTS.md").read_bytes(),
                             b"BASELINE_AGENT_UNTOUCHED")
            backup = pilot / "audit-backups" / "backup-candidate-v1"
            self.assertEqual((backup / "candidate-config-before-restore.toml").read_bytes(),
                             changed)
            report = json.loads(out.getvalue())
            self.assertEqual(report["status"], "RESTORED")
            self.assertTrue(report["candidate_matches_recorded_original"])
            self.assertTrue(report["baseline_original_unchanged"])
            self.assertFalse(report["credentials_copied"])
            self.assertEqual(report["codex_model_calls"], 0)
            audit = json.loads((backup / "restore-audit.json").read_text())
            self.assertEqual(audit["previous_candidate_sha256"], app.runner.digest(changed))
            self.assertEqual(audit["restored_sha256"], app.runner.digest(original))
            for private in ("PRIVATE_CANDIDATE_AUTH", "PRIVATE_BASELINE_AUTH",
                            "PRIVATE/CANDIDATE", str(dirname)):
                self.assertNotIn(private, out.getvalue())

    def test_refuses_drifted_reference_before_writing_backup(self):
        with tempfile.TemporaryDirectory() as dirname:
            pilot, baseline, candidate, original, changed, state = self.fixture(Path(dirname))
            (baseline / "config.toml").write_bytes(original + b" \n")
            with patch.object(app.runner, "state", return_value=state):
                with self.assertRaisesRegex(ValueError, "REFERENCE_BASELINE_CONFIG_MISMATCH"):
                    app.restore(pilot, "backup-ref-invalid", execute=True)
            self.assertFalse((pilot / "audit-backups").exists())
            self.assertEqual((candidate / "config.toml").read_bytes(), changed)

    def test_idempotence_and_non_overwrite_backup(self):
        with tempfile.TemporaryDirectory() as dirname:
            pilot, baseline, candidate, original, changed, state = self.fixture(Path(dirname))
            with (patch.object(app.runner, "state", return_value=state),
                  patch("sys.stdout", io.StringIO())):
                app.restore(pilot, "backup-candidate-run", execute=True)
                with self.assertRaisesRegex(ValueError, "NO_RESTORE_NEEDED"):
                    app.restore(pilot, "backup-other", execute=True)
                (candidate / "config.toml").write_bytes(changed)
                with self.assertRaisesRegex(ValueError, "BACKUP_ALREADY_EXISTS"):
                    app.restore(pilot, "backup-candidate-run", execute=True)
            self.assertEqual(
                (pilot / "audit-backups" / "backup-candidate-run" /
                 "candidate-config-before-restore.toml").read_bytes(), changed)
            self.assertEqual((candidate / "config.toml").read_bytes(), changed)

    def test_invalid_label_and_invalid_candidate_toml_do_not_write(self):
        with tempfile.TemporaryDirectory() as dirname:
            pilot, baseline, candidate, original, changed, state = self.fixture(Path(dirname))
            with patch.object(app.runner, "state", return_value=state):
                for label in ("outside", "../outside", "backup-PRIVATE/path"):
                    with self.assertRaisesRegex(ValueError, "INVALID_BACKUP_LABEL"):
                        app.restore(pilot, label, execute=True)
                (candidate / "config.toml").write_bytes(b"bad = [notvalid")
                with self.assertRaisesRegex(ValueError, "CANDIDATE_CONFIG_NOT_PARSEABLE"):
                    app.restore(pilot, "backup-invalid-candidate", execute=True)
            self.assertFalse((pilot / "audit-backups").exists())


if __name__ == "__main__":
    unittest.main()

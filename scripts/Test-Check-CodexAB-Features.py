#!/usr/bin/env python3
"""Synthetic preflight validation only: no real Codex CLI, network or model calls."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SOURCE = Path(__file__).with_name("Check-CodexAB-Features.py")
spec = importlib.util.spec_from_file_location("codex_ab_preflight", SOURCE)
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class TestFeaturePreflight(unittest.TestCase):
    def test_cli_flags_only_whitelisted_booleans(self):
        raw = ("multi_agent experimental false\n"
               "multi_agent_v2 under_development true\n"
               "unrelated_api_secret PRIVATE_SECRET_SENTINEL\n"
               "collab stable false\n"
               "log PRIVATE_SENTINEL\n")
        info = tool.public_feature_flags(raw)
        self.assertEqual(info, {"multi_agent": False, "multi_agent_v2": True,
                                "collab": False})
        self.assertNotIn("PRIVATE", json.dumps(info))

    def test_config_summary_ignores_unrelated_secrets(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "config.toml"
            path.write_text(
                "dangerous_credential = 'PRIVATE_SENTINEL'\n"
                "[agents]\nenabled = true\nmax_concurrent_threads_per_session = 2\n"
                "[agents.luna-medium]\nconfig_file = 'agents/luna-medium.toml'\n"
                "[features]\nmulti_agent = true\n"
                "[features.multi_agent_v2]\nenabled = false\n",
                encoding="utf-8")
            info = tool.config_summary(path)
            self.assertTrue(info["agents_enabled_configured"])
            self.assertTrue(info["multi_agent_feature_configured"])
            self.assertFalse(info["multi_agent_v2_feature_configured"])
            self.assertEqual(info["configured_worker_roles"], 1)
            self.assertNotIn("PRIVATE_SENTINEL", str(info))

    def test_end_to_end_audit_is_read_only_and_never_calls_exec(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            for arm in tool.runner.ARMS:
                home = root / (arm + "-home")
                home.mkdir()
                (home / "AGENTS.md").write_text("different-" + arm, encoding="utf-8")
                (home / "config.toml").write_text(
                    "[agents]\nenabled = true\n"
                    "max_concurrent_threads_per_session = 2\n",
                    encoding="utf-8")
                (home / "auth.json").write_text("PRIVATE_AUTH_SENTINEL", encoding="utf-8")
            class Proc:
                returncode = 0
                stdout = "multi_agent experimental false\nmulti_agent_v2 development false\n"
            def fake_codex(argv, **kw):
                self.assertEqual(argv, ["features", "list"])
                self.assertIn("CODEX_HOME", kw["env"])
                return Proc()
            with patch.object(tool.runner, "call_codex", side_effect=fake_codex):
                report = tool.audit(root)
            self.assertTrue(report["multi_agent_reported_disabled_on_both"])
            self.assertTrue(report["config_identical_between_arms"])
            self.assertTrue(report["agents_instructions_distinct"])
            self.assertEqual(report["model_calls_made"], 0)
            self.assertNotIn("PRIVATE_AUTH_SENTINEL", json.dumps(report))

    def test_mismatched_configs_fail_without_model_calls(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            for arm in tool.runner.ARMS:
                home = root / (arm + "-home")
                home.mkdir()
                (home / "AGENTS.md").write_text(arm, encoding="utf-8")
                (home / "config.toml").write_text(
                    "[agents]\nenabled = true\n" + (
                        "max_concurrent_threads_per_session = 2\n"
                        if arm == "baseline" else ""), encoding="utf-8")
            class Proc:
                returncode = 0
                stdout = ""
            with patch.object(tool.runner, "call_codex", return_value=Proc()):
                with self.assertRaises(ValueError):
                    tool.audit(root)


if __name__ == "__main__":
    unittest.main()

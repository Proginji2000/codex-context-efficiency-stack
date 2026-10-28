#!/usr/bin/env python3
"""Synthetic tests only; no live Codex, remote calls, or credential inspection."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SOURCE = Path(__file__).with_name("Check-CodexAB-ModelPrompt.py")
spec = importlib.util.spec_from_file_location("codex_ab_model_prompt", SOURCE)
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class TestModelPromptPreflight(unittest.TestCase):
    def test_bundled_model_only_whitelisted_metadata(self):
        result = tool.model_summary({
            "models": [{
                "slug": "gpt-6-luna",
                "multi_agent_version": "v2",
                "tool_mode": "code_mode_only",
                "shell_type": "shell_command",
                "model_messages": {"base_instructions": "PRIVATE_INTERNAL_TEMPLATE"},
                "other": {"api_key": "PRIVATE_KEY"},
            }]
        })
        self.assertEqual(result["multi_agent_version"], "v2")
        self.assertEqual(result["tool_mode"], "code_mode_only")
        self.assertTrue(result["model_in_bundled_catalog"])
        self.assertNotIn("PRIVATE", json.dumps(result))

    def test_prompt_marker_nested_json(self):
        sample = {"input": [
            {"role": "developer", "content": {
                "text": "The Luna parent is an orchestrator only"
            }}
        ]}
        self.assertTrue(tool.marker_visible(
            sample, tool.MARKERS["candidate"]))
        self.assertFalse(tool.marker_visible(
            sample, tool.MARKERS["baseline"]))

    def test_probe_no_model_calls_and_no_raw_secrets(self):
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            fixture = root / "workspaces" / "pair-1-baseline"
            (fixture / ".git").mkdir(parents=True)
            for arm in tool.runner.ARMS:
                home = root / (arm + "-home")
                home.mkdir()
                (home / "config.toml").write_text(
                    "[agents]\nenabled = true\n", encoding="utf-8")
                (home / "AGENTS.md").write_text(
                    tool.MARKERS[arm], encoding="utf-8")
                (home / "auth.json").write_text(
                    "PRIVATE_AUTH_SENTINEL", encoding="utf-8")

            catalog = json.dumps({"models": [{
                "slug": "gpt-6-luna",
                "tool_mode": "code_mode_only",
                "multi_agent_version": "v2",
                "shell_type": "shell_command",
                "model_messages": {
                    "instructions_template": "PRIVATE_MODEL_TEMPLATE"
                },
            }]})

            class Proc:
                returncode = 0
                def __init__(self, output):
                    self.stdout = output

            calls = []
            def fake_codex(argv, **kwargs):
                calls.append(argv)
                self.assertEqual(
                    kwargs["env"]["CODEX_HOME"].split("-home")[0][-9:],
                    "candidate" if len(calls) > 2 else "baseline"
                )
                if argv == ["debug", "models", "--bundled"]:
                    return Proc(catalog)
                self.assertEqual(
                    argv, ["--model", "gpt-6-luna", "-c",
                           "model_reasoning_effort=medium",
                           "debug", "prompt-input"])
                arm = "baseline" if len(calls) <= 2 else "candidate"
                return Proc(json.dumps({
                    "input": [{"role": "developer",
                               "content": tool.MARKERS[arm]}],
                    "secret": "PRIVATE_PROMPT_SENTINEL",
                }))

            with patch.object(tool.runner, "call_codex",
                              side_effect=fake_codex):
                report = tool.probe(root)
            self.assertEqual(len(calls), 4)
            self.assertEqual(report["model_invocations"], 0)
            self.assertTrue(report["config_identical"])
            self.assertTrue(report["agents_distinct"])
            self.assertTrue(all(
                report["arms"][arm]["agents_marker_visible_in_debug_prompt"]
                for arm in tool.runner.ARMS
            ))
            for secret in ("PRIVATE_AUTH_SENTINEL", "PRIVATE_PROMPT_SENTINEL",
                           "PRIVATE_MODEL_TEMPLATE"):
                self.assertNotIn(secret, json.dumps(report))

    def test_missing_fixture_stops_before_codex(self):
        with tempfile.TemporaryDirectory() as dirname:
            with patch.object(tool.runner, "call_codex",
                              side_effect=AssertionError("should not run")):
                with self.assertRaises(ValueError):
                    tool.probe(Path(dirname))

    def test_bad_catalog_rejected(self):
        with self.assertRaises(ValueError):
            tool.model_summary({"not_models": []})


if __name__ == "__main__":
    unittest.main()

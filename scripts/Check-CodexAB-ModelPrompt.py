#!/usr/bin/env python3
"""No-model-call preflight for isolated Codex A/B model metadata and AGENTS discovery."""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

RUNNER = Path(__file__).with_name("Run-CodexAB.py")
spec = importlib.util.spec_from_file_location("codex_ab_runner", RUNNER)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

MODEL = "gpt-6-luna"
MARKERS = {
    "baseline": "The parent is a dispatcher and integrator, not an execution worker.",
    "candidate": "The Luna parent is an orchestrator only",
}


def model_summary(catalog):
    if isinstance(catalog, dict):
        entries = catalog.get("models")
    elif isinstance(catalog, list):
        entries = catalog
    else:
        raise ValueError("invalid bundled model catalog")
    if not isinstance(entries, list):
        raise ValueError("missing catalog models")
    for entry in entries:
        if isinstance(entry, dict) and entry.get("slug") == MODEL:
            return {
                "model_slug": MODEL,
                "multi_agent_version": (
                    entry.get("multi_agent_version")
                    if entry.get("multi_agent_version") in ("v1", "v2") else None
                ),
                "tool_mode": (
                    entry.get("tool_mode")
                    if entry.get("tool_mode") in ("code_mode_only", "auto", "standard") else None
                ),
                "shell_type": (
                    entry.get("shell_type")
                    if entry.get("shell_type") in ("shell_command", "exec_command") else None
                ),
                "model_in_bundled_catalog": True,
            }
    return {"model_slug": MODEL, "model_in_bundled_catalog": False,
            "multi_agent_version": None, "tool_mode": None, "shell_type": None}


def strings_only(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from strings_only(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings_only(item)


def marker_visible(model_input, marker):
    return any(marker in value for value in strings_only(model_input))


def probe(root):
    if not root.is_dir() or root.is_symlink():
        raise ValueError("experiment directory missing or redirected")
    fixture = root / "workspaces" / "pair-1-baseline"
    if not fixture.is_dir() or fixture.is_symlink() or not (fixture / ".git").is_dir():
        raise ValueError("preserved disposable trial missing")
    outputs = {}
    for arm in runner.ARMS:
        home = root / (arm + "-home")
        config = home / "config.toml"
        agents = home / "AGENTS.md"
        if (not home.is_dir() or home.is_symlink() or not agents.is_file()
                or agents.is_symlink() or not config.is_file() or config.is_symlink()):
            raise ValueError("isolated profile invalid")
        env = runner.home_env(root, arm)
        catalog_process = runner.call_codex(
            ["debug", "models", "--bundled"], env=env, timeout=30)
        if catalog_process.returncode:
            raise ValueError("bundled catalog command unavailable")
        catalog = model_summary(json.loads(catalog_process.stdout))
        prompt_process = runner.call_codex(
            ["--model", MODEL, "-c", "model_reasoning_effort=medium",
             "debug", "prompt-input"],
            cwd=fixture, env=env, timeout=30)
        if prompt_process.returncode:
            raise ValueError("prompt-input command unavailable")
        prompt = json.loads(prompt_process.stdout)
        outputs[arm] = {
            "bundled_model": catalog,
            "agents_marker_visible_in_debug_prompt": marker_visible(prompt, MARKERS[arm]),
            "global_agents_sha256": runner.digest(runner.read_file(agents)),
            "profile_config_sha256": runner.digest(runner.read_file(config)),
        }
    return {
        "schema_version": 1,
        "model_invocations": 0,
        "network_required": False,
        "read_only": True,
        "arms": outputs,
        "config_identical": (
            outputs["baseline"]["profile_config_sha256"]
            == outputs["candidate"]["profile_config_sha256"]
        ),
        "agents_distinct": (
            outputs["baseline"]["global_agents_sha256"]
            != outputs["candidate"]["global_agents_sha256"]
        ),
        "interpretation": (
            "Model metadata is bundled (not a runtime tool inventory). "
            "Prompt-input marker presence verifies only that instruction text "
            "appears in the diagnostic prompt, not that the agent can spawn or write. "
            "False may reflect unsupported debug surface or prompt mismatch."
        ),
        "privacy": (
            "No raw catalogs, prompts, model instructions, tool output, auth, "
            "sessions, messages or source content are printed or stored."
        ),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        report = probe(Path(args.output).expanduser().resolve(strict=True))
    except (OSError, ValueError, TypeError, KeyError, RuntimeError):
        print("STOP: safe model/prompt preflight failed; no private text printed.",
              file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

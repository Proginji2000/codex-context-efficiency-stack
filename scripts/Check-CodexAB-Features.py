#!/usr/bin/env python3
"""Read-only preflight of isolated Codex A/B collaboration settings (zero model calls)."""
import argparse
import importlib.util
import json
import re
import sys
import tomllib
from pathlib import Path

RUNNER = Path(__file__).with_name("Run-CodexAB.py")
spec = importlib.util.spec_from_file_location("codex_ab_runner", RUNNER)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

FLAGS = ("multi_agent", "multi_agent_v2", "collab")


def public_feature_flags(output):
    """Extract only allowlisted boolean values; never echo CLI output."""
    state = {key: None for key in FLAGS}
    for line in output.splitlines():
        parts = line.strip().split()
        if len(parts) < 2 or parts[0] not in state:
            continue
        value = parts[-1].lower()
        if value in ("true", "false"):
            state[parts[0]] = value == "true"
    return state


def flag_state(features, name):
    item = features.get(name, None)
    if type(item) is bool:
        return item
    if isinstance(item, dict) and type(item.get("enabled")) is bool:
        return item["enabled"]
    return None


def config_summary(path):
    # Read only config.toml. Never read auth.json or session artifacts.
    obj = tomllib.loads(path.read_text(encoding="utf-8"))
    agents = obj.get("agents", {})
    features = obj.get("features", {})
    if not isinstance(agents, dict) or not isinstance(features, dict):
        raise ValueError("invalid configuration shape")
    enabled = agents.get("enabled", None)
    limit = agents.get("max_concurrent_threads_per_session")
    if enabled is not None and type(enabled) is not bool:
        raise ValueError("invalid agents setting")
    if limit is not None and (type(limit) is not int or limit < 1):
        raise ValueError("invalid concurrency limit")
    role_names = {role for role in runner.ROLES if isinstance(
        agents.get(role), dict)}
    return {
        "agents_enabled_configured": enabled,
        "configured_worker_roles": len(role_names),
        "expected_worker_roles": len(runner.ROLES),
        "max_concurrent_threads_configured": limit,
        "multi_agent_feature_configured": flag_state(features, "multi_agent"),
        "multi_agent_v2_feature_configured": flag_state(features, "multi_agent_v2"),
    }


def audit(root):
    if not root.is_dir():
        raise ValueError("experiment directory missing")
    report = {}
    agent_hashes, conf_hashes = [], []
    for arm in runner.ARMS:
        home = root / (arm + "-home")
        if home.is_symlink() or not home.is_dir():
            raise ValueError("missing or redirected isolated home")
        conf = home / "config.toml"
        agents_md = home / "AGENTS.md"
        if conf.is_symlink() or agents_md.is_symlink():
            raise ValueError("redirected instruction/config file")
        summary = config_summary(conf)
        agent_hashes.append(runner.digest(runner.read_file(agents_md)))
        conf_hashes.append(runner.digest(runner.read_file(conf)))
        proc = runner.call_codex(["features", "list"], env=runner.home_env(root, arm),
                                 timeout=20)
        if proc.returncode != 0:
            raise ValueError("Codex features list unavailable")
        summary["cli_feature_flags"] = public_feature_flags(proc.stdout)
        report[arm] = summary
    identical = conf_hashes[0] == conf_hashes[1]
    distinct = agent_hashes[0] != agent_hashes[1]
    if not identical or not distinct:
        raise ValueError("A/B isolation fingerprint mismatch")
    reported_disabled = all(report[arm]["cli_feature_flags"]["multi_agent"] is False
                            for arm in runner.ARMS)
    return {
        "schema_version": 1,
        "model_calls_made": 0,
        "config_identical_between_arms": identical,
        "agents_instructions_distinct": distinct,
        "baseline": report["baseline"],
        "candidate": report["candidate"],
        "multi_agent_reported_disabled_on_both": reported_disabled,
        "interpretation": (
            "CLI reports multi_agent disabled in both isolated homes; may block parent delegation."
            if reported_disabled else
            "Flag state alone cannot prove delegation availability, model tool support or sandbox access."
        ),
        "safety": "Only isolated config.toml, AGENTS hashes and Codex features list; no auth, sessions, prompts, raw CLI output or model calls.",
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True)
    args = p.parse_args(argv)
    try:
        result = audit(Path(args.output).expanduser().resolve(strict=True))
    except (OSError, ValueError, KeyError, RuntimeError, TypeError):
        print("STOP: cannot audit isolated features; no private content printed.",
              file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

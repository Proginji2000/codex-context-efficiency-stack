#!/usr/bin/env python3
"""Opt-in worktree wave planner; does not launch Codex agents or delete worktrees."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

MANAGER = Path(__file__).with_name("Manage-CodexWorktrees.py")
LANES = {"luna-low", "luna-medium", "luna-high", "terra-medium", "terra-high",
         "ui-implementer", "sol-high", "sol-xhigh", "astra-high"}
NAME = re.compile(r"[a-z][a-z0-9-]{0,35}\Z")


class InvalidPlan(ValueError):
    pass


def owned_path(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 200:
        raise InvalidPlan("Invalid owned path.")
    if value.startswith(("/", "\\")) or any(c in value for c in "\\:*?<>|"):
        raise InvalidPlan("Write ownership must use relative plain paths.")
    parts = value.split("/")
    if any(p in ("", ".", "..") for p in parts) or any(
        p.lower() in (".git", ".codex") for p in parts
    ):
        raise InvalidPlan("Write scope traverses a protected directory.")
    return "/".join(parts).casefold()


def validate(manifest):
    if not isinstance(manifest, dict) or manifest.get("version") != 1:
        raise InvalidPlan("Expected version 1 manifest.")
    workers = manifest.get("workers")
    if not isinstance(workers, list) or not 1 <= len(workers) <= 2:
        raise InvalidPlan("A wave supports one or two writers.")
    result = []
    names = set()
    for worker in workers:
        if not isinstance(worker, dict):
            raise InvalidPlan("Invalid worker entry.")
        name, lane, goal = (worker.get(k) for k in ("name", "lane", "goal"))
        if not isinstance(name, str) or not NAME.fullmatch(name) or name in names:
            raise InvalidPlan("Worktree names must be unique safe slugs.")
        if lane not in LANES:
            raise InvalidPlan("Unknown worker lane.")
        if not isinstance(goal, str) or not 1 <= len(goal.strip()) <= 500:
            raise InvalidPlan("A bounded worker goal is required.")
        paths = worker.get("write_scopes")
        if not isinstance(paths, list) or not 1 <= len(paths) <= 32:
            raise InvalidPlan("Each writer requires 1-32 owned paths.")
        normalized = [owned_path(p) for p in paths]
        if len(set(normalized)) != len(normalized):
            raise InvalidPlan("Duplicate owned path.")
        names.add(name)
        result.append({"name": name, "lane": lane, "write_scopes": normalized})
    for first in result:
        for second in result:
            if first is second:
                continue
            for a in first["write_scopes"]:
                for b in second["write_scopes"]:
                    if a == b or a.startswith(b + "/") or b.startswith(a + "/"):
                        raise InvalidPlan("Overlapping writer ownership.")
    return result


def manager(repo, name, apply):
    cmd = [sys.executable, str(MANAGER), "create",
           "--name", name, "--repo", str(repo)]
    if apply:
        cmd.append("--apply")
    completed = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
    if completed.returncode:
        raise InvalidPlan("Git worktree preflight or creation blocked.")
    try:
        report = json.loads(completed.stdout)
    except json.JSONDecodeError:
        raise InvalidPlan("Unexpected worktree manager output.") from None
    expected = apply is True
    if report.get("created") is not expected:
        raise InvalidPlan("Unexpected worktree manager mode.")
    return report


def main():
    parser = argparse.ArgumentParser(description="Validate and optionally provision independent worktrees.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    created = []
    try:
        if args.manifest.stat().st_size > 65536:
            raise InvalidPlan("Manifest is too large.")
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        workers = validate(manifest)
        if not MANAGER.is_file():
            raise InvalidPlan("Worktree manager unavailable.")
        # Preflight all destinations before making the first branch.
        for worker in workers:
            manager(args.repo, worker["name"], False)
        if args.apply:
            for worker in workers:
                manager(args.repo, worker["name"], True)
                created.append(worker["name"])
        print(json.dumps({
            "mode": "applied" if args.apply else "preview_only",
            "workers": [{"name": w["name"], "lane": w["lane"],
                         "owned_paths": len(w["write_scopes"]),
                         "created": w["name"] in created} for w in workers],
            "created_names": created, "agents_started": 0,
            "automatic_cleanup": False,
            "note": "Assign actual workers separately; no cleanup or merging is performed.",
        }, indent=2))
        return 0
    except (InvalidPlan, OSError, ValueError, UnicodeError, subprocess.TimeoutExpired):
        print("BLOCKED: Invalid plan or failed local Git preflight; details withheld.", file=sys.stderr)
        if created:
            print("PARTIAL: worktrees retained: " + ", ".join(created), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""One opt-in, read-only Codex tool/delegation smoke test. No raw model logs."""
import argparse
import json
import os
import re
import secrets
import subprocess
import sys
import time
from pathlib import Path
import importlib.util

SPEC = importlib.util.spec_from_file_location(
    "codex_ab_runner", Path(__file__).with_name("Run-CodexAB.py")
)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)

MODEL = "gpt-6-luna"
MARKER_SIZE = 16  # 32 random hexadecimal characters, not included in prompt.
RUNNER_VERSION = 1


def init_probe_workspace(workspace, marker):
    workspace.mkdir(parents=True)
    (workspace / "marker.txt").write_text(marker + "\n", encoding="ascii")
    (workspace / ".gitignore").write_text(
        "__pycache__/\n*.pyc\n", encoding="ascii"
    )
    if runner.call(["git", "init", "-q", "-b", "main"], cwd=workspace).returncode:
        raise ValueError("cannot create disposable git repository")
    if runner.call(["git", "add", "marker.txt", ".gitignore"],
                   cwd=workspace).returncode:
        raise ValueError("cannot stage synthetic fixture")
    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = "2020-01-01T00:00:00+00:00"
    env["GIT_COMMITTER_DATE"] = "2020-01-01T00:00:00+00:00"
    commit = runner.call([
        "git", "-c", "user.name=Codex Diagnostic Fixture",
        "-c", "user.email=probe@example.invalid",
        "commit", "-qm", "synthetic read-only base"
    ], cwd=workspace, env=env)
    if commit.returncode:
        raise ValueError("cannot commit synthetic fixture")
    return runner.call(["git", "rev-parse", "HEAD"], cwd=workspace).stdout.strip()


def classify_final_text(text):
    # Intentionally coarse classification: never echo model-authored text.
    lowered = text.lower()
    if re.search(r"(code.mode host|code.mode.host).{0,80}(handshake|exited|failed)", lowered):
        return "CODE_MODE_HOST_ERROR_CLAIM"
    if re.search(r"(no (available |integrated )?(shell|exec|tool)|tools? (are |is )?(not |un)available|cannot access (the )?tools?)", lowered):
        return "NO_TOOLS_CLAIM"
    if re.search(r"(cannot|unable to|can.t|failed to).{0,80}(spawn|delegat|worker|subagent)", lowered):
        return "DELEGATION_UNAVAILABLE_CLAIM"
    if "permission denied" in lowered or "access is denied" in lowered:
        return "PERMISSION_DENIED_CLAIM"
    if "blocked" in lowered:
        return "BLOCKED_OR_UNVERIFIED"
    return "UNCLASSIFIED"


def classify_stderr(stderr):
    """Return only a fixed class; never expose or persist stderr text."""
    if not stderr or not stderr.strip():
        return "NONE"
    text = stderr.lower()
    if ("code-mode host" in text or "code_mode_host" in text or
            "codex-code-mode-host" in text):
        return "CODE_MODE_HOST_MENTION"
    if "permission denied" in text or "access is denied" in text:
        return "PERMISSION_MENTION"
    if "agent thread limit reached" in text:
        return "AGENT_LIMIT_MENTION"
    if ("spawn_agent" in text or "subagent" in text or
            "multi-agent" in text):
        return "COLLABORATION_MENTION"
    if "sandbox" in text and (
            "denied" in text or "failed" in text or "blocked" in text):
        return "SANDBOX_ERROR_MENTION"
    return "OTHER_OR_NONFATAL_WARNING"


def collab_event_summary(stdout):
    """Count allowlisted JSONL fields only; never copy prompts or thread ids."""
    tools = ("spawn_agent", "send_input", "wait", "close_agent")
    statuses = ("in_progress", "completed", "failed")
    summary = {
        tool: {status: 0 for status in statuses}
        for tool in tools
    }
    max_receiver_counts = {tool: 0 for tool in tools}
    other_collab = 0
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except (TypeError, ValueError):
            continue
        if not isinstance(event, dict) or event.get("type") not in (
                "item.started", "item.completed", "item.updated"):
            continue
        item = event.get("item")
        if not isinstance(item, dict) or item.get("type") != "collab_tool_call":
            continue
        # Count state only from started/completed snapshots. Unknown tools
        # and statuses stay in coarse counters; no arbitrary strings output.
        tool = item.get("tool")
        status = item.get("status")
        if tool not in summary or status not in statuses:
            other_collab += 1
            continue
        summary[tool][status] += 1
        receivers = item.get("receiver_thread_ids")
        if isinstance(receivers, list):
            max_receiver_counts[tool] = max(
                max_receiver_counts[tool], min(len(receivers), 20))
    return {
        "observed_events_by_tool_and_status": summary,
        "max_receiver_count_by_tool": max_receiver_counts,
        "unknown_collab_event_count": other_collab,
        "limitations": (
            "Only events present in codex exec --json. V2 spawn events "
            "and unified execution events can be omitted. A wait event "
            "does not prove the worker was successfully created."
        ),
    }


def summarize(stdout, stderr, exit_code, marker, elapsed, workspace, timed_out):
    usage, delegated, json_valid, _ = runner.parse_events(stdout)
    final_messages = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except (ValueError, TypeError):
            continue
        if not isinstance(event, dict) or event.get("type") != "item.completed":
            continue
        item = event.get("item")
        if isinstance(item, dict) and item.get("type") == "agent_message":
            value = item.get("text")
            if isinstance(value, str):
                final_messages.append(value)
    # Deliberately do not test raw stdout, which may contain source/tool output.
    marker_visible_in_final = any(
        re.search(r"(?<![0-9a-f])" + re.escape(marker) + r"(?![0-9a-f])", msg)
        for msg in final_messages
    )
    final_class = ("MARKER_READ_IN_MODEL_REPLY" if marker_visible_in_final else
                   classify_final_text(final_messages[-1]) if final_messages else
                   "NO_FINAL_MESSAGE_OBSERVED")
    status = runner.call(["git", "status", "--porcelain"], cwd=workspace)
    unchanged = status.returncode == 0 and not status.stdout.strip()
    events = runner.summarize_cli_events(
        stdout, stderr, exit_code, timed_out=timed_out
    )
    # This demonstrates tool-mediated discovery of the marker at most;
    # neither the JSONL surface nor a matching reply proves a worker ran.
    return {
        "schema_version": RUNNER_VERSION,
        "probe_kind": "one-read-only-delegation-smoke",
        "model": MODEL,
        "sandbox": "read-only",
        "used_ephemeral": True,
        "model_invocations": 1,
        "elapsed_s": round(elapsed, 3),
        "codex_returncode": exit_code,
        "timed_out": timed_out,
        "stderr_present": bool(stderr.strip()),
        "json_stream_valid": json_valid,
        "final_message_observed": bool(final_messages),
        "result_class": final_class,
        "marker_seen_in_final": marker_visible_in_final,
        "disposable_workspace_unchanged": unchanged,
        "delegation_event_observed": delegated,
        "delegation_verified": False,
        "usage": usage,
        "cli_metadata": events,
        "observed_collaboration": collab_event_summary(stdout),
        "stderr_category": classify_stderr(stderr),
        "interpretation": (
            "Matching the unknown marker demonstrates access to its contents, "
            "not that a subagent rather than its parent performed the read. "
            "Missing JSONL collaboration events are inconclusive."
        ),
        "privacy": (
            "The synthetic marker exists only in the disposable Git fixture; "
            "it is never included in sanitized results. No raw model messages, "
            "commands, stderr, JSONL, auth or session contents are saved."
        ),
    }


def probe(args):
    if not args.execute:
        raise ValueError("single live model invocation requires --execute")
    if not (20 <= args.timeout <= 180):
        raise ValueError("timeout must be between 20 and 180 seconds")
    pilot = Path(args.pilot).expanduser().resolve(strict=True)
    cfg = runner.state(pilot)
    if cfg.get("model") != MODEL or cfg.get("sandbox") != "workspace-write":
        raise ValueError("unexpected baseline experiment definition")
    baseline = pilot / "baseline-home"
    conf = baseline / "config.toml"
    if baseline.is_symlink() or conf.is_symlink() or (
        runner.digest(runner.read_file(conf)) != cfg["config_sha256"]
    ):
        raise ValueError("baseline config changed since original preparation")
    root = Path(args.output).expanduser().resolve()
    if (root.exists() or root == pilot or pilot in root.parents
            or root == Path.home().resolve()
            or Path(args.repo).resolve() in root.parents):
        raise ValueError("choose a new, external disposable probe directory")
    root.mkdir(parents=True)
    workspace = root / "workspace"
    marker = secrets.token_hex(MARKER_SIZE)
    init_probe_workspace(workspace, marker)
    prompt = (
        "You are the orchestrator-only Luna parent. Delegate exactly one "
        "read-only task to the configured luna-medium worker. The worker "
        "must use an available local tool to read marker.txt in this working "
        "directory, and return its exact 32-character hexadecimal contents. "
        "Relay only that marker as the final answer. The parent must not "
        "read the file itself or guess. If delegation or file reading is "
        "unavailable, reply BLOCKED. Do not modify files, contact the "
        "network, install tools or change configuration."
    )
    cmd = ["exec", "--json", "--ephemeral", "--sandbox", "read-only",
           "-C", str(workspace), "--model", MODEL,
           "-c", "model_reasoning_effort=medium", prompt]
    print("START: exactly one sandboxed read-only Codex invocation; no raw logs.",
          flush=True)
    start = time.monotonic()
    try:
        proc = runner.call_codex(
            cmd, env=runner.home_env(pilot, "baseline"), timeout=args.timeout)
        stdout, stderr, code, timed_out = (
            proc.stdout, proc.stderr, proc.returncode, False)
    except subprocess.TimeoutExpired:
        stdout, stderr, code, timed_out = "", "", None, True
    elapsed = time.monotonic() - start
    report = summarize(stdout, stderr, code, marker, elapsed, workspace, timed_out)
    runner.save_json(root / "sanitized-probe-result.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))
    if (timed_out or code != 0 or not report["json_stream_valid"]
            or not report["marker_seen_in_final"]
            or not report["disposable_workspace_unchanged"]):
        return 1
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pilot", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--repo", default=str(Path(__file__).resolve().parent.parent))
    p.add_argument("--timeout", type=int, default=90)
    p.add_argument("--execute", action="store_true")
    args = p.parse_args(argv)
    try:
        return probe(args)
    except (OSError, ValueError, RuntimeError, KeyError):
        print("STOP: safe read-only Codex probe precondition failed. "
              "No private input printed.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

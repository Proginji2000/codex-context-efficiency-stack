#!/usr/bin/env python3
"""Offline, allowlisted audit of EXPLICITLY supplied Codex app-server v2 events.

Pinned reference: openai/codex tag rust-v0.165.0, schema/typescript/v2.
This tool never starts Codex, reads CODEX_HOME, discovers sessions, connects
to an app-server, writes data, or prints event payloads, prompts, or IDs.
A supplied stream is NOT an independent attestation of the TUI runtime.
"""
import argparse
import json
import math
from pathlib import Path
import re
import sys

MAX_BYTES = 3_000_000
MAX_EVENTS = 30_000
METHODS = frozenset({
    "item/started", "item/completed", "thread/tokenUsage/updated",
    "turn/completed",
})
TOOLS = frozenset({
    "spawnAgent", "sendInput", "resumeAgent", "wait", "closeAgent",
    "sendMessage", "followupTask", "interruptAgent", "listAgents",
})
STATUSES = frozenset({"inProgress", "completed", "failed", "interrupted"})
AGENT_KINDS = frozenset({"started", "interacted", "interrupted", "completed"})
FIELDS = (
    "totalTokens", "inputTokens", "cachedInputTokens",
    "cacheWriteInputTokens", "outputTokens", "reasoningOutputTokens",
)


class AuditError(ValueError):
    """Privacy-safe fixed diagnostic codes only."""


def integer(value):
    return type(value) is int and value >= 0


def identifier(value):
    return isinstance(value, str) and 0 < len(value) <= 256


def read_events(file):
    path = Path(file).expanduser()
    if path.is_symlink() or not path.is_file():
        raise AuditError("INPUT_MISSING_OR_SYMLINK")
    if path.stat().st_size > MAX_BYTES:
        raise AuditError("INPUT_TOO_LARGE")
    try:
        with path.open("r", encoding="utf-8-sig") as reader:
            for line in reader:
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                except (ValueError, UnicodeError):
                    raise AuditError("INVALID_JSONL") from None
                if not isinstance(value, dict):
                    raise AuditError("INVALID_EVENT")
                yield value
    except UnicodeError:
        raise AuditError("INVALID_UTF8") from None


def audit(events):
    counts = {tool: {"started": 0, "completed": 0,
                     "failed": 0, "interrupted": 0} for tool in sorted(TOOLS)}
    item_starts = {}
    item_ends = set()
    unpaired = 0
    activity = {}
    turns = {"completed": 0, "failed": 0, "interrupted": 0,
             "inProgress": 0}
    usages = {}
    token_updates = 0
    seen = 0
    ignored = 0
    for event in events:
        seen += 1
        if seen > MAX_EVENTS:
            raise AuditError("TOO_MANY_EVENTS")
        method = event.get("method")
        if method not in METHODS:
            ignored += 1
            continue
        params = event.get("params")
        if not isinstance(params, dict):
            raise AuditError("INVALID_PARAMS")
        if method in ("item/started", "item/completed"):
            item = params.get("item")
            if not isinstance(item, dict) or not identifier(item.get("id")):
                raise AuditError("INVALID_ITEM")
            item_type = item.get("type")
            if item_type == "collabAgentToolCall":
                tool = item.get("tool")
                status = item.get("status")
                if tool not in TOOLS or status not in STATUSES:
                    raise AuditError("UNKNOWN_COLLAB_STATUS")
                key = (params.get("threadId"), params.get("turnId"), item["id"])
                if not all(identifier(v) for v in key):
                    raise AuditError("INVALID_INTERNAL_IDENTIFIERS")
                if method == "item/started":
                    if key in item_starts or key in item_ends:
                        raise AuditError("DUPLICATE_ITEM")
                    item_starts[key] = tool
                    counts[tool]["started"] += 1
                else:
                    if key in item_ends:
                        raise AuditError("DUPLICATE_ITEM")
                    item_ends.add(key)
                    if item_starts.get(key) != tool:
                        unpaired += 1
                    if status == "inProgress":
                        raise AuditError("NONTERMINAL_COMPLETED_ITEM")
                    if tool == "spawnAgent" and status == "completed":
                        receivers = item.get("receiverThreadIds")
                        if not isinstance(receivers, list) or not receivers or not all(
                            identifier(v) for v in receivers
                        ):
                            raise AuditError("SUCCESSFUL_SPAWN_WITHOUT_RECEIVER")
                    counts[tool][status] += 1
            elif item_type == "subAgentActivity" and method == "item/completed":
                kind = item.get("kind")
                agent_id = item.get("agentThreadId")
                if kind not in AGENT_KINDS or not identifier(agent_id):
                    raise AuditError("INVALID_AGENT_ACTIVITY")
                states = activity.setdefault(agent_id, set())
                if kind in states:
                    raise AuditError("DUPLICATE_AGENT_ACTIVITY")
                states.add(kind)
            # All other item types are ignored by design: they may contain
            # raw commands, paths, message text, results, and secrets.
        elif method == "turn/completed":
            turn = params.get("turn")
            if not isinstance(turn, dict) or turn.get("status") not in turns:
                raise AuditError("INVALID_TURN_STATUS")
            turns[turn["status"]] += 1
        elif method == "thread/tokenUsage/updated":
            thread = params.get("threadId")
            usage = params.get("tokenUsage")
            total = usage.get("total") if isinstance(usage, dict) else None
            if not identifier(thread) or not isinstance(total, dict):
                raise AuditError("INVALID_TOKEN_USAGE")
            if not all(integer(total.get(f)) for f in FIELDS):
                raise AuditError("INVALID_TOKEN_COUNTER")
            if (total["cachedInputTokens"] > total["inputTokens"] or
                    total["reasoningOutputTokens"] > total["outputTokens"]):
                raise AuditError("TOKEN_ACCOUNTING_INVALID")
            last = usages.get(thread)
            if last is not None and total["totalTokens"] < last:
                raise AuditError("TOKEN_COUNTER_REGRESSION")
            usages[thread] = total["totalTokens"]
            token_updates += 1
    finished = sum("started" in v and "completed" in v for v in activity.values())
    partial = len(activity) - finished
    return {
        "schema_version": 1,
        "protocol_reference": "openai/codex rust-v0.165.0 app-server v2",
        "input_provenance": "operator_supplied_unattested_event_export",
        "event_count": seen,
        "ignored_event_count": ignored,
        "collab_calls": counts,
        "unpaired_collab_completions": unpaired,
        "subagent_activity_ids_observed": len(activity),
        "subagent_started_and_completed_observed": finished,
        "subagent_partial_activity_observed": partial,
        "turn_outcomes": turns,
        "token_usage_notification_count": token_updates,
        "token_usage_thread_count": len(usages),
        "token_latest_per_thread_sum_descriptive_only": (
            sum(usages.values()) if usages else None
        ),
        "independently_attests_original_tui": False,
        "effective_sandbox_policy_verified": False,
        "runtime_event_availability_in_pinned_cli_verified": False,
        "model_calls_made": 0,
        "files_written": 0,
        "limitations": [
            "Supplied event lines may be incomplete, fabricated or unrelated to a TUI run.",
            "No thread IDs, prompts, messages, command text or raw session content are printed.",
            "Thread token totals can overlap; summed counters are not billed usage or subscription quota.",
            "Events are not fetched from running sessions and cannot independently attest prior TUI runs.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True,
                        help="Operator-curated v2 event JSONL, never CODEX_HOME/session files")
    args = parser.parse_args(argv)
    try:
        result = audit(read_events(args.input))
    except (AuditError, OSError, TypeError, KeyError):
        # Never echo input, paths, event bodies, or arbitrary exception text.
        print("STOP: EVENT_AUDIT_INVALID_OR_UNAVAILABLE", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

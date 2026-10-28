#!/usr/bin/env python3
"""Compare sanitized paired Codex CLI A/B trials; never launches Codex or reads sessions."""

import argparse
import json
import statistics
import sys
from pathlib import Path

CONTROLS = frozenset({
    "cli_version", "model", "reasoning_effort", "sandbox",
    "repo_head", "mcp_profile", "prompt_sha256",
})
RUN_KEYS = frozenset({
    "pair", "arm", "controls", "agents_sha", "case_id",
    "success", "delegated", "parent_orchestrated", "safety_pass",
    "retries", "elapsed_s", "usage",
})
USAGE_KEYS = frozenset({
    "complete_turns", "turns_with_usage", "failed_turns",
    "input_tokens", "cached_input_tokens", "output_tokens",
})
ARMS = ("baseline", "candidate")


def _integer(value):
    return type(value) is int and value >= 0


def _number(value):
    return type(value) in (int, float) and 0 <= value < float("inf")


def analyze(data):
    if not isinstance(data, dict) or set(data) != {"schema_version", "runs"}:
        raise ValueError("invalid document shape")
    if data["schema_version"] != 1 or type(data["schema_version"]) is not int:
        raise ValueError("unsupported schema version")
    runs = data["runs"]
    if not isinstance(runs, list) or not runs:
        raise ValueError("runs missing")

    pairs = {}
    fingerprint = None
    agents_by_arm = {}
    for run in runs:
        if not isinstance(run, dict) or set(run) != RUN_KEYS:
            raise ValueError("invalid run shape")
        arm = run["arm"]
        if arm not in ARMS or not _integer(run["pair"]) or run["pair"] < 1:
            raise ValueError("invalid pair or arm")
        key = run["pair"]
        if arm in pairs.setdefault(key, {}):
            raise ValueError("duplicate pair/arm")
        if not isinstance(run["case_id"], str) or not run["case_id"].strip():
            raise ValueError("missing case")
        controls = run["controls"]
        if (not isinstance(controls, dict) or set(controls) != CONTROLS
                or any(not isinstance(v, str) or not v.strip() for v in controls.values())):
            raise ValueError("invalid controls")
        current = (run["case_id"], tuple(sorted(controls.items())))
        if fingerprint is None:
            fingerprint = current
        elif current != fingerprint:
            raise ValueError("unmatched controls")
        sha = run["agents_sha"]
        if not isinstance(sha, str) or len(sha) < 12 or not all(c in "0123456789abcdef" for c in sha.lower()):
            raise ValueError("invalid AGENTS fingerprint")
        previous = agents_by_arm.setdefault(arm, sha)
        if previous != sha:
            raise ValueError("unstable AGENTS fingerprint")
        if any(type(run[key]) is not bool for key in ("success", "delegated", "parent_orchestrated", "safety_pass")):
            raise ValueError("invalid behavioral assertions")
        if not _integer(run["retries"]) or not _number(run["elapsed_s"]):
            raise ValueError("invalid retries or elapsed")
        usage = run["usage"]
        if not isinstance(usage, dict) or set(usage) != USAGE_KEYS:
            raise ValueError("invalid usage")
        if not all(_integer(value) for value in usage.values()):
            raise ValueError("negative or invalid usage")
        if usage["cached_input_tokens"] > usage["input_tokens"]:
            raise ValueError("cached exceeds input")
        pairs[key][arm] = run

    if set(agents_by_arm) != set(ARMS) or agents_by_arm["baseline"] == agents_by_arm["candidate"]:
        raise ValueError("variants missing or identical")
    if sorted(pairs) != list(range(1, len(pairs) + 1)):
        raise ValueError("pair numbering must be consecutive")
    if any(set(pair_runs) != set(ARMS) for pair_runs in pairs.values()):
        raise ValueError("incomplete pairs")

    def median(arm, fn):
        return statistics.median(fn(pairs[k][arm]) for k in sorted(pairs))

    def uncached(r):
        return r["usage"]["input_tokens"] - r["usage"]["cached_input_tokens"]

    def total_input(r):
        return r["usage"]["input_tokens"]

    def elapsed(r):
        return r["elapsed_s"]

    def valid_run(r):
        u = r["usage"]
        return (r["success"] and r["delegated"] and r["parent_orchestrated"]
                and r["safety_pass"] and u["complete_turns"] > 0
                and u["turns_with_usage"] == u["complete_turns"]
                and u["failed_turns"] == 0)

    quality = all(valid_run(r) for paired in pairs.values() for r in paired.values())
    stats = {}
    for arm in ARMS:
        runs_arm = [p[arm] for p in pairs.values()]
        stats[arm] = {
            "median_input_tokens": median(arm, total_input),
            "median_uncached_input_tokens": median(arm, uncached),
            "median_output_tokens": median(arm, lambda r: r["usage"]["output_tokens"]),
            "median_elapsed_s": median(arm, elapsed),
            "total_retries": sum(r["retries"] for r in runs_arm),
            "passed_runs": sum(valid_run(r) for r in runs_arm),
        }

    def change_pct(field):
        old = stats["baseline"][field]
        new = stats["candidate"][field]
        return round((new - old) * 100.0 / old, 2) if old else None

    uncached_delta = change_pct("median_uncached_input_tokens")
    elapsed_delta = change_pct("median_elapsed_s")
    enough = len(pairs) >= 3
    no_regression = (uncached_delta is not None and uncached_delta <= 0
                     and elapsed_delta is not None and elapsed_delta <= 15
                     and stats["candidate"]["total_retries"] <= stats["baseline"]["total_retries"])
    if not quality:
        status = "behavior_or_usage_regression"
    elif not enough:
        status = "insufficient_repetitions"
    elif no_regression:
        status = "manual_review_candidate"
    else:
        status = "metrics_inconclusive"

    return {
        "schema_version": 1,
        "pair_count": len(pairs),
        "behavior_and_usage_complete": quality,
        "statistics": stats,
        "uncached_input_change_pct": uncached_delta,
        "elapsed_change_pct": elapsed_delta,
        "status": status,
        "merge_authorized": False,
        "accounting_note": "CLI counters only: not ChatGPT/Codex subscription quota.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Locally prepared sanitized A/B JSON file")
    args = parser.parse_args()
    try:
        data = json.loads(Path(args.input).read_text(encoding="utf-8"))
        result = analyze(data)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        print("Invalid sanitized A/B data or unmatched trial controls (input not echoed).", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "manual_review_candidate" else 1


if __name__ == "__main__":
    sys.exit(main())

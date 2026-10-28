#!/usr/bin/env python3
"""P1.2: anonymized configured-vs-observed tool-surface reconciliation.

Uses only local config.toml and already documented October 2026 observations.
Does not run Codex, start MCP servers, call a model, or inspect auth/sessions.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys

POLICY = Path(__file__).with_name("Get-CodexMcpPolicyAudit.py")
spec = importlib.util.spec_from_file_location("codex_mcp_policy_audit", POLICY)
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)

# Reproduce only the existing *historical* TUI observation documented in
# docs/QUALIFICATION_ROADMAP_2026.md. These are not measured anew.
OBSERVED_AT = "2026-10-28"
OBSERVED_TOOLS = {
    "local_configured_mcp": {
        "code-review-graph": 30,
        "context7": 2,
        "node_repl": 4,
        "playwright": 25,
    },
    "managed_app_bridge": {"codex_apps": 258},
    "codex_internal": {"codex_tui": 12, "cua_repl": 3},
    "nonfunctional_or_inactive": {"codex_app": 0, "oracle_reflex": 0},
}
# Classify *server names* only in memory. No names or commands leave the audit.
FUNCTIONS = {
    "code-review-graph": "code_navigation",
    "context7": "documentation",
    "node_repl": "javascript_repl",
    "playwright": "browser_automation",
}


def make_report(config: Path) -> dict[str, object]:
    summary = policy.audit(config, include_names=False)

    # This separate in-memory read is needed only to classify the four known
    # server roles. Keep names/paths/arguments/credentials OUT of the output.
    try:
        with config.open("rb") as stream:
            import tomllib
            data = tomllib.load(stream)
    except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
        raise ValueError("Cannot parse Codex MCP configuration; details withheld.") from None
    servers = data.get("mcp_servers", {})
    if not isinstance(servers, dict):
        raise ValueError("Invalid MCP server configuration; details withheld.")

    by_function = {
        "code_navigation": 0,
        "documentation": 0,
        "javascript_repl": 0,
        "browser_automation": 0,
        "other_or_private": 0,
    }
    for name, details in servers.items():
        if not isinstance(name, str) or not isinstance(details, dict):
            raise ValueError("Invalid MCP server configuration; details withheld.")
        kind = FUNCTIONS.get(name, "other_or_private")
        by_function[kind] += 1

    return {
        "schema_version": 1,
        "audit": "configured_vs_historical_observed_not_model_exposure",
        "model_calls_made": 0,
        "codex_processes_started": 0,
        "mcp_servers_started": 0,
        "local_config_now": {
            "configured_servers": summary["configured_servers"],
            "declared_enabled_servers": summary["declared_enabled_servers"],
            "declared_disabled_servers": summary["declared_disabled_servers"],
            "transport_counts": summary["transport_counts"],
            "servers_with_allowlist": summary["servers_with_allowlist"],
            "servers_with_denylist": summary["servers_with_denylist"],
            "review_flag_counts": summary["review_flag_counts"],
            "function_classification": by_function,
            "classification_limit": "Names classified in memory; cannot infer server readiness or tool count.",
        },
        "historical_tui_observation": {
            "observed_at": OBSERVED_AT,
            "provenance": "docs/QUALIFICATION_ROADMAP_2026.md (previously verified TUI /mcp observation)",
            "surfaces": [
                {
                    "origin_class": origin,
                    "surface_count": len(values),
                    "listed_tool_count": sum(values.values()),
                    "confidence": "historical_user_observed_not_current",
                }
                for origin, values in OBSERVED_TOOLS.items()
            ],
            "listed_total_not_safe_to_sum_as_unique_or_loaded": True,
        },
        "unknown_metrics": {
            "actual_connected_mcp_servers_now": None,
            "current_codex_apps_tools": None,
            "current_codex_tui_tools": None,
            "current_cua_repl_tools": None,
            "actual_tool_names_and_schemas_in_model_turn": None,
            "actual_tool_schema_token_overhead": None,
            "duplicate_tools_across_surfaces": None,
            "worker_specific_tool_access": None,
        },
        "decision": "NO_GLOBAL_CHANGES_OR_TOKEN_SAVINGS_CLAIM",
        "privacy": "No credentials, paths, MCP names, commands, arguments, private tool definitions or chat logs printed; no network, Codex process or new model calls.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    parser.add_argument("--config", type=Path, default=default_home / "config.toml")
    args = parser.parse_args(argv)
    try:
        result = make_report(args.config)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

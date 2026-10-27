#!/usr/bin/env python3
"""Privacy-limited static audit of Codex MCP TOML policies. Python >= 3.11."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tomllib


def _list_policy(value: object) -> tuple[int | None, set[str] | None]:
    if value is None:
        return None, None
    if not isinstance(value, list) or any(not isinstance(x, str) for x in value):
        raise ValueError("Invalid MCP tool policy array; configuration details withheld.")
    return len(value), set(value)


def audit(config: Path, include_names: bool = False) -> dict[str, object]:
    # Read only the explicit config file. Do not inspect auth.json, sessions, logs,
    # environment variable values, credentials, or project source files.
    try:
        with config.open("rb") as handle:
            data = tomllib.load(handle)
    except FileNotFoundError as exc:
        raise ValueError("Codex config.toml was not found.") from exc
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ValueError("Could not read or parse Codex TOML config; contents withheld.") from exc

    configured = data.get("mcp_servers", {})
    if not isinstance(configured, dict):
        raise ValueError("Invalid mcp_servers table; contents withheld.")

    rows: list[dict[str, object]] = []
    enabled_count = 0
    disabled_count = 0
    transport_counts = {"stdio": 0, "http": 0, "mixed": 0, "unspecified": 0}
    with_allow = 0
    with_deny = 0
    issues: dict[str, int] = {}
    for index, name in enumerate(sorted(configured), 1):
        cfg = configured[name]
        if not isinstance(cfg, dict):
            raise ValueError("Invalid MCP server table; contents withheld.")
        enabled = cfg.get("enabled", True)
        if not isinstance(enabled, bool):
            raise ValueError("Nonboolean MCP enabled flag; contents withheld.")
        if enabled:
            enabled_count += 1
        else:
            disabled_count += 1

        has_command = "command" in cfg
        has_url = "url" in cfg
        transport = (
            "mixed" if has_command and has_url
            else "stdio" if has_command
            else "http" if has_url
            else "unspecified"
        )
        transport_counts[transport] += 1

        allow_count, allow = _list_policy(cfg.get("enabled_tools"))
        deny_count, deny = _list_policy(cfg.get("disabled_tools"))
        with_allow += allow_count is not None
        with_deny += deny_count is not None
        overlap_count = len(allow & deny) if allow is not None and deny is not None else 0

        flags: list[str] = []
        if transport in ("unspecified", "mixed"):
            flags.append("transport_needs_review")
        if enabled and allow_count == 0:
            flags.append("enabled_with_empty_allowlist")
        if overlap_count:
            flags.append("allow_deny_overlap")
        for flag in flags:
            issues[flag] = issues.get(flag, 0) + 1

        row: dict[str, object] = {
            "slot": f"mcp_{index:02d}",
            "declared_enabled": enabled,
            "transport": transport,
            "allowlist_count": allow_count,
            "denylist_count": deny_count,
            "allow_deny_overlap_count": overlap_count,
            "review_flags": flags,
        }
        if include_names:
            row["server_name"] = name
        rows.append(row)

    plugins = data.get("plugins", {})
    plugin_mcp_policy_blocks = 0
    if isinstance(plugins, dict):
        for info in plugins.values():
            if isinstance(info, dict) and isinstance(info.get("mcp_servers"), dict):
                plugin_mcp_policy_blocks += len(info["mcp_servers"])

    return {
        "audit_kind": "configuration_only_not_runtime_tool_inventory",
        "source": "local Codex TOML file",
        "configured_servers": len(rows),
        "declared_enabled_servers": enabled_count,
        "declared_disabled_servers": disabled_count,
        "transport_counts": transport_counts,
        "servers_with_allowlist": with_allow,
        "servers_with_denylist": with_deny,
        "review_flag_counts": issues,
        "plugin_mcp_policy_blocks": plugin_mcp_policy_blocks,
        "servers": rows,
        "runtime_mcp_tools_discovered": None,
        "model_visible_tool_schemas": None,
        "token_attribution": None,
        "note": "Configured does not mean started, connected or exposed. Neither plugins nor project/managed overrides are fully resolved.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect Codex MCP configuration policy without starting servers or printing credentials."
    )
    default_home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    parser.add_argument("--config", type=Path, default=default_home / "config.toml")
    parser.add_argument("--include-names", action="store_true",
                        help="Opt-in: include MCP server identifiers only. Do not post if sensitive.")
    args = parser.parse_args()
    try:
        print(json.dumps(audit(args.config, args.include_names), indent=2, ensure_ascii=True))
    except ValueError as exc:
        # Hide the original TOML parse exception, which can contain private paths.
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

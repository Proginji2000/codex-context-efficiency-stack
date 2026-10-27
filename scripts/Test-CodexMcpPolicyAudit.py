#!/usr/bin/env python3
"""Synthetic read-only tests for Get-CodexMcpPolicyAudit.py."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile


SCRIPT = Path(__file__).with_name("Get-CodexMcpPolicyAudit.py")
SECRET_MARKERS = (
    "PRIVATE_SERVER_ACME",
    "TOP_SECRET_CREDENTIAL",
    "private.example.internal",
    "READ_TOKEN_SECRET",
)


def run_cli(path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--config", str(path), *extra],
        capture_output=True, text=True, check=False, timeout=15
    )


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="codex_mcp_audit_test_") as temp:
        config = Path(temp) / "config.toml"
        config.write_text(
            '''
[mcp_servers.PRIVATE_SERVER_ACME]
command = "npx"
args = ["-y", "secret-package"]
env = { API_KEY = "TOP_SECRET_CREDENTIAL" }
enabled_tools = ["one", "two"]
disabled_tools = ["two"]

[mcp_servers.remote_private]
url = "https://private.example.internal/with-token"
enabled = false

[mcp_servers.empty_allowlist]
command = "python"
enabled_tools = []

[mcp_servers.simple_http]
url = "https://service.invalid"
disabled_tools = ["unsafe"]

[plugins.private_plugin.mcp_servers.server_policy]
enabled_tools = ["READ_TOKEN_SECRET"]
'''.lstrip(), encoding="utf-8"
        )
        result = run_cli(config)
        assert result.returncode == 0, "Synthetic audit failed."
        summary = json.loads(result.stdout)
        assert summary["configured_servers"] == 4
        assert summary["declared_enabled_servers"] == 3
        assert summary["declared_disabled_servers"] == 1
        assert summary["transport_counts"]["stdio"] == 2
        assert summary["transport_counts"]["http"] == 2
        assert summary["servers_with_allowlist"] == 2
        assert summary["servers_with_denylist"] == 2
        assert summary["review_flag_counts"]["allow_deny_overlap"] == 1
        assert summary["review_flag_counts"]["enabled_with_empty_allowlist"] == 1
        assert summary["plugin_mcp_policy_blocks"] == 1
        assert all("server_name" not in row for row in summary["servers"])
        assert all(marker not in result.stdout + result.stderr for marker in SECRET_MARKERS)
        assert temp not in result.stdout
        assert summary["runtime_mcp_tools_discovered"] is None

        explicit = run_cli(config, "--include-names")
        assert explicit.returncode == 0
        explicit_data = json.loads(explicit.stdout)
        assert any(row.get("server_name") == "PRIVATE_SERVER_ACME" for row in explicit_data["servers"])
        assert all(marker not in explicit.stdout for marker in SECRET_MARKERS[1:])
        assert temp not in explicit.stdout

        bad = Path(temp) / "invalid.toml"
        bad.write_text('[mcp_servers.invalid]\nurl = "TOP_SECRET_CREDENTIAL"\n$not-toml\n', encoding="utf-8")
        bad_result = run_cli(bad)
        assert bad_result.returncode != 0
        assert "TOP_SECRET_CREDENTIAL" not in bad_result.stderr
        assert temp not in bad_result.stderr

        missing = run_cli(Path(temp) / "missing.toml")
        assert missing.returncode != 0
        assert temp not in missing.stderr

    print("[OK] TOML MCP server transport, enablement and tool-policy counts.")
    print("[OK] Plugin policy block count, sanitized default output, explicit name opt-in.")
    print("[OK] Invalid and missing TOML rejected without leaking config values.")
    print("PASS: offline MCP policy audit; no Codex process or server invocation.")


if __name__ == "__main__":
    main()

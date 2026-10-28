#!/usr/bin/env python3
"""Offline synthetic validation of the P1.2 tool-surface report."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

SCRIPT = Path(__file__).with_name("Get-CodexToolSurfaceInventory.py")
SECRET_STRINGS = (
    "PRIVATE_CUSTOM_SERVER",
    "PRIVATE_AUTH_KEY_123",
    "https://private.invalid/internal",
    "supersecretcommand",
)


def call(config: Path):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--config", str(config)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        encoding="utf-8", timeout=20, check=False,
    )


def main():
    with tempfile.TemporaryDirectory(prefix="codex_tools_p12_") as temp:
        config = Path(temp) / "config.toml"
        config.write_text(
            """
[mcp_servers.code-review-graph]
command = "crg"
[mcp_servers.context7]
command = "context7"
[mcp_servers.node_repl]
command = "node"
[mcp_servers.playwright]
command = "playwright"
[mcp_servers.PRIVATE_CUSTOM_SERVER]
command = "supersecretcommand"
args = ["PRIVATE_AUTH_KEY_123"]
url = "https://private.invalid/internal"
enabled = false
""".lstrip(), encoding="utf-8",
        )
        output = call(config)
        assert output.returncode == 0, "Expected successful synthetic config."
        data = json.loads(output.stdout)
        assert data["schema_version"] == 1
        assert data["model_calls_made"] == 0
        assert data["codex_processes_started"] == 0
        assert data["mcp_servers_started"] == 0
        local = data["local_config_now"]
        assert local["configured_servers"] == 5
        assert local["declared_enabled_servers"] == 4
        assert local["declared_disabled_servers"] == 1
        assert local["function_classification"] == {
            "code_navigation": 1,
            "documentation": 1,
            "javascript_repl": 1,
            "browser_automation": 1,
            "other_or_private": 1,
        }
        obs = {
            x["origin_class"]: x["listed_tool_count"]
            for x in data["historical_tui_observation"]["surfaces"]
        }
        assert obs == {
            "local_configured_mcp": 61,
            "managed_app_bridge": 258,
            "codex_internal": 15,
            "nonfunctional_or_inactive": 0,
        }
        assert data["historical_tui_observation"]["listed_total_not_safe_to_sum_as_unique_or_loaded"]
        assert all(v is None for v in data["unknown_metrics"].values())
        assert data["decision"] == "NO_GLOBAL_CHANGES_OR_TOKEN_SAVINGS_CLAIM"
        assert all(marker not in output.stdout + output.stderr for marker in SECRET_STRINGS)
        assert temp not in output.stdout + output.stderr
        assert "server_name" not in data["local_config_now"]

        missing = call(Path(temp) / "nonexistent" / "config.toml")
        assert missing.returncode != 0
        assert temp not in missing.stdout + missing.stderr

        invalid = Path(temp) / "invalid.toml"
        invalid.write_text(
            '[mcp_servers.PRIVATE_CUSTOM_SERVER]\n'
            'url="https://private.invalid/internal"\n'
            'wrong TOML CONTENT \n', encoding="utf-8"
        )
        malformed = call(invalid)
        assert malformed.returncode != 0
        assert all(marker not in malformed.stderr for marker in SECRET_STRINGS)
        assert temp not in malformed.stderr

        empty = Path(temp) / "empty.toml"
        empty.write_text("# no MCP\n", encoding="utf-8")
        no_mcp = call(empty)
        assert no_mcp.returncode == 0
        assert json.loads(no_mcp.stdout)["local_config_now"]["configured_servers"] == 0

    print("PASS: P1.2 tool-surface inventory provenance, privacy, errors, zero-model checks.")


if __name__ == "__main__":
    main()

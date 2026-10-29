#!/usr/bin/env python3
"""P1.1 H1.2: OFFLINE contract checker for pinned app-server thread/start.

Default and --simulate are fully synthetic: no Codex process, network, model,
CODEX_HOME, filesystem mutations or secret/session inspection. Real thread
creation and Windows MXC effectiveness are NOT claimed by this tool.
"""
import argparse
import json
import ntpath
import re
import sys

CONTRACT = "p1.1-appserver-h12-thread-policy-design-v1"
CLI = "codex-cli 0.165.0"
MODEL = "gpt-6-luna"
EFFORT = "medium"
SYNTHETIC_WORKSPACE = r"C:\P11-ISOLATED\workspace"
SYNTHETIC_HOME = r"C:\P11-ISOLATED\codex-home"


class PolicyError(ValueError):
    """Allowlisted failure codes without raw source data."""


def canonical_windows_path(value):
    if not isinstance(value, str) or not value or not ntpath.isabs(value):
        raise PolicyError("INVALID_ABSOLUTE_PATH")
    if value.startswith("\\\\") or "\x00" in value or "\n" in value or "\r" in value:
        raise PolicyError("INVALID_ABSOLUTE_PATH")
    value = ntpath.normcase(ntpath.normpath(value))
    if not re.match(r"^[a-z]:\\", value):
        raise PolicyError("INVALID_DRIVE_PATH")
    return value


def within(root, candidate):
    r = canonical_windows_path(root)
    c = canonical_windows_path(candidate)
    return c == r or c.startswith(r.rstrip("\\") + "\\")


def request_for_workspace(workspace):
    canonical_windows_path(workspace)
    return {
        "id": 2,
        "method": "thread/start",
        "params": {
            "model": MODEL,
            "cwd": workspace,
            "approvalPolicy": "never",
            "sandbox": "workspace-write",
            "config": {
                "windows": {"sandbox": "mxc"},
                "model_reasoning_effort": EFFORT,
            },
            "ephemeral": True,
        },
    }


def validate(request, response, workspace, isolated_home):
    """Validate reported policy *echo only*, never attests OS enforcement."""
    w = canonical_windows_path(workspace)
    h = canonical_windows_path(isolated_home)
    if within(h, w) or within(w, h):
        raise PolicyError("HOME_AND_WORKSPACE_OVERLAP")
    if not isinstance(request, dict) or request.get("method") != "thread/start":
        raise PolicyError("INVALID_METHOD")
    params = request.get("params")
    if not isinstance(params, dict) or params != request_for_workspace(workspace)["params"]:
        raise PolicyError("POLICY_REQUEST_MISMATCH")
    if type(request.get("id")) is not int or request["id"] != 2:
        raise PolicyError("INVALID_RPC_ID")
    if not isinstance(response, dict) or response.get("id") != 2:
        raise PolicyError("INVALID_RPC_RESPONSE")
    if "jsonrpc" in response and response["jsonrpc"] != "2.0":
        raise PolicyError("INVALID_WIRE_VERSION")
    if "error" in response or not isinstance(response.get("result"), dict):
        raise PolicyError("RPC_REJECTED")
    r = response["result"]
    if r.get("approvalPolicy") != "never" or r.get("model") != MODEL:
        raise PolicyError("POLICY_ECHO_MISMATCH")
    if r.get("reasoningEffort") != EFFORT:
        raise PolicyError("REASONING_ECHO_MISMATCH")
    if canonical_windows_path(r.get("cwd")) != w:
        raise PolicyError("CWD_ECHO_MISMATCH")
    sandbox = r.get("sandbox")
    if not isinstance(sandbox, dict) or sandbox.get("type") != "workspaceWrite":
        raise PolicyError("SANDBOX_TYPE_MISMATCH")
    if sandbox.get("networkAccess") is not False:
        raise PolicyError("SANDBOX_NETWORK_UNPROVEN")
    # Codex rust-v0.165.0 SandboxPolicy.new_workspace_write_policy()
    # sets writable_roots: vec![]: cwd is implicitly writable. This list
    # contains *additional* roots, not the mandatory workspace itself.
    # Missing/malformed writableRoots remains a failure: do not confuse an
    # absent wire field with a valid, explicitly empty array.
    roots = sandbox.get("writableRoots")
    if not isinstance(roots, list):
        raise PolicyError("WRITABLE_ROOTS_MISSING")
    normalized = [canonical_windows_path(v) for v in roots]
    if len(set(normalized)) != len(normalized):
        raise PolicyError("WRITABLE_ROOTS_MISMATCH")
    if normalized and w not in normalized:
        raise PolicyError("WRITABLE_ROOTS_MISMATCH")
    if any(root not in (w, h) for root in normalized):
        raise PolicyError("UNEXPECTED_WRITABLE_ROOT")
    thread = r.get("thread")
    if not isinstance(thread, dict) or thread.get("ephemeral") is not True:
        raise PolicyError("THREAD_NOT_EPHEMERAL")
    if not isinstance(thread.get("id"), str) or not thread["id"]:
        raise PolicyError("THREAD_ID_ABSENT")
    if thread.get("turns") != []:
        raise PolicyError("TURNS_ALREADY_PRESENT")
    sources = r.get("instructionSources")
    if not isinstance(sources, list):
        raise PolicyError("INSTRUCTION_SOURCES_UNKNOWN")
    for source in sources:
        if not isinstance(source, str) or not (
            within(w, source) or within(h, source)
        ):
            raise PolicyError("INSTRUCTION_OUTSIDE_ISOLATION")
    return {
        "status": "SYNTHETIC_THREAD_POLICY_ECHO_PASS",
        "contract": CONTRACT,
        "wire_envelope": "codex_0165_versionless",
        "approval_echo": "never",
        "sandbox_echo": "workspaceWrite",
        "network_access_echo": False,
        "reasoning_effort_echo": EFFORT,
        "ephemeral_echo": True,
        "allowed_root_count": len(normalized),
        "implicit_cwd_write_by_pinned_contract": len(normalized) == 0,
        "instruction_source_count": len(sources),
        "thread_start_simulated": True,
        "turn_start_sent": False,
        "model_calls_made": 0,
        "real_app_server_connected": False,
        "real_thread_created": False,
        "worker_runtime_verified": False,
        "windows_mxc_runtime_verified": False,
        "network_isolation_runtime_verified": False,
        "candidate_merge_authorized": False,
    }


def synthetic_response(workspace, isolated_home):
    # No client origin/session identifiers or workspace paths are returned.
    return {
        "id": 2,
        "result": {
            "approvalPolicy": "never",
            "model": MODEL,
            "reasoningEffort": EFFORT,
            "cwd": workspace,
            "sandbox": {
                "type": "workspaceWrite",
                "writableRoots": [workspace],
                "networkAccess": False,
                "excludeTmpdirEnvVar": True,
                "excludeSlashTmp": True,
            },
            "thread": {
                "id": "SYNTHETIC-THREAD-ID-NOT-EXPORTED",
                "ephemeral": True,
                "turns": [],
            },
            "instructionSources": [],
        },
    }


def simulate():
    request = request_for_workspace(SYNTHETIC_WORKSPACE)
    response = synthetic_response(SYNTHETIC_WORKSPACE, SYNTHETIC_HOME)
    return validate(request, response, SYNTHETIC_WORKSPACE, SYNTHETIC_HOME)


def plan():
    return {
        "contract": CONTRACT,
        "mode": "OFFLINE_PLAN_ONLY",
        "pinned_cli": CLI,
        "protocol_schema": "openai/codex rust-v0.165.0",
        "next_proposed_messages": ["initialize", "initialized", "thread/start"],
        "next_proposed_messages_executed": False,
        "turn_start_allowed": False,
        "model_calls_made": 0,
        "real_app_server_connected": False,
        "real_thread_created": False,
        "approval_policy": "never",
        "sandbox_requested": "workspace-write",
        "windows_sandbox_requested": "mxc",
        "network_isolation_independently_verified": False,
        "windows_mxc_effective_policy_verified": False,
        "requires_separate_local_execution_authorization": True,
        "candidate_merge_authorized": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulate", action="store_true",
                        help="Validate a synthetic thread/start reply; never invoke Codex")
    args = parser.parse_args(argv)
    try:
        result = simulate() if args.simulate else plan()
    except (PolicyError, OSError, TypeError):
        print("STOP: H12_OFFLINE_POLICY_CHECK_FAILED", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Codex 0.165.0 app-server harness: plan and IN-MEMORY MOCK ONLY.

No socket/process, Codex invocation, auth/session read, workspace write, or model.
This is a contract prototype; it cannot attest real Windows MXC isolation.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parent
CONTRACT = "p1.1-appserver-instrumented-harness-design-v1"
CLI = "codex-cli 0.165.0"
MODEL = "gpt-6-luna"
WORKER = "luna-medium"
WORKSPACE_PLACEHOLDER = "/DISPOSABLE-WORKSPACE-PLACEHOLDER"
CLIENT = {"name": "codex-ab-harness-mock", "title": "P1.1 offline protocol test", "version": "0.1.0"}


class HarnessError(ValueError):
    """Fixed codes: no prompt, file path or source payload in errors."""


def load(name, alias):
    spec = importlib.util.spec_from_file_location(alias, SCRIPTS / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cases():
    return load("Plan-CodexAB-RepresentativeFixtures.py", "p11_cases").CASES


def event_auditor():
    return load("Audit-CodexAppServer-Events.py", "p11_audit")


def plan():
    result = []
    # Two repetitions per case; order balanced within each case.
    for case in cases():
        for repeat in (1, 2):
            for arm in (("candidate", "baseline") if repeat == 1 else ("baseline", "candidate")):
                result.append({
                    "case_id": case["id"],
                    "repeat": repeat,
                    "arm": arm,
                    "prompt_contract": CONTRACT,
                    "fixture_contract": "p1.1-representative-fixtures-design-v1",
                    "allowed_writes": list(case["allowed_writes"]),
                    "model": MODEL,
                    "worker": WORKER,
                    "sandbox_requested": "workspace-write",
                    "approval_requested": "never",
                    "windows_sandbox_requested": "mxc",
                    "reasoning_effort_requested": "medium",
                })
    return {
        "schema_version": 1,
        "contract": CONTRACT,
        "mode": "OFFLINE_PLAN_ONLY",
        "pinned_cli": CLI,
        "planned_runs_not_authorized": len(result),
        "case_count": len(cases()),
        "runs": result,
        "app_server_transport": "none",
        "model_calls": 0,
        "live_execution_implemented": False,
        "runtime_mxc_attested": False,
        "merge_pr14_authorized": False,
        "v2_v3_evidence_unchanged": True,
    }


def request(request_id, method, params):
    return {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}


def initialize_request():
    return request(1, "initialize", {"clientInfo": dict(CLIENT), "capabilities": None})


def thread_request(case):
    # config keys are PROPOSED only; their runtime support and precedence
    # are intentionally not asserted by the simulator.
    return request(2, "thread/start", {
        "model": MODEL,
        "cwd": WORKSPACE_PLACEHOLDER,
        "approvalPolicy": "never",
        "sandbox": "workspace-write",
        "config": {"windows": {"sandbox": "mxc"}, "model_reasoning_effort": "medium"},
        "ephemeral": True,
    })


def turn_request(case, thread_id):
    return request(3, "turn/start", {
        "threadId": thread_id,
        "input": [{"type": "text", "text": case["prompt"]}],
        "effort": "medium",
        "approvalPolicy": "never",
    })


def rpc_result(req, response):
    if not isinstance(response, dict) or response.get("jsonrpc") != "2.0":
        raise HarnessError("BAD_JSONRPC_ENVELOPE")
    if response.get("id") != req["id"] or "error" in response:
        raise HarnessError("RPC_ID_OR_ERROR")
    result = response.get("result")
    if not isinstance(result, dict):
        raise HarnessError("MISSING_RPC_RESULT")
    return result


def assert_thread_policy(req, response):
    result = rpc_result(req, response)
    params = req["params"]
    if (params.get("approvalPolicy") != "never"
            or params.get("sandbox") != "workspace-write"
            or params.get("model") != MODEL or params.get("ephemeral") is not True
            or params.get("config") != {"windows": {"sandbox": "mxc"}, "model_reasoning_effort": "medium"}):
        raise HarnessError("INVALID_THREAD_REQUEST")
    if result.get("model") != MODEL or result.get("approvalPolicy") != "never":
        raise HarnessError("POLICY_ECHO_MISMATCH")
    sandbox = result.get("sandbox")
    if (not isinstance(sandbox, dict)
            or sandbox.get("type") != "workspaceWrite"
            or sandbox.get("networkAccess") is not False
            or sandbox.get("writableRoots") != [WORKSPACE_PLACEHOLDER]):
        raise HarnessError("SANDBOX_ECHO_MISMATCH")
    if result.get("cwd") != WORKSPACE_PLACEHOLDER:
        raise HarnessError("WORKSPACE_ECHO_MISMATCH")
    thread = result.get("thread")
    if not isinstance(thread, dict) or not isinstance(thread.get("id"), str) or not thread["id"]:
        raise HarnessError("MISSING_THREAD_IDENTIFIER")
    return thread["id"]


def require_worker_events(events):
    report = event_auditor().audit(events)
    spawn = report["collab_calls"]["spawnAgent"]
    if (spawn["started"] != 1 or spawn["completed"] != 1
            or spawn["failed"] or spawn["interrupted"]
            or report["unpaired_collab_completions"]
            or report["subagent_started_and_completed_observed"] != 1
            or report["subagent_partial_activity_observed"] != 0
            or report["turn_outcomes"]["completed"] != 1
            or any(report["turn_outcomes"][status] for status in ("failed", "interrupted", "inProgress"))):
        raise HarnessError("WORKER_LIFECYCLE_INCOMPLETE")
    return {"spawn_started": 1, "spawn_completed": 1, "worker_completed_markers": 1,
            "completed_turns": 1}


class MockEndpoint:
    """No socket or model. Deterministic responses; never accepts exec calls."""

    def __init__(self):
        self.state = "created"
        self.thread_id = "SYNTHETIC_THREAD"
        self.messages = []

    def notify(self, notice):
        if notice != {"jsonrpc": "2.0", "method": "initialized"} or self.state != "initialized":
            raise HarnessError("INVALID_INITIALIZED_NOTIFICATION")
        self.messages.append("initialized")
        self.state = "ready"

    def call(self, req):
        self.messages.append(req["method"])
        if req["method"] == "initialize" and self.state == "created":
            self.state = "initialized"
            return {"jsonrpc": "2.0", "id": req["id"],
                    "result": {"userAgent": "synthetic", "platformFamily": "windows",
                               "platformOs": "windows", "codexHome": "/SYNTHETIC-NOT-REAL"}}
        if req["method"] == "thread/start" and self.state == "ready":
            self.state = "thread"
            return {"jsonrpc": "2.0", "id": req["id"], "result": {
                "thread": {"id": self.thread_id},
                "model": MODEL, "approvalPolicy": "never",
                "cwd": WORKSPACE_PLACEHOLDER,
                "sandbox": {"type": "workspaceWrite", "writableRoots": [WORKSPACE_PLACEHOLDER],
                            "networkAccess": False, "excludeTmpdirEnvVar": True,
                            "excludeSlashTmp": True},
            }}
        if req["method"] == "turn/start" and self.state == "thread":
            self.state = "turn"
            return {"jsonrpc": "2.0", "id": req["id"],
                    "result": {"turn": {"id": "SYNTHETIC_TURN", "status": "inProgress"}}}
        raise HarnessError("MOCK_ONLY_METHOD_OR_ORDER_FORBIDDEN")

    def synthetic_events(self):
        if self.state != "turn":
            raise HarnessError("MOCK_TURN_NOT_STARTED")
        tid = self.thread_id
        turn = "SYNTHETIC_TURN"
        base = {"threadId": tid, "turnId": turn}
        return [
            {"method": "item/started", "params": {**base, "item": {
                "type": "collabAgentToolCall", "id": "SYNTHETIC_SPAWN",
                "tool": "spawnAgent", "status": "inProgress"}}},
            {"method": "item/completed", "params": {**base, "item": {
                "type": "collabAgentToolCall", "id": "SYNTHETIC_SPAWN",
                "tool": "spawnAgent", "status": "completed",
                "receiverThreadIds": ["SYNTHETIC_WORKER"]}}},
            {"method": "item/completed", "params": {**base, "item": {
                "type": "subAgentActivity", "id": "SYNTHETIC_ACTIVITY_START",
                "agentThreadId": "SYNTHETIC_WORKER", "kind": "started"}}},
            {"method": "item/completed", "params": {**base, "item": {
                "type": "subAgentActivity", "id": "SYNTHETIC_ACTIVITY_END",
                "agentThreadId": "SYNTHETIC_WORKER", "kind": "completed"}}},
            {"method": "turn/completed", "params": {**base,
                "turn": {"id": turn, "status": "completed"}}},
        ]


def simulate(case, endpoint=None):
    """Only MockEndpoint is legal: guards against accidental live transport."""
    if endpoint is None:
        endpoint = MockEndpoint()
    if type(endpoint) is not MockEndpoint:
        raise HarnessError("LIVE_ENDPOINT_FORBIDDEN")
    valid = {c["id"]: c for c in cases()}
    if case not in valid:
        raise HarnessError("UNKNOWN_CASE")
    initialized = rpc_result(initialize_request(), endpoint.call(initialize_request()))
    if initialized.get("platformOs") != "windows":
        raise HarnessError("PLATFORM_MISMATCH")
    endpoint.notify({"jsonrpc": "2.0", "method": "initialized"})
    start = thread_request(valid[case])
    thread_id = assert_thread_policy(start, endpoint.call(start))
    turn = turn_request(valid[case], thread_id)
    t = rpc_result(turn, endpoint.call(turn))
    if t.get("turn", {}).get("status") != "inProgress":
        raise HarnessError("INVALID_TURN_STARTED")
    report = require_worker_events(endpoint.synthetic_events())
    return {
        "status": "SYNTHETIC_PROTOCOL_SIMULATION_PASS",
        "contract": CONTRACT, "case_id": case,
        "transport": "in_memory_mock_only",
        "request_sequence": list(endpoint.messages),
        "requested_policy": {"approval": "never", "sandbox": "workspace-write",
                             "windows_sandbox": "mxc", "effort": "medium"},
        "mock_echo_policy_validated": True,
        "synthetic_events": report,
        "model_calls": 0, "files_written": 0,
        "real_app_server_connected": False,
        "worker_delegation_independently_verified_in_runtime": False,
        "effective_mxc_policy_verified_in_runtime": False,
        "real_fixture_acceptance_verified": False,
        "live_execution_implemented": False,
        "merge_pr14_authorized": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulate", choices=[c["id"] for c in cases()],
                        help="In-memory fake server only; no Codex")
    args = parser.parse_args(argv)
    try:
        result = simulate(args.simulate) if args.simulate else plan()
    except (HarnessError, ValueError, TypeError, OSError):
        print("STOP: OFFLINE_HARNESS_CONTRACT_FAILED", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

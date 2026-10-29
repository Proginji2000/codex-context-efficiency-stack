#!/usr/bin/env python3
"""H1.3d strict OFFLINE-only MXC network isolation evidence design.

This file NEVER creates sockets, connects to an endpoint or runs Codex.
It assesses independently collected, *simulated or future* evidence with
fail-closed rules. A passing fabricated matrix is NOT a real network proof.
"""
import argparse
import json
import sys

CONTRACT = "p1.1-h13d-mxc-network-evidence-design-v1"
FIELDS = frozenset({
    "source", "windows_mxc_selected", "network_policy_declared_deny",
    "managed_proxy_mode_verified", "endpoint_owned_and_controlled",
    "endpoint_numeric_non_loopback", "host_can_connect_same_endpoint",
    "sandbox_attempt_observed", "sandbox_connect_result",
    "endpoint_observed_sandbox_connection",
    "independent_os_block_evidence", "sandbox_used_proxy_or_fallback",
})
DENIED = "explicit_policy_denied"
UNACCEPTABLE = frozenset({
    "success", "timeout", "dns_failure", "connection_refused",
    "unreachable", "unknown", "proxy_error", "skipped",
})


class EvidenceError(Exception):
    pass


def evaluate(evidence):
    """Strict and deliberately conservative; no IO or network operations."""
    if not isinstance(evidence, dict) or set(evidence) != FIELDS:
        raise EvidenceError("EVIDENCE_SHAPE_INVALID")
    if evidence["source"] != "real_independent_observation":
        raise EvidenceError("SYNTHETIC_EVIDENCE_NOT_RUNTIME")
    for key in FIELDS - {"source", "sandbox_connect_result"}:
        if type(evidence[key]) is not bool:
            raise EvidenceError("EVIDENCE_SHAPE_INVALID")
    result = evidence["sandbox_connect_result"]
    if not isinstance(result, str) or result not in UNACCEPTABLE | {DENIED}:
        raise EvidenceError("SANDBOX_CONNECT_RESULT_INVALID")
    if not evidence["windows_mxc_selected"]:
        raise EvidenceError("MXC_BACKEND_UNATTESTED")
    if not evidence["network_policy_declared_deny"]:
        raise EvidenceError("NETWORK_POLICY_NOT_DENY")
    if not evidence["managed_proxy_mode_verified"]:
        raise EvidenceError("NETWORK_PROXY_TOPOLOGY_UNVERIFIED")
    if not evidence["endpoint_owned_and_controlled"] or not evidence["endpoint_numeric_non_loopback"]:
        raise EvidenceError("NETWORK_ENDPOINT_NOT_CONTROLLED")
    if not evidence["host_can_connect_same_endpoint"]:
        raise EvidenceError("HOST_POSITIVE_CONTROL_FAILED")
    if not evidence["sandbox_attempt_observed"]:
        raise EvidenceError("SANDBOX_ATTEMPT_NOT_OBSERVED")
    if evidence["sandbox_used_proxy_or_fallback"]:
        raise EvidenceError("SANDBOX_USED_UNCONTROLLED_NETWORK_PATH")
    if evidence["endpoint_observed_sandbox_connection"]:
        raise EvidenceError("NETWORK_ESCAPE_OBSERVED")
    if result != DENIED:
        raise EvidenceError("NETWORK_DENIAL_NOT_ATTRIBUTABLE")
    if not evidence["independent_os_block_evidence"]:
        raise EvidenceError("NETWORK_OS_DENY_UNATTESTED")
    return {
        "contract": CONTRACT,
        "status": "H13D_EVIDENCE_CONDITIONS_SATISFIED_NOT_RUNTIME",
        "network_egress_real_verified": False,
        "actual_network_io_run_by_this_tool": False,
        "appserver_turn_mxc_verified": False,
        "worker_provenance_verified": False,
        "model_calls_made": 0,
        "candidate_merge_authorized": False,
    }


def fabricated_sample():
    return {
        "source": "fabricated",
        "windows_mxc_selected": True,
        "network_policy_declared_deny": True,
        "managed_proxy_mode_verified": True,
        "endpoint_owned_and_controlled": True,
        "endpoint_numeric_non_loopback": True,
        "host_can_connect_same_endpoint": True,
        "sandbox_attempt_observed": True,
        "sandbox_connect_result": DENIED,
        "endpoint_observed_sandbox_connection": False,
        "independent_os_block_evidence": True,
        "sandbox_used_proxy_or_fallback": False,
    }


def plan():
    return {
        "contract": CONTRACT,
        "mode": "PLAN_ONLY_NO_NETWORK_OR_PROCESS",
        "target_cli": "codex-cli 0.165.0",
        "mxc_network_policy_note": "direct vs managed proxy must be distinguished",
        "localhost_only_test_is_not_valid_isolation_proof": True,
        "timeouts_dns_errors_or_unreachable_endpoint_are_not_denial_proof": True,
        "real_test_implemented": False,
        "operator_owned_numeric_non_loopback_endpoint_needed": True,
        "future_runtime_requires_separate_opt_in": True,
        "real_network_egress_verified": False,
        "appserver_turn_mxc_verified": False,
        "worker_provenance_verified": False,
        "model_calls_made": 0,
        "candidate_merge_authorized": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulate", action="store_true",
                        help="Offline fabricated negative self-check, never runtime")
    args = parser.parse_args(argv)
    if args.simulate:
        try:
            evaluate(fabricated_sample())
        except EvidenceError as exc:
            if str(exc) != "SYNTHETIC_EVIDENCE_NOT_RUNTIME":
                print("STOP: H13D_OFFLINE_MATRIX_INVALID", file=sys.stderr)
                return 2
        else:
            print("STOP: H13D_FABRICATED_INPUT_ACCEPTED_AS_RUNTIME", file=sys.stderr)
            return 2
        value = {
            "contract": CONTRACT,
            "status": "H13D_FABRICATED_INPUT_REJECTED_PASS",
            "fabricated_only": True,
            "actual_network_io_run_by_this_tool": False,
            "real_network_egress_verified": False,
            "model_calls_made": 0,
        }
    else:
        value = plan()
    print(json.dumps(value, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

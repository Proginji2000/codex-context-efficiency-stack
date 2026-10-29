#!/usr/bin/env python3
"""P1.1 H1.3 design-only matrix for standalone Windows MXC negative tests.

No subprocess, no file access, no network, no real OS sandbox, no model.
--simulate verifies only a constructed example, NOT any runtime evidence.
A separate explicitly authorized runtime launcher is required later.
"""
import argparse
import json
import sys

CONTRACT = "p1.1-h13-windows-mxc-standalone-design-v1"

# These are prospective evidence predicates, not measurements.
REQUIRED = {
    "pinned_cli_0165": True,
    "non_admin_parent": True,
    "new_codex_home": True,
    "new_disposable_workspace": True,
    "backend_explicit_mxc": True,
    "no_automatic_setup_or_install": True,
    "unsandboxed_outside_control_writable": True,
    "sandbox_workspace_write_succeeded": True,
    "sandbox_outside_write_denied": True,
    "outside_sentinel_unchanged": True,
    "no_global_config_mutation": True,
    "no_turn_start": True,
    "no_model_call": True,
}


class MatrixError(ValueError):
    pass


def plan():
    return {
        "contract": CONTRACT,
        "mode": "PLAN_ONLY_NO_PROCESS",
        "target_cli": "codex-cli 0.165.0",
        "scope": "standalone_cli_sandbox_not_appserver_turn",
        "official_cli_entry": "codex sandbox",
        "official_backend_selection": "windows.sandbox=mxc",
        "parent_permission": "non_admin_only",
        "test_environment": "fresh_temporary_codex_home_and_disposable_workspace",
        "positive_control": "write_inside_disposable_workspace",
        "negative_control": "outside_disposable_workspace_write_denied",
        "host_control": "outside_sentinel_confirmed_writable_without_sandbox",
        "independent_evidence": "outside_sentinel_unchanged_after_child",
        "fail_closed": True,
        "model_calls_made": 0,
        "thread_start_sent": False,
        "turn_start_sent": False,
        "standalone_runtime_mxc_verified": False,
        "appserver_turn_runtime_mxc_verified": False,
        "network_isolation_verified": False,
        "worker_provenance_verified": False,
        "complete_child_tree_cleanup_verified": False,
        "user_approved_runtime_run": False,
        "proposed_runtime_launcher_implemented": False,
        "future_gates": [
            "H1.3a_standalone_mxc_runtime_negative_test",
            "H1.3b_appserver_turn_mxc_runtime_parity_requires_separate_approval",
            "H1.3c_worker_lifecycle_and_process_tree_attestation",
            "H1.3d_network_isolation_independent_check",
        ],
        "required_runtime_evidence_keys": sorted(REQUIRED),
    }


def simulate_evidence():
    """Only a fabricated fixture: proves this decision matrix is consistent."""
    return {"source": "SYNTHETIC_FIXTURE", **REQUIRED}


def evaluate_synthetic_evidence(candidate):
    if not isinstance(candidate, dict) or candidate.get("source") != "SYNTHETIC_FIXTURE":
        raise MatrixError("SOURCE_NOT_SYNTHETIC")
    if set(candidate) != set(REQUIRED) | {"source"}:
        raise MatrixError("EVIDENCE_SCHEMA_MISMATCH")
    for key, expected in REQUIRED.items():
        if candidate[key] is not expected:
            raise MatrixError("EVIDENCE_PREDICATE_FAILED")
    return {
        "contract": CONTRACT,
        "status": "SYNTHETIC_H13_MATRIX_PASS_NOT_RUNTIME",
        "criteria_count": len(REQUIRED),
        "all_inputs_fabricated": True,
        "real_mxc_process_launched": False,
        "standalone_runtime_mxc_verified": False,
        "appserver_turn_runtime_mxc_verified": False,
        "network_isolation_verified": False,
        "worker_provenance_verified": False,
        "model_calls_made": 0,
        "candidate_merge_authorized": False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--simulate", action="store_true", help="Fabricated evidence only")
    args = p.parse_args(argv)
    try:
        output = evaluate_synthetic_evidence(simulate_evidence()) if args.simulate else plan()
    except MatrixError:
        print("STOP: H13_SYNTHETIC_MATRIX_FAILED", file=sys.stderr)
        return 2
    print(json.dumps(output, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

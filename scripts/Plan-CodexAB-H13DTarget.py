#!/usr/bin/env python3
"""P1.1 H1.3d: OFFLINE-only controlled LAN target eligibility gate.

No sockets, DNS, subprocesses, Codex, model calls, file writes, or endpoint
connections. Only parse explicit addresses supplied by operator. Values stay
in memory and are never reproduced in output or exception messages.

A candidate is NOT a verified reachable service or network-isolation proof.
"""
import argparse
import ipaddress
import json
import sys

CONTRACT = "p1.1-h13d-controlled-target-eligibility-v1"
RFC1918 = tuple(ipaddress.IPv4Network(x) for x in (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))
SAFE_CODES = frozenset({
    "TARGET_DETAILS_INCOMPLETE", "TARGET_IP_INVALID",
    "TARGET_NOT_RFC1918_IPV4", "TARGET_ADDRESS_UNSUITABLE",
    "TARGET_EQUALS_LOCAL_HOST", "TARGET_DIFFERENT_MACHINE_NOT_CONFIRMED",
    "TARGET_OWNERSHIP_NOT_CONFIRMED", "TARGET_PORT_NOT_ALLOWED",
    "LOCAL_ADDRESS_INVENTORY_MISSING", "LOCAL_ADDRESS_INVALID",
    "LOCAL_ADDRESS_INVENTORY_INCOMPLETE",
})


class GateError(Exception):
    pass


def ipv4(value, invalid_code):
    if not isinstance(value, str) or value.strip() != value:
        raise GateError(invalid_code)
    try:
        parsed = ipaddress.ip_address(value)
    except ValueError:
        raise GateError(invalid_code) from None
    if not isinstance(parsed, ipaddress.IPv4Address):
        raise GateError(invalid_code)
    return parsed


def rfc1918(address):
    return isinstance(address, ipaddress.IPv4Address) and any(
        address in net for net in RFC1918)


def eligible_target(address, port, local_addresses,
                    remote_machine_confirmed, ownership_confirmed,
                    local_inventory_complete):
    """Evaluate explicit operator declarations; never inspect network."""
    if type(port) is not int or not 20000 <= port <= 60999:
        raise GateError("TARGET_PORT_NOT_ALLOWED")
    dest = ipv4(address, "TARGET_IP_INVALID")
    if not rfc1918(dest):
        raise GateError("TARGET_NOT_RFC1918_IPV4")
    if dest.packed[-1] in (0, 255):
        # Conservative lab preflight; avoid a likely /24 network/broadcast.
        raise GateError("TARGET_ADDRESS_UNSUITABLE")
    if not isinstance(local_addresses, (tuple, list)) or not local_addresses:
        raise GateError("LOCAL_ADDRESS_INVENTORY_MISSING")
    if len(local_addresses) > 48:
        raise GateError("LOCAL_ADDRESS_INVALID")
    local = [ipv4(v, "LOCAL_ADDRESS_INVALID") for v in local_addresses]
    if len(set(local)) != len(local):
        raise GateError("LOCAL_ADDRESS_INVALID")
    if dest in local:
        raise GateError("TARGET_EQUALS_LOCAL_HOST")
    for flag in (remote_machine_confirmed, ownership_confirmed,
                 local_inventory_complete):
        if type(flag) is not bool:
            raise GateError("TARGET_DETAILS_INCOMPLETE")
    if not local_inventory_complete:
        raise GateError("LOCAL_ADDRESS_INVENTORY_INCOMPLETE")
    if not remote_machine_confirmed:
        raise GateError("TARGET_DIFFERENT_MACHINE_NOT_CONFIRMED")
    if not ownership_confirmed:
        raise GateError("TARGET_OWNERSHIP_NOT_CONFIRMED")
    return {
        "contract": CONTRACT,
        "status": "H13D_TARGET_CANDIDATE_ELIGIBLE_OFFLINE_NOT_RUNTIME",
        "mode": "OPERATOR_DECLARED_TARGET_CHECK_NO_IO",
        "target_ip_rfc1918": True,
        "target_is_not_listed_local_address": True,
        "target_port_unprivileged_lab_range": True,
        "local_address_inventory_declared_complete": True,
        "remote_machine_ownership_operator_declared_only": True,
        "remote_endpoint_reachability_verified": False,
        "network_policy_effective_verified": False,
        "managed_proxy_topology_verified": False,
        "host_positive_control_observed": False,
        "sandbox_network_attempt_observed": False,
        "independent_os_block_observed": False,
        "actual_network_io_run": False,
        "real_network_egress_verified": False,
        "appserver_turn_mxc_verified": False,
        "model_calls_made": 0,
        "candidate_merge_authorized": False,
    }


def plan():
    return {
        "contract": CONTRACT,
        "mode": "PLAN_ONLY_NO_NETWORK_OR_PROCESS",
        "status": "CONTROLLED_REMOTE_TARGET_NOT_SELECTED",
        "remote_machine_required": True,
        "suggested_scope": "operator-owned independent machine on RFC1918 LAN",
        "candidate_and_local_addresses_never_printed": True,
        "target_service_running_or_authorized": False,
        "actual_network_io_run": False,
        "real_network_egress_verified": False,
        "operator_owned_target_confirmation_required": True,
        "host_positive_control_observed": False,
        "model_calls_made": 0,
    }


def safe_error(exc):
    if isinstance(exc, GateError) and len(exc.args) == 1 and exc.args[0] in SAFE_CODES:
        return exc.args[0]
    return "TARGET_VALIDATION_FAILED"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-ip", default=None)
    parser.add_argument("--candidate-port", type=int, default=None)
    parser.add_argument("--local-ip", action="append", default=[])
    parser.add_argument("--local-inventory-complete", action="store_true")
    parser.add_argument("--controlled-remote-machine", action="store_true")
    parser.add_argument("--endpoint-owned", action="store_true")
    args = parser.parse_args(argv)
    if (args.candidate_ip is None and args.candidate_port is None
            and not args.local_ip and not args.local_inventory_complete
            and not args.controlled_remote_machine and not args.endpoint_owned):
        result = plan()
    else:
        try:
            result = eligible_target(
                args.candidate_ip, args.candidate_port, args.local_ip,
                args.controlled_remote_machine, args.endpoint_owned,
                args.local_inventory_complete)
        except GateError as exc:
            print("STOP: H13D_TARGET_GATE:" + safe_error(exc), file=sys.stderr)
            return 2
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Offline-only tests for controlled remote LAN target gate. No connections."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import unittest

SCRIPT = Path(__file__).with_name("Plan-CodexAB-H13DTarget.py")
SPEC = importlib.util.spec_from_file_location("h13d_target", SCRIPT)
p = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p)


class H13dTargetGateTests(unittest.TestCase):
    def good(self):
        return {
            "address": "192.168.1.101",
            "port": 42589,
            "local_addresses": ["192.168.1.40", "10.85.0.1"],
            "remote_machine_confirmed": True,
            "ownership_confirmed": True,
            "local_inventory_complete": True,
        }

    def evaluate(self, **kw):
        obj = self.good()
        obj.update(kw)
        return p.eligible_target(**obj)

    def assert_gate_error(self, code, **kw):
        with self.assertRaises(p.GateError) as caught:
            self.evaluate(**kw)
        self.assertEqual(p.safe_error(caught.exception), code)

    def test_default_no_target_no_io(self):
        capture = io.StringIO()
        with contextlib.redirect_stdout(capture):
            self.assertEqual(p.main([]), 0)
        r = json.loads(capture.getvalue())
        self.assertEqual(r["mode"], "PLAN_ONLY_NO_NETWORK_OR_PROCESS")
        self.assertFalse(r["actual_network_io_run"])
        self.assertFalse(r["target_service_running_or_authorized"])

    def test_good_declared_remote_private_target_not_network_pass(self):
        r = self.evaluate()
        self.assertEqual(r["status"], "H13D_TARGET_CANDIDATE_ELIGIBLE_OFFLINE_NOT_RUNTIME")
        self.assertTrue(r["remote_machine_ownership_operator_declared_only"])
        self.assertFalse(r["remote_endpoint_reachability_verified"])
        self.assertFalse(r["network_policy_effective_verified"])
        self.assertFalse(r["real_network_egress_verified"])
        self.assertFalse(r["host_positive_control_observed"])
        self.assertFalse(r["independent_os_block_observed"])

    def test_private_ipv4_classes_only(self):
        for a in ("10.15.1.3", "172.16.4.13", "172.31.2.3", "192.168.5.9"):
            with self.subTest(a=a):
                self.assertTrue(self.evaluate(address=a)["target_ip_rfc1918"])

    def test_public_or_reserved_or_ipv6_rejected(self):
        cases = (
            "8.8.8.8", "1.1.1.1", "127.0.0.1", "0.0.0.0",
            "169.254.2.2", "224.0.0.1", "255.255.255.255",
            "100.64.0.1", "192.0.2.1",
        )
        for a in cases:
            with self.subTest(a=a):
                self.assert_gate_error("TARGET_NOT_RFC1918_IPV4", address=a)
        for ipv6 in ("2001:db8::1", "::1"):
            with self.subTest(ipv6=ipv6):
                self.assert_gate_error("TARGET_IP_INVALID", address=ipv6)

    def test_invalid_address_rejected_with_fixed_code(self):
        for a in (None, "", "example.com", "192.168.1.101/24",
                  " 192.168.1.101", "192.168.1.101 ",
                  "192.168.1.999", "192.168.1.101\nPRIVATE"):
            with self.subTest(a=a):
                self.assert_gate_error("TARGET_IP_INVALID", address=a)

    def test_port_unprivileged_bound_and_nonboolean(self):
        for port in (-1, 0, 80, 443, 1024, 19999, 61000, 65535, None,
                     "42589", True, 2.0):
            with self.subTest(port=port):
                self.assert_gate_error("TARGET_PORT_NOT_ALLOWED", port=port)
        self.assertTrue(self.evaluate(port=20000)["target_port_unprivileged_lab_range"])
        self.assertTrue(self.evaluate(port=60999)["target_port_unprivileged_lab_range"])

    def test_likely_network_and_broadcast_addresses_rejected(self):
        for a in ("192.168.1.0", "192.168.1.255", "10.2.3.0", "10.2.3.255"):
            with self.subTest(a=a):
                self.assert_gate_error("TARGET_ADDRESS_UNSUITABLE", address=a)

    def test_self_target_always_rejected(self):
        self.assert_gate_error("TARGET_EQUALS_LOCAL_HOST",
                  local_addresses=["10.85.0.1", "192.168.1.101"])

    def test_missing_local_inventory_rejected(self):
        self.assert_gate_error("LOCAL_ADDRESS_INVENTORY_MISSING", local_addresses=[])
        self.assert_gate_error("LOCAL_ADDRESS_INVENTORY_INCOMPLETE",
                  local_inventory_complete=False)

    def test_invalid_local_inventory_rejected(self):
        for addrs in (["notIP"], ["192.168.1.40", "192.168.1.40"],
                      ["192.168.1.40", None], ["192.168.1.40"] * 50):
            with self.subTest(addrs=addrs[:3]):
                self.assert_gate_error("LOCAL_ADDRESS_INVALID", local_addresses=addrs)

    def test_explicit_remote_machine_and_ownership_required(self):
        self.assert_gate_error("TARGET_DIFFERENT_MACHINE_NOT_CONFIRMED",
                  remote_machine_confirmed=False)
        self.assert_gate_error("TARGET_OWNERSHIP_NOT_CONFIRMED",
                  ownership_confirmed=False)

    def test_bool_flags_reject_truthy_nonboolean(self):
        for key in ("remote_machine_confirmed", "ownership_confirmed",
                    "local_inventory_complete"):
            with self.subTest(key=key):
                self.assert_gate_error("TARGET_DETAILS_INCOMPLETE", **{key: 1})

    def test_cli_reports_no_private_addresses(self):
        out, err = io.StringIO(), io.StringIO()
        args = ["--candidate-ip", "192.168.1.101", "--candidate-port", "42589",
                "--local-ip", "192.168.1.40", "--local-ip", "10.85.0.1",
                "--local-inventory-complete", "--controlled-remote-machine",
                "--endpoint-owned"]
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(p.main(args), 0)
        s = out.getvalue() + err.getvalue()
        self.assertNotIn("192.168", s)
        self.assertNotIn("10.85", s)
        self.assertNotIn("42589", s)
        self.assertIn("OFFLINE_NOT_RUNTIME", s)
        self.assertFalse(json.loads(out.getvalue())["real_network_egress_verified"])

    def test_cli_private_invalid_target_no_input_leak(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = p.main(["--candidate-ip", "HOST_PRIVATE_TOKEN", "--candidate-port", "42589"])
        self.assertEqual(rc, 2)
        self.assertNotIn("HOST_PRIVATE_TOKEN", err.getvalue())
        self.assertIn("STOP: H13D_TARGET_GATE:", err.getvalue())
        self.assertEqual(out.getvalue(), "")

    def test_no_io_or_process_imports(self):
        s = SCRIPT.read_text(encoding="utf-8")
        for banned in ("import socket", "import urllib", "import requests",
                       "import subprocess", "subprocess.run(", "socket.socket(",
                       "Get-NetIPAddress", "turn/start"):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, s)


if __name__ == "__main__":
    unittest.main()

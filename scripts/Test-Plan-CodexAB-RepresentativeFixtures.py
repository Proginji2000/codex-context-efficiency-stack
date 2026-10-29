#!/usr/bin/env python3
"""Offline deterministic tests for three disposable representative fixtures."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SRC = Path(__file__).with_name("Plan-CodexAB-RepresentativeFixtures.py")
SPEC = importlib.util.spec_from_file_location("codex_representative_cases", SRC)
app = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(app)


class RepresentativeFixturesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name) / "new-qualification"
        self.roots = [Path(str(self.base) + "-" + case["id"]) for case in app.CASES]

    def materialize(self):
        result = app.materialize(str(self.base))
        self.assertEqual(result["fixture_count"], 3)
        self.assertFalse(result["new_canaries_authorized"])

    def test_plan_default_does_not_create_workspaces(self):
        result = app.summary()
        self.assertEqual(len(result["cases"]), 3)
        self.assertEqual(result["model_calls"], 0)
        self.assertTrue(result["no_live_canaries_authorized"])
        self.assertFalse(any(p.exists() for p in self.roots))

    def test_materialize_three_isolated_git_repos(self):
        self.materialize()
        for root, case in zip(self.roots, app.CASES):
            manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["contract"], app.CONTRACT)
            self.assertEqual(manifest["case_id"], case["id"])
            self.assertFalse(manifest["historical_v2_v3_evidence_reusable"])
            self.assertTrue((root / "workspace" / ".git").is_dir())
            status = subprocess.run(
                ["git", "status", "--porcelain"], cwd=root / "workspace",
                capture_output=True, text=True, check=False)
            self.assertEqual(status.returncode, 0)
            self.assertEqual(status.stdout.strip(), "")

    def test_all_seeded_cases_have_failing_unit_tests(self):
        self.materialize()
        for root in self.roots:
            proc = subprocess.run([
                sys.executable, "-B", "-m", "unittest", "discover",
                "-s", "tests", "-q"
            ], cwd=root / "workspace", capture_output=True, check=False, timeout=10,
               env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
            self.assertNotEqual(proc.returncode, 0)
            self.assertEqual(list((root / "workspace").glob("**/__pycache__")), [])

    def test_preflight_refuses_existing_outputs_and_preserves_them(self):
        self.materialize()
        marker = self.roots[0] / "manifest.json"
        previous = marker.read_bytes()
        with self.assertRaisesRegex(app.PlanError, "OUTPUT_ALREADY_EXISTS"):
            app.materialize(str(self.base))
        self.assertEqual(marker.read_bytes(), previous)

    def test_reject_output_inside_repo(self):
        with self.assertRaisesRegex(app.PlanError, "UNSAFE_OUTPUT"):
            app.destination_paths(str(app.REPO / ".scratch" / "fixture"))
        with self.assertRaisesRegex(app.PlanError, "UNSAFE_OUTPUT"):
            app.destination_paths(str(app.REPO.parent))

    def test_requires_absolute_path_and_nonempty_name(self):
        with self.assertRaisesRegex(app.PlanError, "OUTPUT_MUST_BE_ABSOLUTE"):
            app.destination_paths("relative/prefix")
        with self.assertRaisesRegex(app.PlanError, "OUTPUT_BASE_REQUIRED"):
            app.destination_paths(None)

    def test_case_scopes_and_prompts_are_explicit(self):
        cases = app.CASES
        self.assertEqual({c["id"] for c in cases},
                         {"arith-control", "device-reconcile", "python-fallback-policy"})
        for case in cases:
            self.assertTrue(case["allowed_writes"])
            self.assertIn("git diff --check", case["prompt"])
            self.assertIn("unittest", case["prompt"])
            self.assertTrue(all(path in case["files"] for path in case["allowed_writes"]))
        self.assertTrue(all("auth.json" not in c["files"] for c in cases))

    def test_invalid_existing_case_refuses_partial_start(self):
        self.roots[-1].mkdir()
        with self.assertRaisesRegex(app.PlanError, "OUTPUT_ALREADY_EXISTS"):
            app.materialize(str(self.base))
        self.assertFalse(self.roots[0].exists())

    def test_materialize_only_reports_safe_status(self):
        self.materialize()
        self.assertEqual(app.main(["--output-base", str(self.base), "--materialize"]), 2)
        self.assertFalse(any((r / "workspace" / "auth.json").exists() for r in self.roots))


if __name__ == "__main__":
    unittest.main()

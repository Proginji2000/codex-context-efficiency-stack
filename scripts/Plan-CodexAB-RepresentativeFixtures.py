#!/usr/bin/env python3
"""Plan or explicitly materialize three isolated, deterministic A/B fixtures.

Default is offline JSON plan only: no files, no model, no network. --materialize
writes NEW disposable fixtures only, outside this repository. No Codex launch.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap

REPO = Path(__file__).resolve().parent.parent
CONTRACT = "p1.1-representative-fixtures-design-v1"
CASES = (
    {
        "id": "arith-control",
        "class": "single-file-mechanical",
        "allowed_writes": ["total.py"],
        "prompt": (
            "Delegate to one luna-medium worker. Repair total() to sum prix * "
            "quantite. Only total.py may change. Test with "
            "python -m unittest discover -s tests -q and git diff --check. "
            "Do not install, use network, commit or request privileges."
        ),
        "files": {
            "total.py": """def total(lignes):
    return sum(prix for prix, quantite in lignes)
""",
            "tests/test_total.py": """import unittest
from total import total


class TestTotal(unittest.TestCase):
    def test_nonempty(self):
        self.assertEqual(total([(3, 2), (5, 4)]), 26)

    def test_empty(self):
        self.assertEqual(total([]), 0)
""",
        },
    },
    {
        "id": "device-reconcile",
        "class": "two-module-normalization-and-reconciliation",
        "allowed_writes": ["inventory.py", "labels.py"],
        "prompt": (
            "Delegate the bounded implementation to luna-medium, keeping the parent "
            "orchestrator-only. In labels.py normalize asset IDs by trimming whitespace "
            "and uppercasing; in inventory.py reconcile two fabricated lists of IDs "
            "with sets of normalized IDs, plus sorted duplicates in each source. "
            "Only inventory.py and labels.py may change. Run "
            "python -m unittest discover -s tests -q and git diff --check. "
            "No external systems, files, installs, network, commits, approvals or escalation."
        ),
        "files": {
            "labels.py": """def normalize_asset_id(raw):
    return raw
""",
            "inventory.py": """from labels import normalize_asset_id


def reconcile(gestion, soti):
    g = set(gestion)
    s = set(soti)
    return {
        "gestion_only": sorted(g - s),
        "soti_only": sorted(s - g),
    }
""",
            "tests/test_inventory.py": """import unittest
from inventory import reconcile
from labels import normalize_asset_id


class TestReconcile(unittest.TestCase):
    def test_canonical_id(self):
        self.assertEqual(normalize_asset_id("  mc93-4  "), "MC93-4")

    def test_bidirectional(self):
        actual = reconcile([" mc93-1 ", "MC93-2"], ["mc93-1", " mc93-3 "])
        self.assertEqual(actual["gestion_only"], ["MC93-2"])
        self.assertEqual(actual["soti_only"], ["MC93-3"])

    def test_duplicates_by_normalized_key(self):
        actual = reconcile(["mc93-1", " MC93-1 "], ["MC93-2", " mc93-2 "])
        self.assertEqual(actual["duplicates_gestion"], ["MC93-1"])
        self.assertEqual(actual["duplicates_soti"], ["MC93-2"])

    def test_empty(self):
        actual = reconcile([], [])
        self.assertEqual(actual, {
            "gestion_only": [], "soti_only": [],
            "duplicates_gestion": [], "duplicates_soti": []
        })
""",
        },
    },
    {
        "id": "python-fallback-policy",
        "class": "incident-diagnosis-and-safe-self-correction",
        "allowed_writes": ["fallback.py"],
        "prompt": (
            "Parent orchestrator-only; delegate to luna-medium worker. Repair the "
            "simulated Python fallback policy in fallback.py: execute the requested "
            "Python once and retry exactly once with the trusted interpreter only "
            "when startup fails with FileNotFoundError. Never retry for PermissionError, "
            "test exceptions or failed fallback. Only fallback.py may change. "
            "No real commands, installations, network or privileges. Run "
            "python -m unittest discover -s tests -q and git diff --check."
        ),
        "files": {
            "fallback.py": """def run_python(invoke):
    try:
        return invoke("python")
    except Exception:
        return invoke("absolute-python")
""",
            "tests/test_fallback.py": """import unittest
from fallback import run_python


class TestFallback(unittest.TestCase):
    def test_normal_success(self):
        calls = []
        def run(which):
            calls.append(which)
            return 0
        self.assertEqual(run_python(run), 0)
        self.assertEqual(calls, ["python"])

    def test_only_start_failure_triggers_one_fallback(self):
        calls = []
        def run(which):
            calls.append(which)
            if which == "python":
                raise FileNotFoundError("WindowsApps alias unavailable")
            return 0
        self.assertEqual(run_python(run), 0)
        self.assertEqual(calls, ["python", "absolute-python"])

    def test_policy_denial_never_retries(self):
        calls = []
        def run(which):
            calls.append(which)
            raise PermissionError("sandbox policy denial")
        with self.assertRaises(PermissionError):
            run_python(run)
        self.assertEqual(calls, ["python"])

    def test_test_failure_never_retries(self):
        calls = []
        def run(which):
            calls.append(which)
            raise RuntimeError("assertion failed")
        with self.assertRaises(RuntimeError):
            run_python(run)
        self.assertEqual(calls, ["python"])

    def test_fallback_failure_is_terminal(self):
        calls = []
        def run(which):
            calls.append(which)
            if which == "python":
                raise FileNotFoundError("python absent")
            raise PermissionError("fallback denied")
        with self.assertRaises(PermissionError):
            run_python(run)
        self.assertEqual(calls, ["python", "absolute-python"])
""",
        },
    },
)


class PlanError(ValueError):
    """Safe public error strings."""


def summary():
    return {
        "contract": CONTRACT,
        "mode": "offline_plan",
        "model_calls": 0,
        "cases": [
            {"id": c["id"], "class": c["class"], "allowed_writes": c["allowed_writes"],
             "unit_test_command": "python -B -m unittest discover -s tests -q",
             "git_gate": "git diff --check",
             "prompt": c["prompt"],
             "baseline_candidate_prompt_must_match": True}
            for c in CASES
        ],
        "no_live_canaries_authorized": True,
        "not_comparable_to_v2_or_v3": True,
    }


def destination_paths(output_base):
    if not output_base:
        raise PlanError("OUTPUT_BASE_REQUIRED")
    raw = Path(output_base).expanduser()
    if not raw.is_absolute():
        raise PlanError("OUTPUT_MUST_BE_ABSOLUTE")
    root = raw.resolve(strict=False)
    repo = REPO.resolve(strict=True)
    if root == repo or repo in root.parents or root in repo.parents or root == Path.home().resolve():
        raise PlanError("UNSAFE_OUTPUT")
    if not root.parent.is_dir() or root.parent.is_symlink():
        raise PlanError("OUTPUT_PARENT_INVALID")
    outputs = [Path(str(root) + "-" + case["id"]) for case in CASES]
    if any(p.exists() or p.is_symlink() for p in outputs):
        raise PlanError("OUTPUT_ALREADY_EXISTS")
    return outputs


def _run(args, cwd, env=None):
    return subprocess.run(args, cwd=cwd, env=env, stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL, check=False, timeout=20).returncode


def materialize(output_base):
    outputs = destination_paths(output_base)
    if _run(["git", "--version"], REPO) != 0:
        raise PlanError("GIT_UNAVAILABLE")
    for case, root in zip(CASES, outputs):
        root.mkdir(parents=False, exist_ok=False)
        work = root / "workspace"
        work.mkdir()
        for name, raw in case["files"].items():
            rel = Path(name)
            if rel.is_absolute() or ".." in rel.parts or rel.parts[0] == ".":
                raise PlanError("INVALID_FIXTURE_PATH")
            path = work / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(textwrap.dedent(raw), encoding="utf-8")
        (work / ".gitignore").write_text("__pycache__/\n*.pyc\n", encoding="utf-8")
        (root / "manifest.json").write_text(json.dumps({
            "schema": 1,
            "contract": CONTRACT,
            "case_id": case["id"],
            "case_class": case["class"],
            "allowed_writes": case["allowed_writes"],
            "prompt": case["prompt"],
            "historical_v2_v3_evidence_reusable": False,
            "model_calls": 0,
        }, indent=2) + "\n", encoding="utf-8")
        if _run(["git", "init", "-q", "-b", "main"], work):
            raise PlanError("GIT_FIXTURE_INIT_FAILED")
        if _run(["git", "add", "--", "."], work):
            raise PlanError("GIT_FIXTURE_ADD_FAILED")
        env = os.environ.copy()
        env.update({
            "GIT_AUTHOR_DATE": "2020-01-01T00:00:00+00:00",
            "GIT_COMMITTER_DATE": "2020-01-01T00:00:00+00:00",
        })
        if _run(["git", "-c", "user.name=Codex AB Fixture",
                  "-c", "user.email=fixture@example.invalid",
                  "commit", "-qm", "base", "--no-verify"], work, env=env):
            raise PlanError("GIT_FIXTURE_COMMIT_FAILED")
    return {
        "status": "DISPOSABLE_FIXTURES_MATERIALIZED",
        "fixture_count": len(CASES),
        "model_calls": 0,
        "existing_outputs_overwritten": False,
        "new_canaries_authorized": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-base", help="New absolute path prefix, outside repository")
    parser.add_argument("--materialize", action="store_true",
                        help="Explicitly create three disposable fixture repositories; no model")
    args = parser.parse_args(argv)
    try:
        result = materialize(args.output_base) if args.materialize else summary()
    except (OSError, subprocess.TimeoutExpired, PlanError) as exc:
        code = str(exc) if isinstance(exc, PlanError) else "FIXTURE_PRECONDITION_FAILED"
        print("STOP: " + code, file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

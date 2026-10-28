#!/usr/bin/env python3
"""Isolated Codex AGENTS A/B runner. No mutation of existing Codex homes."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

COMMIT = "80bb5d9eaa09d141075176ea363e93765e9f41cc"
URL = ("https://raw.githubusercontent.com/Proginji2000/"
       "codex-context-efficiency-stack/" + COMMIT + "/templates/AGENTS.md")
ROLES = ("luna-low", "luna-medium", "luna-high", "terra-medium",
         "terra-high", "ui-implementer", "sol-high", "sol-xhigh",
         "astra-high", "sol6-legacy-high")
ARMS = ("baseline", "candidate")
PROMPT = (
    "Luna Medium is orchestrator-only. Delegate this exact task to the configured "
    "luna-medium worker: inspect total.py and tests/test_total.py, repair the "
    "broken total() calculation and run python -m unittest discover -s tests -q. "
    "The parent must supervise and report evidence, not change files itself. "
    "Do not install anything, access other projects, use network or commit. "
    "Only total.py may be changed."
)
FIXTURE = {
    "total.py": "def total(lignes):\n    return sum(prix for prix, quantite in lignes)\n",
    "tests/test_total.py": (
        "import unittest\nfrom total import total\n\n"
        "class TestTotal(unittest.TestCase):\n"
        "    def test_multiple(self):\n"
        "        self.assertEqual(total([(3, 2), (5, 4)]), 26)\n"
        "    def test_empty(self):\n"
        "        self.assertEqual(total([]), 0)\n"
    ),
    ".gitignore": "__pycache__/\n*.pyc\n",
}


def digest(value):
    return hashlib.sha256(value).hexdigest()


def read_file(path):
    value = path.read_bytes()
    if not value or len(value) > 100000:
        raise ValueError("missing or oversized input")
    return value


def call(args, *, cwd=None, env=None, timeout=40):
    return subprocess.run(args, cwd=cwd, env=env, timeout=timeout,
                          text=True, encoding="utf-8", errors="replace",
                          capture_output=True, check=False)


def resolve_codex_executable():
    """Return an explicit executable path: Windows CreateProcess ignores PATHEXT."""
    candidate = shutil.which("codex")
    if os.name != "nt":
        return candidate

    if candidate:
        path = Path(candidate)
        suffix = path.suffix.lower()
        if suffix in (".exe", ".com", ".cmd", ".bat"):
            return str(path)
        # npm/pnpm can put a POSIX shim or a PowerShell .ps1 beside a
        # Windows .cmd shim. Do not pass the POSIX shim to CreateProcess.
        stem = path.with_suffix("") if suffix == ".ps1" else path
        for ext in (".cmd", ".exe", ".bat"):
            sibling = Path(str(stem) + ext)
            if sibling.is_file():
                return str(sibling)

    # e.g. an npm .cmd visible through PATH but not found as bare 'codex'.
    for extension in (".exe", ".cmd", ".bat", ".com"):
        found = shutil.which("codex" + extension)
        if found:
            return found
    return None


def call_codex(args, *, cwd=None, env=None, timeout=40):
    executable = resolve_codex_executable()
    if not executable:
        raise FileNotFoundError("Codex executable missing")
    return call([executable, *args], cwd=cwd, env=env, timeout=timeout)


def home_env(root, arm):
    env = os.environ.copy()
    # Avoid inheriting auth-provider overrides or redirecting SQLite/session state.
    # Each run must use its own CODEX_HOME credentials and state stores.
    for key in ("CODEX_SQLITE_HOME", "CODEX_API_KEY", "CODEX_ACCESS_TOKEN",
                "OPENAI_API_KEY", "OPENAI_BASE_URL"):
        env.pop(key, None)
    env["CODEX_HOME"] = str(root / (arm + "-home"))
    return env


def save_json(path, value):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def state(root):
    config = json.loads((root / "benchmark-state.json").read_text(encoding="utf-8"))
    if config.get("schema_version") != 1 or config.get("candidate_commit") != COMMIT:
        raise ValueError("invalid experiment state")
    for arm in ARMS:
        if digest(read_file(root / (arm + "-home") / "AGENTS.md")) != config[arm + "_sha256"]:
            raise ValueError("AGENTS fingerprint mismatch: experiment must stop")
    if call_codex(["--version"]).stdout.strip() != config["cli_version"]:
        raise ValueError("Codex CLI version changed since preparation")
    return config


class PrepareError(ValueError):
    """Fixed public-safe error code; do not expose paths, config or credentials."""


def prepare(args):
    repo = Path(args.repo).resolve(strict=True)
    root = Path(args.output).expanduser().resolve()
    if root.exists():
        raise PrepareError("OUTPUT_ALREADY_EXISTS: choose a new empty experiment path; never erase previous files")
    if root == repo or repo in root.parents or root == Path.home().resolve():
        raise PrepareError("OUTPUT_UNSAFE_LOCATION: choose a fresh folder outside the stack checkout and user home")

    # Respect an explicitly configured Codex home. Do not inspect session history.
    baseline_path = (Path(args.baseline).expanduser() if args.baseline else
                     Path(os.environ.get("CODEX_HOME") or
                          Path.home() / ".codex") / "AGENTS.md")
    try:
        baseline = read_file(baseline_path.resolve(strict=True))
    except (OSError, ValueError):
        raise PrepareError(
            "BASELINE_UNAVAILABLE: current AGENTS.md absent/unreadable; pass --baseline with its exact path"
        ) from None

    try:
        snippet = read_file(repo / "templates" / "config.routing.snippet.toml")
    except (OSError, ValueError):
        raise PrepareError("ROUTING_TEMPLATE_MISSING: update the stack checkout") from None
    role_dir = repo / "templates" / "agents"
    for role in ROLES:
        if not (role_dir / (role + ".toml")).is_file():
            raise PrepareError("ROLE_TEMPLATE_MISSING: update the stack checkout")

    if args.candidate_file:
        try:
            candidate = read_file(Path(args.candidate_file).resolve(strict=True))
        except (OSError, ValueError):
            raise PrepareError("CANDIDATE_FILE_UNAVAILABLE: check the local candidate path") from None
        candidate_source = "explicit-local-file"
    else:
        # The pinned PR commit is normally present after the user's git pull.
        # This avoids relying on raw.githubusercontent.com or TLS proxy settings.
        try:
            local = subprocess.run(
                ["git", "show", COMMIT + ":templates/AGENTS.md"],
                cwd=repo, capture_output=True, timeout=20, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            local = None
        if local is not None and local.returncode == 0 and local.stdout:
            candidate = local.stdout
            candidate_source = "pinned-local-git-object"
        else:
            try:
                with urllib.request.urlopen(URL, timeout=20) as response:
                    candidate = response.read(100001)
            except (OSError, ValueError):
                raise PrepareError(
                    "CANDIDATE_FETCH_FAILED: pinned Git commit unavailable locally and HTTPS fetch failed; "
                    "retrieve the pinned file separately and use --candidate-file"
                ) from None
            candidate_source = "pinned-github-download"
    if not candidate or len(candidate) > 100000:
        raise PrepareError("CANDIDATE_INVALID_SIZE: verify the pinned file")
    if digest(candidate) == digest(baseline):
        raise PrepareError("VARIANTS_IDENTICAL: baseline already equals the experimental candidate")

    if not shutil.which("git"):
        raise PrepareError("GIT_UNAVAILABLE: git must be callable from Python's PATH")
    if not resolve_codex_executable():
        raise PrepareError(
            "CODEX_UNAVAILABLE: codex is accessible in PowerShell but not on Python's executable PATH"
        )
    try:
        version = call_codex(["--version"])
    except (OSError, subprocess.TimeoutExpired):
        raise PrepareError("CODEX_START_FAILED: Python cannot launch the Codex CLI") from None
    if version.returncode or not version.stdout.strip():
        raise PrepareError("CODEX_VERSION_FAILED: codex --version did not complete")

    # No new directory is written before all checkable prerequisites pass.
    try:
        root.mkdir(parents=True)
        for arm, value in (("baseline", baseline), ("candidate", candidate)):
            home = root / (arm + "-home")
            (home / "agents").mkdir(parents=True)
            (home / "AGENTS.md").write_bytes(value)
            (home / "config.toml").write_bytes(
                b"tool_output_token_limit = 4000\n\n" + snippet)
            for role in ROLES:
                shutil.copyfile(role_dir / (role + ".toml"),
                                home / "agents" / (role + ".toml"))
        record = {
            "schema_version": 1, "candidate_commit": COMMIT,
            "baseline_sha256": digest(baseline), "candidate_sha256": digest(candidate),
            "config_sha256": digest(b"tool_output_token_limit = 4000\n\n" + snippet),
            "cli_version": version.stdout.strip(), "model": "gpt-6-luna",
            "reasoning_effort": "medium", "sandbox": "workspace-write",
            "mcp_profile": "routing-only-no-MCP", "case_id": "smoke-total-01",
            "prompt_sha256": digest(PROMPT.encode("utf-8")),
        }
        save_json(root / "benchmark-state.json", record)
    except OSError:
        raise PrepareError(
            "PREPARE_WRITE_FAILED: inspect the newly created experiment folder; "
            "retry using a NEW path without deleting any evidence"
        ) from None

    print("PREPARED: two separate Codex homes; existing user config untouched.")
    print("Candidate source:", candidate_source)
    print("Baseline SHA256:", record["baseline_sha256"])
    print("Candidate SHA256:", record["candidate_sha256"])
    print("Log in separately in each *-home; never upload these home directories.")
    print("No model calls have been made.")

def status(args):
    root = Path(args.output).expanduser().resolve(strict=True)
    state(root)
    for arm in ARMS:
        check = call_codex(["login", "status"], env=home_env(root, arm))
        if check.returncode:
            raise ValueError("one or both isolated homes require their own 'codex login'")
    print("READY: both isolated profiles have a Codex login; CLI and hashes match.")


def make_fixture(path):
    path.mkdir(parents=True)  # Refuse to overwrite existing trial directories.
    for name, content in FIXTURE.items():
        file = path / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content, encoding="utf-8")
    if call(["git", "init", "-q", "-b", "main"], cwd=path).returncode:
        raise ValueError("cannot initialize disposable test repository")
    if call(["git", "add", "total.py", "tests/test_total.py", ".gitignore"], cwd=path).returncode:
        raise ValueError("cannot stage disposable fixture")
    env = os.environ.copy()
    env.update({"GIT_AUTHOR_DATE": "2020-01-01T00:00:00+00:00",
                "GIT_COMMITTER_DATE": "2020-01-01T00:00:00+00:00"})
    commit = call(["git", "-c", "user.name=Codex AB Fixture",
                   "-c", "user.email=fixture@example.invalid",
                   "commit", "-qm", "base"], cwd=path, env=env)
    if commit.returncode:
        raise ValueError("cannot commit disposable fixture")
    return call(["git", "rev-parse", "HEAD"], cwd=path).stdout.strip()


def parse_events(text):
    usage = {"complete_turns": 0, "turns_with_usage": 0, "failed_turns": 0,
             "input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0}
    delegated, valid, started = False, True, 0
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except (ValueError, TypeError):
            valid = False
            continue
        kind = event.get("type")
        if kind == "turn.started":
            started += 1
        elif kind == "turn.failed":
            usage["failed_turns"] += 1
        elif kind == "turn.completed":
            usage["complete_turns"] += 1
            counters = event.get("usage")
            if not isinstance(counters, dict):
                continue
            values = [counters.get(k) for k in
                      ("input_tokens", "cached_input_tokens", "output_tokens")]
            if not all(type(n) is int and n >= 0 for n in values) or values[1] > values[0]:
                valid = False
                continue
            usage["turns_with_usage"] += 1
            for key, n in zip(("input_tokens", "cached_input_tokens", "output_tokens"), values):
                usage[key] += n
        elif kind == "item.completed":
            item = event.get("item")
            if (isinstance(item, dict) and item.get("type") == "collab_tool_call"
                    and item.get("tool") == "spawn_agent" and item.get("status") == "completed"
                    and isinstance(item.get("receiver_thread_ids"), list)
                    and len(item["receiver_thread_ids"]) > 0):
                delegated = True
    return usage, delegated, valid, max(0, started - 1)


def verify(path):
    tests = call([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
                 cwd=path)
    check = call(["git", "diff", "--check"], cwd=path)
    tracked = call(["git", "diff", "--name-only"], cwd=path)
    untracked = call(["git", "ls-files", "--others", "--exclude-standard"], cwd=path)
    actual = (path / "total.py").read_text(encoding="utf-8")
    return (tests.returncode == 0 and check.returncode == 0
            and tracked.stdout.splitlines() == ["total.py"]
            and not untracked.stdout.strip()
            and "prix * quantite" in actual)


def run(args):
    if not args.execute:
        raise ValueError("live model use requires the explicit --execute flag")
    root = Path(args.output).expanduser().resolve(strict=True)
    cfg = state(root)
    status(args)
    result_path = root / "anonymized-results.json"
    if result_path.exists():
        raise ValueError("existing results: will not append, resume or overwrite trials")
    records, fixture_head = [], None
    print("Starting", args.pairs * 2, "new Codex invocations, with no raw event persistence.", flush=True)
    for pair in range(1, args.pairs + 1):
        arms = ARMS if pair % 2 else tuple(reversed(ARMS))
        for arm in arms:
            work = root / "workspaces" / ("pair-" + str(pair) + "-" + arm)
            head = make_fixture(work)
            if fixture_head is None:
                fixture_head = head
            elif head != fixture_head:
                raise ValueError("disposable fixture HEAD differs across runs")
            cmd = ["exec", "--json", "--ephemeral",
                   "--sandbox", "workspace-write", "-C", str(work),
                   "--model", "gpt-6-luna", "-c", "model_reasoning_effort=medium",
                   PROMPT]
            start = time.monotonic()
            try:
                proc = call_codex(cmd, env=home_env(root, arm), timeout=args.timeout)
            except subprocess.TimeoutExpired:
                proc = None
            elapsed = round(time.monotonic() - start, 3)
            usage, delegated, valid, retries = parse_events(proc.stdout if proc else "")
            safe = verify(work) if proc else False
            record = {
                "pair": pair, "arm": arm, "case_id": cfg["case_id"],
                "controls": {
                    "cli_version": cfg["cli_version"], "model": cfg["model"],
                    "reasoning_effort": cfg["reasoning_effort"], "sandbox": cfg["sandbox"],
                    "repo_head": fixture_head, "mcp_profile": cfg["mcp_profile"],
                    "prompt_sha256": cfg["prompt_sha256"],
                },
                "agents_sha": cfg[arm + "_sha256"],
                "success": bool(proc and proc.returncode == 0 and valid and safe),
                "delegated": delegated,
                # Public Codex JSONL has had gaps in subagent events. Neither
                # non-delegation nor parent-only orchestration can be proved
                # simply by parsing a missing/partial spawn event.
                "parent_orchestrated": False,
                "safety_pass": safe,
                "retries": retries,  # CLI-visible extra turns only (lower bound).
                "elapsed_s": elapsed, "usage": usage,
            }
            records.append(record)
            save_json(result_path, {"schema_version": 1, "runs": records})
            print("pair %d/%d %s: tests=%s, spawn_event=%s, input=%d" %
                  (pair, args.pairs, arm, "PASS" if safe else "FAIL",
                   "observed" if delegated else "unverified", usage["input_tokens"]),
                  flush=True)
            if not record["success"]:
                print("STOP: runtime or deterministic verification failed, no retry/escalation.")
                return 1
    print("Completed. Behavioral parent role remains unverified; do not merge PR #14.")
    print("Only anonymized-results.json may be shared, never the *-home directories.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--repo", default=str(Path(__file__).resolve().parent.parent))
    p.add_argument("--output", required=True)
    p.add_argument("--baseline", default=None)
    p.add_argument("--candidate-file", default=None)
    for verb in ("status", "run"):
        s = sub.add_parser(verb)
        s.add_argument("--output", required=True)
        if verb == "run":
            s.add_argument("--execute", action="store_true")
            s.add_argument("--pairs", type=int, default=3, choices=(1, 2, 3))
            s.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args(argv)
    try:
        return {"prepare": prepare, "status": status, "run": run}[args.command](args) or 0
    except PrepareError as error:
        print("STOP [PREPARE]: " + str(error), file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.TimeoutExpired):
        print("STOP: benchmark precondition or verification failed; no private input printed.",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Synthetic local-Git tests for the opt-in Luna worktree planner."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

PLANNER = Path(__file__).with_name("Plan-CodexWorktreeWave.py")


def run(*cmd, succeed=True):
    result = subprocess.run(cmd, text=True, capture_output=True,
                            encoding="utf-8", errors="replace", timeout=50)
    if succeed and result.returncode:
        raise AssertionError("A required synthetic test command failed.")
    if not succeed and result.returncode == 0:
        raise AssertionError("A prohibited synthetic action unexpectedly succeeded.")
    return result


def manifest(path, a="src/api", b="web/ui"):
    data = {"version": 1, "workers": [
        {"name": "wave-api", "lane": "luna-medium",
         "goal": "Implement an isolated API task", "write_scopes": [a]},
        {"name": "wave-ui", "lane": "ui-implementer",
         "goal": "Implement independent UI task", "write_scopes": [b]},
    ]}
    path.write_text(json.dumps(data), encoding="utf-8")


def invoke(repo, plan, apply=False, succeed=True):
    args = [sys.executable, str(PLANNER),
            "--repo", str(repo), "--manifest", str(plan)]
    if apply:
        args.append("--apply")
    result = run(*args, succeed=succeed)
    assert str(repo) not in result.stdout + result.stderr
    return json.loads(result.stdout) if succeed else None


def main():
    with tempfile.TemporaryDirectory(prefix="codex_wave_fixture_") as temp:
        root = Path(temp)
        repo = root / "test-repo"
        repo.mkdir()
        run("git", "-C", str(repo), "init", "-b", "main")
        run("git", "-C", str(repo), "-c", "user.name=Fixture",
            "-c", "user.email=fixture@example.invalid",
            "commit", "--allow-empty", "-m", "base")
        plan = root / "wave.json"
        manifest(plan)

        preview = invoke(repo, plan)
        assert preview["mode"] == "preview_only"
        assert preview["agents_started"] == 0
        assert len(preview["workers"]) == 2
        assert not (root / "test-repo-codex-worktrees").exists()

        # File/directory nesting, Windows case collisions and traversal rejected.
        for a, b in (("src", "src/module"), ("Src/API", "src/api"),
                     ("../external", "web"), (".git/config", "web"),
                     ("web\\ui", "src"), ("C:/Windows", "src")):
            manifest(plan, a, b)
            invoke(repo, plan, apply=True, succeed=False)
            assert not (root / "test-repo-codex-worktrees").exists()

        manifest(plan)
        applied = invoke(repo, plan, apply=True)
        assert applied["mode"] == "applied"
        assert applied["created_names"] == ["wave-api", "wave-ui"]
        area = root / "test-repo-codex-worktrees"
        assert (area / "wave-api").is_dir() and (area / "wave-ui").is_dir()
        assert applied["agents_started"] == 0
        assert applied["automatic_cleanup"] is False

        # Never overwrite or silently reuse existing worktrees/branches.
        invoke(repo, plan, apply=True, succeed=False)
        assert (area / "wave-api").exists() and (area / "wave-ui").exists()
        branches = run("git", "-C", str(repo), "branch", "--list", "codex/*").stdout
        assert "codex/wave-api" in branches and "codex/wave-ui" in branches

    print("[OK] Two disjoint workers previewed and provisioned in isolated Git worktrees.")
    print("[OK] Nested/case-insensitive/path-traversal ownership rejected.")
    print("[OK] Reused branch/worktree refused; no model calls, merges, or cleanup.")
    print("PASS: Opt-in worktree wave planner synthetic Git lifecycle.")


if __name__ == "__main__":
    main()

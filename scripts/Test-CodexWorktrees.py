#!/usr/bin/env python3
"""Synthetic end-to-end Git worktree safety tests; no Codex model calls."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

MANAGER = Path(__file__).with_name("Manage-CodexWorktrees.py")


def call(*argv: str, ok: bool = True) -> subprocess.CompletedProcess[str]:
    p = subprocess.run(list(argv), capture_output=True, text=True,
                       check=False, timeout=30, encoding="utf-8", errors="replace")
    if ok and p.returncode:
        raise AssertionError("Unexpected command failure (return %d): %s" %
                             (p.returncode, " ".join(argv[:3])))
    return p


def git(repo: Path, *args: str, ok: bool = True) -> subprocess.CompletedProcess[str]:
    return call("git", "-C", str(repo), *args, ok=ok)


def manage(repo: Path, *args: str, ok: bool = True) -> dict[str, object] | None:
    p = call(sys.executable, str(MANAGER), *args, "--repo", str(repo), ok=ok)
    if ok:
        return json.loads(p.stdout)
    if p.returncode == 0:
        raise AssertionError("Expected unsafe command to be rejected.")
    # Check that explicit local paths and private sentinel strings are never
    # shown by the manager's conservative failure messages.
    assert str(repo) not in p.stderr
    assert "PRIVATE_SENTINEL" not in p.stderr
    return None


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="codex_worktree_safety_test_") as temp:
        repo = Path(temp) / "source-repo"
        repo.mkdir()
        git(repo, "init", "-b", "main")
        git(repo, "-c", "user.name=Test",
            "-c", "user.email=test@example.invalid",
            "commit", "--allow-empty", "-m", "initial")
        base_sha = git(repo, "rev-parse", "HEAD").stdout.strip()

        initial = manage(repo, "inventory")
        assert initial is not None
        assert initial["mode"] == "read_only" and initial["count"] == 1
        assert initial["worktrees"][0]["primary"] is True

        preview = manage(repo, "create", "--name", "alpha")
        assert preview is not None and preview["created"] is False
        assert manage(repo, "inventory")["count"] == 1
        assert git(repo, "show-ref", "--verify", "--quiet",
                   "refs/heads/codex/alpha", ok=False).returncode != 0

        created = manage(repo, "create", "--name", "alpha", "--apply")
        assert created is not None and created["created"] is True
        alpha = repo.parent / "source-repo-codex-worktrees" / "alpha"
        assert alpha.is_dir()
        assert git(alpha, "rev-parse", "HEAD").stdout.strip() == base_sha
        assert manage(repo, "inventory")["count"] == 2
        assert manage(repo, "inventory")["worktrees"][1]["managed"] is True

        # No manual or automated deletion of a worktree with untracked files.
        dirty = alpha / "PRIVATE_SENTINEL.txt"
        dirty.write_text("Untracked work must not be removed.", encoding="utf-8")
        manage(repo, "remove", "--name", "alpha", "--apply",
               "--confirm-name", "alpha", ok=False)
        assert dirty.read_text(encoding="utf-8").startswith("Untracked")
        dirty.unlink()

        # Even ignored scratch/build data is protected.
        git(alpha, "config", "core.excludesfile", str(repo / "ignore-patterns.txt"))
        (repo / "ignore-patterns.txt").write_text("*.cache\n", encoding="ascii")
        ignored = alpha / "PRIVATE_SENTINEL.cache"
        ignored.write_text("Preserve ignored evidence.", encoding="utf-8")
        manage(repo, "remove", "--name", "alpha", "--apply",
               "--confirm-name", "alpha", ok=False)
        assert ignored.exists()
        ignored.unlink()

        # Git lock prevents deletion, even if the branch is merged.
        git(repo, "worktree", "lock", "--reason", "test lock", str(alpha))
        manage(repo, "remove", "--name", "alpha", "--apply",
               "--confirm-name", "alpha", ok=False)
        assert alpha.exists()
        git(repo, "worktree", "unlock", str(alpha))

        # A clean worktree with an unmerged commit still cannot be removed.
        git(alpha, "-c", "user.name=Test",
            "-c", "user.email=test@example.invalid",
            "commit", "--allow-empty", "-m", "unmerged change")
        manage(repo, "remove", "--name", "alpha", "--apply",
               "--confirm-name", "alpha", ok=False)
        assert alpha.exists()

        # After an explicit merge, a preview still cannot delete anything.
        git(repo, "merge", "--ff-only", "codex/alpha")
        planned = manage(repo, "remove", "--name", "alpha")
        assert planned is not None and planned["removed"] is False
        assert alpha.is_dir()
        manage(repo, "remove", "--name", "alpha", "--apply", ok=False)
        assert alpha.is_dir()
        manage(repo, "remove", "--name", "alpha", "--apply",
               "--confirm-name", "wrong", ok=False)
        assert alpha.is_dir()

        removed = manage(repo, "remove", "--name", "alpha", "--apply",
                         "--confirm-name", "alpha")
        assert removed is not None and removed["removed"] is True
        assert not alpha.exists()
        assert manage(repo, "inventory")["count"] == 1
        # Crucial: the original branch remains for traceability and recovery.
        assert git(repo, "show-ref", "--verify", "--quiet",
                   "refs/heads/codex/alpha").returncode == 0

        # Don't create a fresh branch by overwriting a retained one.
        manage(repo, "create", "--name", "alpha", "--apply", ok=False)
        manage(repo, "remove", "--name", "missing", "--apply",
               "--confirm-name", "missing", ok=False)
        manage(repo, "create", "--name", "bad/branch", "--apply", ok=False)

        # Unmanaged / detached worktrees are never removal candidates.
        extra = Path(temp) / "unmanaged-worktree"
        git(repo, "worktree", "add", "--detach", str(extra), "HEAD")
        snapshot = manage(repo, "inventory")
        assert snapshot is not None and snapshot["count"] == 2
        assert all(not item["managed"] for item in snapshot["worktrees"])
        manage(repo, "remove", "--name", "unmanaged-worktree", "--apply",
               "--confirm-name", "unmanaged-worktree", ok=False)
        assert extra.exists()

    print("[OK] Preview-only inventory/create/remove; clean isolated branch creation.")
    print("[OK] Untracked and ignored data, Git locks and unmerged commits protected.")
    print("[OK] Explicit confirmation required; no --force; original branch retained.")
    print("[OK] Main, unmanaged and detached worktrees cannot be removed.")
    print("PASS: Synthetic Git worktree lifecycle; zero Codex calls and no network.")


if __name__ == "__main__":
    main()

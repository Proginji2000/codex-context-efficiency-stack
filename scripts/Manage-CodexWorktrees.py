#!/usr/bin/env python3
"""Conservative Git worktree inventory, creation and explicit guarded removal.

Python 3.11+, Git. No Codex calls, no external dependencies, no git fetch/reset,
no force/remove-recursive, no branch deletion and no background operations.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

NAME = re.compile(r"[a-z][a-z0-9-]{0,35}\Z")
BRANCH_PREFIX = "refs/heads/codex/"


class UnsafeWorktree(RuntimeError):
    pass


def git(repo: Path, *args: str, allowed: tuple[int, ...] = (0,)) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        timeout=30,
    )
    if result.returncode not in allowed:
        # stderr can contain local paths, usernames and remote URLs: never echo it.
        raise UnsafeWorktree("Git check or action failed; details withheld (exit %d)." % result.returncode)
    return result


def repo_root(start: Path) -> Path:
    out = git(start, "rev-parse", "--show-toplevel").stdout.decode("utf-8", errors="replace").strip()
    if not out:
        raise UnsafeWorktree("No Git working tree found.")
    return Path(out).resolve(strict=True)


def worktrees(root: Path) -> list[dict[str, object]]:
    raw = git(root, "worktree", "list", "--porcelain", "-z").stdout
    items: list[dict[str, object]] = []
    item: dict[str, object] = {}
    for field in raw.split(b"\0"):
        if not field:
            if item:
                items.append(item)
                item = {}
            continue
        key, _, value = field.partition(b" ")
        text = os.fsdecode(value)
        if key == b"worktree":
            if item:
                raise UnsafeWorktree("Unexpected worktree record format.")
            item["path"] = str(Path(text).resolve(strict=False))
        elif key == b"HEAD":
            item["head"] = text
        elif key == b"branch":
            item["branch"] = text
        elif key == b"detached":
            item["detached"] = True
        elif key == b"locked":
            item["locked"] = True
        elif key == b"prunable":
            item["prunable"] = True
    if item:
        items.append(item)
    if not items or not items[0].get("path"):
        raise UnsafeWorktree("Cannot identify primary worktree.")
    return items


def managed_directory(primary: Path) -> Path:
    parent = primary.parent
    directory = parent / (primary.name + "-codex-worktrees")
    if directory.is_symlink():
        raise UnsafeWorktree("Managed worktree directory is a symlink.")
    if directory.exists() and not directory.is_dir():
        raise UnsafeWorktree("Managed worktree directory is not a directory.")
    return directory.resolve(strict=False)


def managed_target(directory: Path, name: str) -> Path:
    if not NAME.fullmatch(name):
        raise UnsafeWorktree("Worktree name must match [a-z][a-z0-9-]{0,35}.")
    target = directory / name
    if target.is_symlink():
        raise UnsafeWorktree("Target is a symlink.")
    if target.resolve(strict=False).parent != directory:
        raise UnsafeWorktree("Target escapes the managed worktree directory.")
    return target


def clean_status(target: Path) -> bool:
    # Includes ignored files to avoid silently losing build outputs, scratch
    # data, evidence, .env files or other data ignored by .gitignore.
    result = git(target, "status", "--porcelain=v1", "--ignored=matching",
                 "--untracked-files=all", "-z")
    return result.stdout == b""


def merged_into(primary: Path, branch_ref: str, base_ref: str) -> bool:
    if not base_ref.startswith("refs/heads/") or any(
        part in base_ref for part in ("..", "@{", "\\", "\0", " ")
    ):
        raise UnsafeWorktree("Merge target must be a simple local refs/heads/ reference.")
    if not re.fullmatch(r"refs/heads/[a-zA-Z0-9_./-]+", base_ref):
        raise UnsafeWorktree("Merge target is not a valid local branch reference.")
    if git(primary, "show-ref", "--verify", "--quiet", base_ref, allowed=(0, 1)).returncode != 0:
        return False
    check = git(primary, "merge-base", "--is-ancestor", branch_ref, base_ref, allowed=(0, 1))
    return check.returncode == 0


def inventory(root: Path, records: list[dict[str, object]], directory: Path,
              include_paths: bool, base_ref: str) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for index, item in enumerate(records):
        path = Path(str(item["path"]))
        is_primary = index == 0
        name = path.name
        branch = str(item.get("branch", ""))
        registered = (
            not is_primary
            and NAME.fullmatch(name) is not None
            and path.parent == directory
            and branch == BRANCH_PREFIX + name
        )
        available = path.is_dir() and not path.is_symlink()
        dirty: bool | None = None
        reason = "not_managed"
        if is_primary:
            reason = "primary_worktree"
        elif item.get("locked"):
            reason = "locked"
        elif item.get("prunable"):
            reason = "prunable"
        elif not registered:
            reason = "not_managed"
        elif not available:
            reason = "missing_directory"
        else:
            try:
                dirty = not clean_status(path)
                if dirty:
                    reason = "has_changes_or_ignored_files"
                elif not merged_into(root, branch, base_ref):
                    reason = "branch_not_merged_into_base"
                else:
                    reason = "eligible_with_explicit_confirmation"
            except UnsafeWorktree:
                reason = "unverifiable_git_state"
        output: dict[str, object] = {
            "slot": index,
            "name": name if registered else None,
            "branch": branch.removeprefix("refs/heads/") if branch else None,
            "primary": is_primary,
            "managed": bool(registered),
            "locked": bool(item.get("locked")),
            "prunable": bool(item.get("prunable")),
            "has_changes_or_ignored_files": dirty,
            "removal_eligibility": reason,
        }
        if include_paths:
            output["path"] = str(path)
        out.append(output)
    return out


def run() -> int:
    parser = argparse.ArgumentParser(description="Preview-first, conservative Git worktree management.")
    parser.add_argument("action", choices=("inventory", "create", "remove"), nargs="?", default="inventory")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--name", help="Dedicated managed worktree name, e.g. audit-1")
    parser.add_argument("--apply", action="store_true", help="Explicitly perform create/remove")
    parser.add_argument("--confirm-name", help="For removal, repeat --name exactly")
    parser.add_argument("--merged-into", default="refs/heads/main",
                        help="Local branch which must already contain the worktree tip")
    parser.add_argument("--include-paths", action="store_true",
                        help="Opt in to printing local worktree paths")
    args = parser.parse_args()
    try:
        root = repo_root(args.repo)
        records = worktrees(root)
        primary = Path(str(records[0]["path"])).resolve(strict=False)
        directory = managed_directory(primary)

        if args.action == "inventory":
            if args.apply:
                raise UnsafeWorktree("Inventory is read-only; --apply is not applicable.")
            result = {
                "action": "inventory", "mode": "read_only", "count": len(records),
                "worktrees": inventory(root, records, directory, args.include_paths, args.merged_into),
                "note": "Paths hidden by default. Eligibility is a snapshot, not a removal authorization.",
            }
        else:
            if args.name is None:
                raise UnsafeWorktree("--name is required for create/remove.")
            target = managed_target(directory, args.name)
            branch_ref = BRANCH_PREFIX + args.name
            matched = [r for r in records if Path(str(r["path"])) == target]

            if args.action == "create":
                if target.exists() or target.is_symlink() or matched:
                    raise UnsafeWorktree("Managed target already exists or is registered.")
                exists = git(root, "show-ref", "--verify", "--quiet", branch_ref,
                             allowed=(0, 1)).returncode == 0
                if exists:
                    raise UnsafeWorktree("Dedicated branch already exists; refusing to reuse/reset it.")
                result = {"action": "create", "name": args.name, "branch": "codex/" + args.name,
                          "mode": "preview_only", "created": False,
                          "note": "Explicit --apply creates an isolated worktree at current primary HEAD."}
                if args.apply:
                    # git add -b does not reset an existing branch; no --force.
                    git(primary, "worktree", "add", "-b", "codex/" + args.name,
                        str(target), "HEAD")
                    result["mode"] = "applied"
                    result["created"] = True
            else:
                if len(matched) != 1 or target == primary:
                    raise UnsafeWorktree("Target is not a registered managed linked worktree.")
                item = matched[0]
                if item.get("locked") or item.get("prunable"):
                    raise UnsafeWorktree("Locked or prunable worktrees are never removable by this tool.")
                if item.get("branch") != branch_ref:
                    raise UnsafeWorktree("Target branch does not match managed worktree name.")
                if not target.is_dir() or target.is_symlink():
                    raise UnsafeWorktree("Target directory missing or symlinked.")
                if not clean_status(target):
                    raise UnsafeWorktree("Changes, untracked or ignored files exist; refusing removal.")
                if not merged_into(root, branch_ref, args.merged_into):
                    raise UnsafeWorktree("Branch is not proven contained in the requested local base branch.")
                result = {"action": "remove", "name": args.name, "branch_retained": True,
                          "mode": "preview_only", "removed": False,
                          "note": "Removal requires --apply --confirm-name NAME; branch is retained."}
                if args.apply:
                    if args.confirm_name != args.name:
                        raise UnsafeWorktree("Removal requires --confirm-name matching --name exactly.")
                    # Recheck immediately before running Git's own non-forced safety gate.
                    if not clean_status(target) or not merged_into(root, branch_ref, args.merged_into):
                        raise UnsafeWorktree("Worktree state changed before removal.")
                    git(primary, "worktree", "remove", str(target))
                    result["mode"] = "applied"
                    result["removed"] = True
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0
    except (UnsafeWorktree, OSError, subprocess.TimeoutExpired) as exc:
        # Never emit arbitrary exception details (can include private paths).
        if isinstance(exc, UnsafeWorktree):
            print("BLOCKED: " + str(exc), file=sys.stderr)
        else:
            print("BLOCKED: Git/filesystem check failed; details withheld.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(run())

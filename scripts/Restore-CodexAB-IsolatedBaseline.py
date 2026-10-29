#!/usr/bin/env python3
"""Restore only an isolated A/B baseline config from its verified original.

Explicit local mutation, no Codex model calls, credentials or global config edits.
Preserve the current baseline TOML in a non-overwriting local audit directory.
Never use this on a live Codex session. Existing run reports remain untouched.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import tomllib

BASE = Path(__file__).resolve().with_name("Run-CodexAB.py")
SPEC = importlib.util.spec_from_file_location("ab_restore_runner", BASE)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)

SAFE_ERRORS = {
    "EXPLICIT_RESTORE_REQUIRED", "PILOT_INVALID", "PILOT_IS_SYMLINK",
    "INVALID_BACKUP_LABEL", "BACKUP_ALREADY_EXISTS", "CONFIG_SYMLINK",
    "ORIGINAL_CONFIG_MISMATCH", "BASELINE_CONFIG_NOT_PARSEABLE",
    "CONFIG_SIZE_INVALID", "BASELINE_CHANGED_DURING_BACKUP",
    "NO_RESTORE_NEEDED", "BACKUP_VERIFY_FAILED", "RESTORE_VERIFY_FAILED",
    "BENCHMARK_STATE_INVALID",
}


def restore(pilot_path, backup_label, *, execute=False):
    if not execute:
        raise ValueError("EXPLICIT_RESTORE_REQUIRED")
    if not backup_label.startswith("backup-") or not all(
        char in "abcdefghijklmnopqrstuvwxyz0123456789-" for char in backup_label
    ) or len(backup_label) > 80:
        raise ValueError("INVALID_BACKUP_LABEL")

    pilot = Path(pilot_path).expanduser().resolve(strict=True)
    if pilot.is_symlink() or not pilot.is_dir():
        raise ValueError("PILOT_INVALID")

    # state validates the two AGENTS fingerprints and the CLI version,
    # but does not inspect private Codex session files.
    state = runner.state(pilot)
    if state.get("schema_version") != 1 or state.get("model") != "gpt-6-luna":
        raise ValueError("BENCHMARK_STATE_INVALID")
    baseline = pilot / "baseline-home" / "config.toml"
    canonical = pilot / "candidate-home" / "config.toml"
    if baseline.is_symlink() or canonical.is_symlink():
        raise ValueError("CONFIG_SYMLINK")

    current = runner.read_file(baseline)
    original = runner.read_file(canonical)
    if runner.digest(original) != state.get("config_sha256"):
        raise ValueError("ORIGINAL_CONFIG_MISMATCH")
    if runner.digest(current) == runner.digest(original):
        raise ValueError("NO_RESTORE_NEEDED")
    try:
        tomllib.loads(current.decode("utf-8"))
        tomllib.loads(original.decode("utf-8"))
    except (UnicodeError, ValueError):
        raise ValueError("BASELINE_CONFIG_NOT_PARSEABLE") from None

    # Backup is kept INSIDE the already-isolated pilot, outside both homes.
    # There is no overwrite of a previous backup, config, or run output.
    audit = pilot / "audit-backups"
    if audit.is_symlink():
        raise ValueError("PILOT_INVALID")
    dest = audit / backup_label
    if dest.exists() or dest.is_symlink():
        raise ValueError("BACKUP_ALREADY_EXISTS")

    audit.mkdir(exist_ok=True)
    dest.mkdir(exist_ok=False)
    archive = dest / "baseline-config-before-restore.toml"
    archive.write_bytes(current)
    if runner.digest(archive.read_bytes()) != runner.digest(current):
        raise ValueError("BACKUP_VERIFY_FAILED")
    metadata = {
        "schema_version": 1,
        "operation": "audited_baseline_config_restore",
        "executed_at_unix_s": int(time.time()),
        "original_recorded_config_matches_candidate": True,
        "previous_baseline_sha256": runner.digest(current),
        "restored_sha256": runner.digest(original),
        "baseline_agents_unchanged_by_script": True,
        "candidate_config_unchanged_by_script": True,
        "auth_files_unchanged_by_script": True,
        "codex_model_calls": 0,
        "note": "Does not authorize a matched A/B comparison across prior TUI sessions.",
    }
    runner.save_json(dest / "restore-audit.json", metadata)

    # Reject a concurrent change at the last possible point; do not operate
    # while Codex sessions using this isolated baseline are still running.
    if runner.digest(runner.read_file(baseline)) != runner.digest(current):
        raise ValueError("BASELINE_CHANGED_DURING_BACKUP")

    tmp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=".config-restore-", suffix=".tmp",
            dir=baseline.parent, delete=False
        ) as fh:
            tmp_name = fh.name
            fh.write(original)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, baseline)
        tmp_name = None
    finally:
        if tmp_name is not None:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass

    if runner.digest(runner.read_file(baseline)) != runner.digest(original):
        raise ValueError("RESTORE_VERIFY_FAILED")

    print(json.dumps({
        "status": "RESTORED",
        "operation": "audited_isolated_baseline_config_restore",
        "backup_label": backup_label,
        "previous_baseline_archived": True,
        "baseline_matches_recorded_original": True,
        "candidate_original_unchanged": True,
        "credentials_copied": False,
        "global_config_touched": False,
        "codex_model_calls": 0,
        "history_restored_or_deleted": False,
    }, indent=2))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pilot", required=True)
    p.add_argument("--backup-label", required=True)
    p.add_argument("--execute", action="store_true",
                   help="Explicit permission to archive and reset isolated baseline config.toml")
    args = p.parse_args(argv)
    try:
        return restore(args.pilot, args.backup_label, execute=args.execute)
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        message = str(exc)
        code = message if message in SAFE_ERRORS else "RESTORE_PRECONDITION_FAILED"
        print("STOP: " + code + " (no config content or private paths printed)",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

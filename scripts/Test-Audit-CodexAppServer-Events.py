#!/usr/bin/env python3
"""Offline synthetic tests for P1.1 v0.165.0 app-server event audit."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

SRC = Path(__file__).with_name("Audit-CodexAppServer-Events.py")
SPEC = importlib.util.spec_from_file_location("p11_appserver_audit", SRC)
app = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(app)


def collab(method, ident, tool="spawnAgent", status="inProgress", receivers=None):
    return {"method": method, "params": {
        "threadId": "private-parent-thread-id",
        "turnId": "private-parent-turn-id",
        "item": {
            "type": "collabAgentToolCall", "id": ident,
            "tool": tool, "status": status,
            "receiverThreadIds": receivers or [],
            "prompt": "PRIVATE_PROMPT_NEVER_EXPORT",
            "senderThreadId": "private-parent-thread-id",
            "model": "worker-model-private",
        }}}


def activity(kind, ident):
    return {"method": "item/completed", "params": {
        "item": {"type": "subAgentActivity", "id": "activity-" + kind,
                 "kind": kind, "agentThreadId": ident,
                 "agentPath": "PRIVATE_PATH_NEVER_EXPORT"}}}


def token_event(total, thread="private-parent-thread-id"):
    return {"method": "thread/tokenUsage/updated", "params": {
        "threadId": thread, "turnId": "private-parent-turn-id",
        "tokenUsage": {"total": {
            "totalTokens": total, "inputTokens": total,
            "cachedInputTokens": total // 2, "cacheWriteInputTokens": 0,
            "outputTokens": 0, "reasoningOutputTokens": 0
        }, "last": {}, "modelContextWindow": None}}}


class OfflineAuditTests(unittest.TestCase):
    def events(self):
        return [
            collab("item/started", "private-tool-id"),
            collab("item/completed", "private-tool-id", status="completed",
                   receivers=["PRIVATE_WORKER_ID"]),
            activity("started", "PRIVATE_WORKER_ID"),
            activity("completed", "PRIVATE_WORKER_ID"),
            token_event(105),
            token_event(110),
            {"method": "turn/completed", "params": {
                "threadId": "PRIVATE_PARENT", "turn": {
                    "status": "completed", "items": [
                        {"type": "agentMessage", "text": "SENSITIVE_TEXT"}
                    ]}}},
            {"method": "item/agentMessage/delta", "params": {
                "delta": "SECRET_THAT_MUST_NEVER_BE_OUTPUT"}},
        ]

    def test_events_count_and_redact(self):
        result = app.audit(self.events())
        self.assertEqual(result["event_count"], 8)
        self.assertEqual(result["collab_calls"]["spawnAgent"]["started"], 1)
        self.assertEqual(result["collab_calls"]["spawnAgent"]["completed"], 1)
        self.assertEqual(result["subagent_started_and_completed_observed"], 1)
        self.assertEqual(result["token_usage_thread_count"], 1)
        self.assertEqual(result["token_latest_per_thread_sum_descriptive_only"], 110)
        self.assertEqual(result["turn_outcomes"]["completed"], 1)
        self.assertFalse(result["independently_attests_original_tui"])
        serialized = json.dumps(result)
        for secret in ("PRIVATE", "SENSITIVE", "SECRET", "PROMPT", "agentPath"):
            self.assertNotIn(secret, serialized)

    def test_read_file_and_no_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            data = "\n".join(json.dumps(e) for e in self.events()) + "\n"
            path.write_text(data, encoding="utf-8")
            original = path.read_bytes()
            result = app.audit(app.read_events(path))
            self.assertEqual(result["event_count"], 8)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_unmatched_completed_is_not_a_verified_pair(self):
        result = app.audit([collab("item/completed", "x", status="completed", receivers=["r"])])
        self.assertEqual(result["unpaired_collab_completions"], 1)
        self.assertEqual(result["subagent_started_and_completed_observed"], 0)

    def test_missing_receiver_rejected(self):
        with self.assertRaisesRegex(app.AuditError, "SUCCESSFUL_SPAWN_WITHOUT_RECEIVER"):
            app.audit([collab("item/completed", "x", status="completed")])

    def test_duplicate_collab_rejected(self):
        item = collab("item/started", "x")
        with self.assertRaisesRegex(app.AuditError, "DUPLICATE_ITEM"):
            app.audit([item, item])

    def test_invalid_usage_and_counter_regression(self):
        with self.assertRaisesRegex(app.AuditError, "TOKEN_COUNTER_REGRESSION"):
            app.audit([token_event(300), token_event(299)])
        wrong = token_event(100)
        wrong["params"]["tokenUsage"]["total"]["cachedInputTokens"] = 101
        with self.assertRaisesRegex(app.AuditError, "TOKEN_ACCOUNTING_INVALID"):
            app.audit([wrong])

    def test_invalid_jsonl_fails_without_logging_source(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "events.jsonl"
            file.write_text('{"method": "item/started"}\nINVALID SECRET', encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                rc = app.main(["--input", str(file)])
            self.assertEqual(rc, 2)
            self.assertNotIn("SECRET", stderr.getvalue())
            self.assertNotIn(str(file), stderr.getvalue())

    def test_turn_failure_observed_not_claimed_pass(self):
        result = app.audit([{"method": "turn/completed", "params": {
            "turn": {"status": "failed", "error": "PRIVATE_ERROR"}}}])
        self.assertEqual(result["turn_outcomes"]["failed"], 1)
        self.assertFalse(result["effective_sandbox_policy_verified"])

    def test_unknown_events_not_echoed(self):
        result = app.audit([{"method": "rawResponse/completed", "params": {
            "raw": "PRIVATE_LONG_STRING"}}])
        self.assertEqual(result["ignored_event_count"], 1)
        self.assertNotIn("PRIVATE", json.dumps(result))


if __name__ == "__main__":
    unittest.main()

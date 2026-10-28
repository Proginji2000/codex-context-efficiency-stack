#!/usr/bin/env python3
"""Offline validation for fictional dashboard pilot fixture; no Codex/npm/network."""
import json
from datetime import date
from pathlib import Path

FILE = (Path(__file__).resolve().parent.parent /
        "examples/dashboard-pilot/fixtures/synthetic-warehouse-kpis.json")
FIELDS = (
    "orders_prepared", "orders_target", "late_orders", "anomalies", "backlog_end"
)


def aggregate(rows):
    prepared = sum(row["orders_prepared"] for row in rows)
    target = sum(row["orders_target"] for row in rows)
    late = sum(row["late_orders"] for row in rows)
    anomalies = sum(row["anomalies"] for row in rows)
    latest = {}
    for row in rows:
        if row["zone"] not in latest or row["date"] > latest[row["zone"]]["date"]:
            latest[row["zone"]] = row
    return {
        "prepared": prepared,
        "target": target,
        "achievement_pct": 100 * prepared / target if target else None,
        "late": late,
        "anomalies": anomalies,
        "backlog_end": sum(row["backlog_end"] for row in latest.values()),
    }


def filter_rows(rows, start, end, zone=None):
    return [
        row for row in rows if start <= row["date"] <= end and
        (zone is None or row["zone"] == zone)
    ]


def main():
    data = json.loads(FILE.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["data_classification"] == "synthetic_only_no_production_data"
    assert data["zones"] == ["A", "B", "C"]
    rows = data["rows"]
    assert len(rows) == 42
    expected_keys = {"date", "zone", *FIELDS}
    dates = set()
    combinations = set()
    for row in rows:
        assert set(row) == expected_keys
        date.fromisoformat(row["date"])
        assert "2026-10-01" <= row["date"] <= "2026-10-14"
        assert row["zone"] in data["zones"]
        dates.add(row["date"])
        combinations.add((row["date"], row["zone"]))
        assert all(type(row[key]) is int and row[key] >= 0 for key in FIELDS)
        assert row["orders_target"] > 0
        assert row["late_orders"] <= row["orders_prepared"]
    assert len(dates) == 14 and len(combinations) == 42
    assert combinations == {(f"2026-10-{day:02d}", zone)
                            for day in range(1, 15) for zone in "ABC"}

    all_metrics = aggregate(rows)
    assert all_metrics["prepared"] > 0
    assert all_metrics["target"] > 0
    assert all_metrics["late"] <= all_metrics["prepared"]
    assert all_metrics["achievement_pct"] > 0

    zone_a = filter_rows(rows, "2026-10-01", "2026-10-14", "A")
    assert len(zone_a) == 14
    only_a = aggregate(zone_a)
    assert only_a["backlog_end"] == zone_a[-1]["backlog_end"]
    assert only_a["prepared"] == sum(row["orders_prepared"] for row in zone_a)

    latest_day = filter_rows(rows, "2026-10-14", "2026-10-14")
    assert len(latest_day) == 3
    assert aggregate(latest_day)["backlog_end"] == sum(
        row["backlog_end"] for row in latest_day)

    missing = filter_rows(rows, "2026-11-01", "2026-11-02")
    assert missing == []
    zero = aggregate(missing)
    assert zero["prepared"] == zero["target"] == zero["backlog_end"] == 0
    assert zero["achievement_pct"] is None

    # Ensure the canonical fixture cannot silently become a live data dump.
    text = FILE.read_text(encoding="utf-8").lower()
    assert not any(term in text for term in (
        "oracle", "reflex", "customer_id", "apikey", "password",
        "client_secret", "token", "real_data", "mobivia",
    ))

    print("PASS: 42 synthetic rows, unique day/zone coverage, metrics, "
          "last-day backlog, zero and privacy invariants.")


if __name__ == "__main__":
    main()

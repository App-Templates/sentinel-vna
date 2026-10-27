#!/usr/bin/env python3
"""Phase 09 Plan 02 — test suite for scripts/deprecate_legacy_alerts.py.

TDD-RED first (this file), then GREEN after Task 2 authors the script.

Fixture strategy: each test creates a tempfile `.db`, builds the Phase-09
post-01 schema (SQL inlined — keeps test self-contained vs. importing
models.py), seeds 7 known rows (legacy + modern), invokes the script via
subprocess, asserts DB state.

Isolation: tempfile per test + teardown unlink → zero live-DB pollution.

Run:  .venv/bin/python scripts/test_deprecate_legacy_alerts.py
Exit: 0 = all tests pass, 1 = failures detected.
"""
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "deprecate_legacy_alerts.py"
PYTHON = sys.executable

# D-15 authoritative reason text (byte-for-byte — DO NOT modify without
# amending CONTEXT.md §D-15 AND scripts/deprecate_legacy_alerts.py).
EXPECTED_REASON = (
    "v1.0 schema stale: legacy channel naming + v1.2 baseline divergence "
    "(Phase 09 deprecation)"
)

# ERRATA I-1 (2026-04-23): severity is an EXPLICIT 4th fixture column —
# not derived from alert_id via rsplit. Less fragile for future fixtures.
# Columns: (alert_id, timestamp, channel_group, severity, expected_deprecated)
FIXTURE_ROWS = [
    # --- legacy: pre-cutoff + legacy channel → deprecated=1 ---
    ("ALT-20251201-100000-P1", "2025-12-01T10:00:00", "GOOGLE",       "P1", 1),
    ("ALT-20260115-140000-P2", "2026-01-15T14:00:00", "OPEN_BIDDING", "P2", 1),
    ("ALT-20260131-235959-P0", "2026-01-31T23:59:59", "GOOGLE",       "P0", 1),
    # --- edge: AT cutoff (excluded by `<` not `<=`) → deprecated=0 ---
    ("ALT-20260201-000000-P1", "2026-02-01T00:00:00", "GOOGLE",       "P1", 0),
    # --- post-cutoff legacy channel → deprecated=0 (timestamp filter) ---
    ("ALT-20260215-120000-P1", "2026-02-15T12:00:00", "GOOGLE",       "P1", 0),
    # --- pre-cutoff modern channel → deprecated=0 (channel filter) ---
    ("ALT-20260110-090000-P2", "2026-01-10T09:00:00", "GOOGLE_ADEX",  "P2", 0),
    ("ALT-20260125-150000-P1", "2026-01-25T15:00:00", "DIRECT",       "P1", 0),
]

SCHEMA_SQL = """
CREATE TABLE alerts (
    alert_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('P0', 'P1', 'P2')),
    channel_group TEXT NOT NULL CHECK(channel_group IN ('GOOGLE_ADEX', 'OPEN_BIDDING', 'HEADER_BIDDING_MAGNITE', 'HEADER_BIDDING_PUBMATIC', 'TAM', 'DIRECT', 'DEAL', 'GOOGLE')),
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK(status IN ('OPEN', 'ACK', 'RESOLVED', 'SNOOZED')),
    alert_rule TEXT NOT NULL CHECK(alert_rule IN ('A0', 'A1', 'A2', 'A3', 'A5', 'A6', 'A7', 'A8')),
    revenue_current REAL NOT NULL,
    revenue_baseline REAL NOT NULL,
    revenue_delta_pct REAL NOT NULL,
    triage_label TEXT NOT NULL,
    contributors_json TEXT DEFAULT '[]',
    geo_breakdown_json TEXT DEFAULT '[]',
    environment_split_json TEXT DEFAULT '{}',
    insights_json TEXT DEFAULT '{}',
    execution_time_sec REAL DEFAULT 0.0,
    data_source TEXT DEFAULT 'athena',
    config_version TEXT DEFAULT '1.0.0',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deprecated INTEGER NOT NULL DEFAULT 0 CHECK(deprecated IN (0, 1)),
    deprecation_reason TEXT
);
"""


class TestDeprecateLegacyAlerts(unittest.TestCase):
    """TDD tests — 12 cases covering cutoff, channel whitelist, idempotency,
    dry-run, exit codes, reason text exact match."""

    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db", prefix="dep_test_")
        os.close(fd)
        self._create_schema_and_seed()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def _create_schema_and_seed(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.executescript(SCHEMA_SQL)
            for alert_id, ts, channel, severity, _expected in FIXTURE_ROWS:
                conn.execute(
                    """INSERT INTO alerts (
                         alert_id, timestamp, severity, channel_group, alert_rule,
                         revenue_current, revenue_baseline, revenue_delta_pct,
                         triage_label, created_at, updated_at
                       ) VALUES (?, ?, ?, ?, 'A1', 100.0, 200.0, -0.5, 'test', ?, ?)""",
                    (alert_id, ts, severity, channel, ts, ts),
                )
            conn.commit()
        finally:
            conn.close()

    def _run(self, *extra_args):
        return subprocess.run(
            [PYTHON, str(SCRIPT), "--db-path", self.db_path, *extra_args],
            capture_output=True, text=True,
        )

    def _count(self, where_clause: str, params=()) -> int:
        conn = sqlite3.connect(self.db_path)
        try:
            return conn.execute(
                f"SELECT COUNT(*) FROM alerts WHERE {where_clause}", params
            ).fetchone()[0]
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    # Cutoff correctness
    # ------------------------------------------------------------------ #

    def test_cutoff_marks_expected_3_rows(self):
        """After the script runs, exactly 3 rows should be deprecated=1."""
        result = self._run()
        self.assertEqual(
            result.returncode, 0,
            f"Script exit {result.returncode}: stderr={result.stderr!r} stdout={result.stdout!r}",
        )
        self.assertEqual(self._count("deprecated=1"), 3)

    def test_cutoff_preserves_expected_4_rows(self):
        """The remaining 4 rows should stay deprecated=0 (non-legacy / post-cutoff)."""
        self._run()
        self.assertEqual(self._count("deprecated=0"), 4)

    def test_timestamp_boundary_exclusive(self):
        """Row with timestamp exactly equal to cutoff is NOT deprecated (`<` not `<=`)."""
        self._run()
        self.assertEqual(
            self._count("alert_id=? AND deprecated=0", ("ALT-20260201-000000-P1",)), 1
        )

    def test_channel_whitelist_enforced_pre_cutoff_modern_channel(self):
        """Pre-cutoff GOOGLE_ADEX row stays deprecated=0 (modern channel excluded)."""
        self._run()
        self.assertEqual(
            self._count("alert_id=? AND deprecated=0", ("ALT-20260110-090000-P2",)), 1
        )

    def test_channel_whitelist_enforced_pre_cutoff_direct(self):
        """Pre-cutoff DIRECT row stays deprecated=0 (modern channel excluded)."""
        self._run()
        self.assertEqual(
            self._count("alert_id=? AND deprecated=0", ("ALT-20260125-150000-P1",)), 1
        )

    # ------------------------------------------------------------------ #
    # Reason text invariants (D-15)
    # ------------------------------------------------------------------ #

    def test_deprecation_reason_exact_text(self):
        """Every deprecated row has deprecation_reason = EXPECTED_REASON (byte match)."""
        self._run()
        conn = sqlite3.connect(self.db_path)
        try:
            rows = conn.execute(
                "SELECT deprecation_reason FROM alerts WHERE deprecated=1"
            ).fetchall()
        finally:
            conn.close()
        self.assertEqual(len(rows), 3)
        for (reason,) in rows:
            self.assertEqual(reason, EXPECTED_REASON)

    def test_non_deprecated_rows_reason_is_null(self):
        """deprecated=0 rows MUST still have deprecation_reason IS NULL."""
        self._run()
        self.assertEqual(self._count("deprecated=0 AND deprecation_reason IS NOT NULL"), 0)
        self.assertEqual(self._count("deprecated=0 AND deprecation_reason IS NULL"), 4)

    # ------------------------------------------------------------------ #
    # Idempotency + dry-run
    # ------------------------------------------------------------------ #

    def test_idempotency_second_run_is_noop(self):
        """Second invocation does not change state; stdout contains IDEMPOTENT-NOOP."""
        first = self._run()
        self.assertEqual(first.returncode, 0)
        # Snapshot post-first-run state
        dep_before = self._count("deprecated=1")
        non_before = self._count("deprecated=0")
        second = self._run()
        self.assertEqual(second.returncode, 0)
        self.assertIn("IDEMPOTENT-NOOP", second.stdout)
        self.assertEqual(self._count("deprecated=1"), dep_before)
        self.assertEqual(self._count("deprecated=0"), non_before)

    def test_dry_run_does_not_write(self):
        """--dry-run prints count without mutating; all rows stay deprecated=0."""
        result = self._run("--dry-run")
        self.assertEqual(result.returncode, 0)
        self.assertIn("DRY RUN", result.stdout)
        # Must contain the count "3" (number of rows that WOULD be updated).
        self.assertIn("3", result.stdout)
        # State unchanged — no write.
        self.assertEqual(self._count("deprecated=1"), 0)
        self.assertEqual(self._count("deprecated=0"), 7)

    # ------------------------------------------------------------------ #
    # Exit codes
    # ------------------------------------------------------------------ #

    def test_exit_code_0_on_success(self):
        result = self._run()
        self.assertEqual(result.returncode, 0)

    def test_exit_code_0_on_idempotent_noop(self):
        self._run()
        result = self._run()
        self.assertEqual(result.returncode, 0)

    def test_exit_code_1_on_db_missing(self):
        """--db-path to a nonexistent file → exit 1 + stderr mentions FATAL: DB not found."""
        result = subprocess.run(
            [PYTHON, str(SCRIPT), "--db-path", "/nonexistent/path/does_not_exist.db"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("FATAL: DB not found", result.stderr)


if __name__ == "__main__":
    unittest.main()

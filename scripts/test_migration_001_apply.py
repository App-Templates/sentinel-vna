#!/usr/bin/env python3
"""
Phase 08 Plan 03 Task 3 — Post-Apply Smoke-Test Suite.

Validates the LIVE data/vna_alerts.db after migration 001 has been applied
(Plan 03 Task 2 is a prerequisite). Tests run against the live DB — not a
tempfile — to confirm the actual production state.

Run:  .venv/bin/python scripts/test_migration_001_apply.py
Exit: 0 = all tests pass, 1 = failures detected.

Constraints:
- stdlib only (sqlite3, unittest, pathlib, re, sys)
- requires data/vna_alerts.db in post-migration-001 state
- tearDown DELETEs all synthetic rows (data_source='phase08-test') to
  leave no test pollution in the live DB
"""

import re
import sqlite3
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "data" / "vna_alerts.db"
BAK_PATH = REPO_ROOT / "data" / "vna_alerts.db.pre-phase08.bak"
MODELS_PY = REPO_ROOT / "backend" / "db" / "models.py"

# 8 valid channel_group values (Phase 08 SCHEMA-01)
VALID_CHANNELS = (
    "GOOGLE_ADEX", "OPEN_BIDDING", "HEADER_BIDDING_MAGNITE", "HEADER_BIDDING_PUBMATIC",
    "TAM", "DIRECT", "DEAL", "GOOGLE",
)

# 8 valid alert_rule values (A4 deliberately absent)
VALID_RULES = ("A0", "A1", "A2", "A3", "A5", "A6", "A7", "A8")

# Marker for synthetic test rows
TEST_DATA_SOURCE = "phase08-test"

# alert_id format: ALT-YYYYMMDD-HHMMSS-P[012]
# Use a fixed date that is deterministic and passes the regex validator.
# Each test uses a unique counter embedded in HHMMSS to avoid PK collision.
_ALERT_ID_COUNTER = [0]


def _make_alert_id() -> str:
    """Generate a valid alert_id in the format ALT-YYYYMMDD-HHMMSS-P1.

    WR-08: `suffix` parameter removed (was unused dead argument — signal of a
    copy-paste origin with richer semantics that never got cleaned up).
    """
    _ALERT_ID_COUNTER[0] += 1
    seq = _ALERT_ID_COUNTER[0]
    # Encode sequence into HHMMSS: max 999999, plenty for our 64 rows
    hh = (seq // 10000) % 100
    mm = (seq // 100) % 100
    ss = seq % 100
    return f"ALT-20260423-{hh:02d}{mm:02d}{ss:02d}-P1"


def _base_row(channel: str, rule: str, alert_id: str) -> dict:
    """Return a minimal valid alerts row dict for a raw INSERT."""
    return {
        "alert_id": alert_id,
        "timestamp": "2026-04-23T00:00:00Z",
        "severity": "P1",
        "channel_group": channel,
        "status": "OPEN",
        "alert_rule": rule,
        "revenue_current": 0.0,
        "revenue_baseline": 0.0,
        "revenue_delta_pct": 0.0,
        "triage_label": "TEST",
        "contributors_json": "[]",
        "geo_breakdown_json": "[]",
        "environment_split_json": "{}",
        "insights_json": "{}",
        "execution_time_sec": 0.0,
        "data_source": TEST_DATA_SOURCE,
        "config_version": "1.0.0",
        "created_at": "2026-04-23T00:00:00Z",
        "updated_at": "2026-04-23T00:00:00Z",
    }


def _insert_alert(conn: sqlite3.Connection, row: dict) -> None:
    conn.execute(
        """
        INSERT INTO alerts(
            alert_id, timestamp, severity, channel_group, status, alert_rule,
            revenue_current, revenue_baseline, revenue_delta_pct, triage_label,
            contributors_json, geo_breakdown_json, environment_split_json,
            insights_json, execution_time_sec, data_source, config_version,
            created_at, updated_at
        ) VALUES (
            :alert_id, :timestamp, :severity, :channel_group, :status, :alert_rule,
            :revenue_current, :revenue_baseline, :revenue_delta_pct, :triage_label,
            :contributors_json, :geo_breakdown_json, :environment_split_json,
            :insights_json, :execution_time_sec, :data_source, :config_version,
            :created_at, :updated_at
        )
        """,
        row,
    )


def _cleanup_synthetic_rows(conn: sqlite3.Connection) -> None:
    """Delete all synthetic rows inserted by this test suite."""
    # WR-04: parameter binding instead of f-string interpolation.
    # TEST_DATA_SOURCE is a module constant today, but this file is the
    # template for Phase 09+ tests and f-string SQL is a latent injection vector.
    conn.execute("DELETE FROM alerts WHERE data_source = ?", (TEST_DATA_SOURCE,))
    conn.execute(
        "DELETE FROM pending_notifications WHERE alert_id LIKE 'ALT-20260423-%'"
    )
    conn.commit()


class TestMigration001Apply(unittest.TestCase):
    """Post-apply smoke-test suite against the LIVE data/vna_alerts.db."""

    def setUp(self) -> None:
        if not DB_PATH.exists():
            self.fail(f"Live DB not found at {DB_PATH}. Run Task 2 first.")
        # WR-08: reset counter so alert_ids are deterministic per-test,
        # independent of test discovery order or re-runs in the same process.
        _ALERT_ID_COUNTER[0] = 0
        self.conn = sqlite3.connect(str(DB_PATH))
        self.conn.execute("PRAGMA foreign_keys=ON;")

    def tearDown(self) -> None:
        # Always clean up synthetic rows — even if the test failed mid-way.
        _cleanup_synthetic_rows(self.conn)
        self.conn.close()

    # -------------------------------------------------------------------------
    # Test 1: alerts table has Phase 08 schema
    # -------------------------------------------------------------------------
    def test_live_db_has_phase_08_schema(self):
        """sqlite_master.alerts.sql contains 'GOOGLE_ADEX', 'A8', does NOT contain 'A4'."""
        row = self.conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='alerts'"
        ).fetchone()
        self.assertIsNotNone(row, "alerts table missing from sqlite_master")
        alerts_sql = row[0]
        self.assertIn("'GOOGLE_ADEX'", alerts_sql, "GOOGLE_ADEX not in alerts schema")
        self.assertIn("'HEADER_BIDDING_MAGNITE'", alerts_sql, "HEADER_BIDDING_MAGNITE missing")
        self.assertIn("'HEADER_BIDDING_PUBMATIC'", alerts_sql, "HEADER_BIDDING_PUBMATIC missing")
        self.assertIn("'TAM'", alerts_sql, "TAM missing from alerts schema")
        self.assertIn("'DIRECT'", alerts_sql, "DIRECT missing from alerts schema")
        self.assertIn("'DEAL'", alerts_sql, "DEAL missing from alerts schema")
        self.assertIn("'GOOGLE'", alerts_sql, "GOOGLE missing from alerts schema")
        self.assertIn("'A8'", alerts_sql, "A8 not in alerts schema")
        self.assertNotIn("'A4'", alerts_sql, "FORBIDDEN: A4 is present in alerts schema")

    # -------------------------------------------------------------------------
    # Test 2: pending_notifications has tightened CHECKs
    # -------------------------------------------------------------------------
    def test_live_db_pending_notifications_tightened(self):
        """pending_notifications has severity CHECK and 8-value channel_group CHECK."""
        row = self.conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='pending_notifications'"
        ).fetchone()
        self.assertIsNotNone(row, "pending_notifications table missing")
        pn_sql = row[0]
        self.assertIn("CHECK(severity IN ('P0', 'P1', 'P2'))", pn_sql,
                      "pending_notifications.severity CHECK missing or wrong format")
        self.assertIn("'GOOGLE_ADEX'", pn_sql, "GOOGLE_ADEX missing from pending_notifications")
        self.assertIn("'HEADER_BIDDING_MAGNITE'", pn_sql,
                      "HEADER_BIDDING_MAGNITE missing from pending_notifications")

    # -------------------------------------------------------------------------
    # Test 3: backup exists and proves pre-apply state (W-01 strengthened)
    # -------------------------------------------------------------------------
    def test_backup_exists_and_is_pre_apply(self):
        """Backup exists AND its sqlite_master shows the STALE 2-value channel_group CHECK.

        W-01 strengthening: verify .bak actually contains the pre-migration stale
        schema (not just that the file exists). The stale schema has:
          - channel_group IN ('GOOGLE', 'OPEN_BIDDING')  (2 values)
          - GOOGLE_ADEX NOT present in alerts.sql
          - A4 NOT present (A0-A3 only, pre-Phase-08 alert_rule values)
        This proves .bak is the pre-apply snapshot, not an empty or post-apply DB.
        """
        self.assertTrue(BAK_PATH.exists(), f"Backup not found at {BAK_PATH}")

        bak_conn = sqlite3.connect(str(BAK_PATH))
        try:
            row = bak_conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='alerts'"
            ).fetchone()
            self.assertIsNotNone(row, "alerts table missing from backup DB")
            bak_alerts_sql = row[0]
            # Backup MUST NOT have GOOGLE_ADEX (that would mean it's post-apply)
            self.assertNotIn(
                "'GOOGLE_ADEX'", bak_alerts_sql,
                "Backup contains GOOGLE_ADEX — it's POST-apply, not pre-apply snapshot!"
            )
            # Backup should have the stale 2-value channel_group CHECK
            self.assertIn(
                "'GOOGLE'", bak_alerts_sql,
                "GOOGLE missing from backup — backup may not be the pre-Phase-08 stale DB"
            )
            # Backup MUST NOT have A4 (A4 is never in any schema version per design)
            # but it also MUST NOT have A8 (A8 is Phase 08 expanded)
            self.assertNotIn(
                "'A8'", bak_alerts_sql,
                "Backup contains A8 — it's POST-apply, not pre-apply snapshot!"
            )
        finally:
            bak_conn.close()

    # -------------------------------------------------------------------------
    # Test 4: 8x8=64 valid INSERTs succeed + teardown preserves row counts
    # -------------------------------------------------------------------------
    def test_insert_succeeds_for_each_valid_channel_and_rule(self):
        """INSERT for each of 8 channels x 8 rules (64 combos) succeeds.

        After insertions, DELETE all 64 synthetic rows. Row count before must
        equal row count after (tearDown handles final cleanup, but this test
        asserts the delete worked correctly).
        """
        pre_count = self.conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]

        inserted_ids = []
        for ch in VALID_CHANNELS:
            for ru in VALID_RULES:
                aid = _make_alert_id()
                row = _base_row(ch, ru, aid)
                try:
                    _insert_alert(self.conn, row)
                    self.conn.commit()
                    inserted_ids.append(aid)
                except sqlite3.IntegrityError as e:
                    self.fail(
                        f"INSERT failed for valid channel={ch!r} rule={ru!r}: {e!r}"
                    )

        self.assertEqual(len(inserted_ids), 64, "Expected 64 successful inserts")

        # Verify count increased by exactly 64
        mid_count = self.conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        self.assertEqual(mid_count, pre_count + 64, "Expected pre_count + 64 rows mid-test")

        # Delete all synthetic rows (WR-04: parameter binding, not f-string).
        self.conn.execute(
            "DELETE FROM alerts WHERE data_source = ?", (TEST_DATA_SOURCE,)
        )
        self.conn.commit()

        # Verify count restored
        post_count = self.conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        self.assertEqual(post_count, pre_count, "Row count not restored after DELETE — data leaked!")

    # -------------------------------------------------------------------------
    # Test 5: INSERT with channel_group='BOGUS' raises IntegrityError
    # -------------------------------------------------------------------------
    def test_insert_fails_for_bogus_channel(self):
        """INSERT with channel_group='BOGUS' raises sqlite3.IntegrityError."""
        aid = _make_alert_id()
        row = _base_row("BOGUS", "A0", aid)
        with self.assertRaises(sqlite3.IntegrityError):
            _insert_alert(self.conn, row)
            self.conn.commit()
        # Rollback so tearDown doesn't see a dirty transaction
        self.conn.rollback()
        # Confirm no row was added
        count = self.conn.execute(
            "SELECT COUNT(*) FROM alerts WHERE alert_id=?", (aid,)
        ).fetchone()[0]
        self.assertEqual(count, 0, "Row with BOGUS channel should not exist")

    # -------------------------------------------------------------------------
    # Test 6: INSERT with alert_rule='A4' raises IntegrityError (explicit negative)
    # -------------------------------------------------------------------------
    def test_insert_fails_for_a4_rule(self):
        """INSERT with alert_rule='A4' raises sqlite3.IntegrityError.

        Explicit proof that A4 is rejected by the live DB CHECK constraint.
        A4 is permanently excluded from the alert_rule domain per Phase 08 SCHEMA-01.
        """
        aid = _make_alert_id()
        row = _base_row("GOOGLE_ADEX", "A4", aid)
        with self.assertRaises(sqlite3.IntegrityError):
            _insert_alert(self.conn, row)
            self.conn.commit()
        self.conn.rollback()
        # Confirm A4 row was not added
        count = self.conn.execute(
            "SELECT COUNT(*) FROM alerts WHERE alert_id=?", (aid,)
        ).fetchone()[0]
        self.assertEqual(count, 0, "A4 alert_rule row should not exist in DB")

    # -------------------------------------------------------------------------
    # Test 7: pending_notifications INSERT fails for bogus severity
    # -------------------------------------------------------------------------
    def test_pending_notifications_insert_fails_for_bogus_severity(self):
        """INSERT into pending_notifications with severity='BOGUS' raises IntegrityError."""
        # First insert a valid alert as FK anchor
        aid = _make_alert_id()
        alert_row = _base_row("GOOGLE_ADEX", "A0", aid)
        _insert_alert(self.conn, alert_row)
        self.conn.commit()

        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                """
                INSERT INTO pending_notifications(alert_id, severity, channel_group, timestamp, created_at)
                VALUES (?, 'BOGUS', 'GOOGLE_ADEX', '2026-04-23T00:00:00Z', '2026-04-23T00:00:00Z')
                """,
                (aid,),
            )
            self.conn.commit()
        self.conn.rollback()

    # -------------------------------------------------------------------------
    # Test 8: pending_notifications INSERT fails for bogus channel_group
    # -------------------------------------------------------------------------
    def test_pending_notifications_insert_fails_for_bogus_channel(self):
        """INSERT into pending_notifications with channel_group='BOGUS' raises IntegrityError."""
        aid = _make_alert_id()
        alert_row = _base_row("GOOGLE_ADEX", "A0", aid)
        _insert_alert(self.conn, alert_row)
        self.conn.commit()

        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                """
                INSERT INTO pending_notifications(alert_id, severity, channel_group, timestamp, created_at)
                VALUES (?, 'P1', 'BOGUS', '2026-04-23T00:00:00Z', '2026-04-23T00:00:00Z')
                """,
                (aid,),
            )
            self.conn.commit()
        self.conn.rollback()

    # -------------------------------------------------------------------------
    # Test 9: vna_schema_migrations ledger has migration 001 row
    # -------------------------------------------------------------------------
    def test_ledger_has_migration_row(self):
        """vna_schema_migrations has exactly 1 row for migration_id='001_expand_channel_groups'."""
        count = self.conn.execute(
            "SELECT COUNT(*) FROM vna_schema_migrations "
            "WHERE migration_id='001_expand_channel_groups'"
        ).fetchone()[0]
        self.assertEqual(count, 1, "Migration ledger should have exactly 1 row for 001")

    # -------------------------------------------------------------------------
    # Test 10: alerts byte-identical to models.py SQL_CREATE_ALERTS
    # -------------------------------------------------------------------------
    def test_alerts_byte_identical_to_models_py(self):
        """Regression guard: alerts CHECK clauses match models.py SQL_CREATE_ALERTS
        byte-for-byte (whitespace-normalized per clause).

        This is success criterion 2 from ROADMAP, re-verified as a standalone test
        so future drifts in models.py are caught at test time, not deploy time.
        """
        models_src = MODELS_PY.read_text(encoding="utf-8")
        m = re.search(r'SQL_CREATE_ALERTS\s*=\s*"""(.*?)"""', models_src, re.DOTALL)
        self.assertIsNotNone(m, "SQL_CREATE_ALERTS not found in models.py")
        models_sql = m.group(1)

        db_sql = self.conn.execute(
            "SELECT sql FROM sqlite_master WHERE name='alerts'"
        ).fetchone()[0]

        for col in ("severity", "channel_group", "status", "alert_rule"):
            pattern = rf"CHECK\(\s*{col}\s+IN\s*\([^)]*\)\s*\)"
            models_match = re.search(pattern, models_sql)
            db_match = re.search(pattern, db_sql)
            self.assertIsNotNone(models_match, f"CHECK({col}) not found in models.py SQL_CREATE_ALERTS")
            self.assertIsNotNone(db_match, f"CHECK({col}) not found in live DB alerts.sql")
            mns = re.sub(r"\s+", " ", models_match.group(0)).strip()
            dns = re.sub(r"\s+", " ", db_match.group(0)).strip()
            self.assertEqual(
                mns, dns,
                f"Byte-identity drift on CHECK({col}):\n  models={mns!r}\n  db={dns!r}"
            )

    # -------------------------------------------------------------------------
    # Test 11: second apply of migration is guarded (idempotency in live context)
    # -------------------------------------------------------------------------
    def test_second_apply_is_guarded_in_live_db(self):
        """Second attempt to INSERT into vna_schema_migrations raises IntegrityError.

        Proves that the live DB's ledger UNIQUE constraint blocks double-apply
        just as the TDD tempfile tests showed.
        """
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO vna_schema_migrations(migration_id, applied_at) "
                "VALUES ('001_expand_channel_groups', datetime('now'))"
            )
            self.conn.commit()
        self.conn.rollback()


def main() -> None:
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestMigration001Apply)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Post-test sanity: verify no synthetic rows remain in live DB
    # (WR-04: parameter binding, not f-string).
    remaining = 0
    try:
        conn = sqlite3.connect(str(DB_PATH))
        remaining = conn.execute(
            "SELECT COUNT(*) FROM alerts WHERE data_source = ?",
            (TEST_DATA_SOURCE,),
        ).fetchone()[0]
        conn.close()
    except Exception:
        pass
    if remaining > 0:
        print(f"\nWARNING: {remaining} synthetic test rows remain in live DB!", file=sys.stderr)
        sys.exit(1)

    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Phase 08 SCHEMA-02: models.py <-> migration 001 bidirectional sync detector.

Fails when backend/db/models.py CHECK strings drift from
scripts/migrations/001_expand_channel_groups.sql -- prevents recurrence of
the 2-month silent-failure class where DB schema and ORM disagreed.

Designed to run in CI (future HARD-03) as a schema gate.

Run:  .venv/bin/python scripts/test_models_sync.py
Exit: 0 = pass, 1 = drift detected.
"""
import os
import re
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS_PATH = REPO_ROOT / "backend" / "db" / "models.py"
MIGRATION_001 = REPO_ROOT / "scripts" / "migrations" / "001_expand_channel_groups.sql"
MIGRATION_002 = REPO_ROOT / "scripts" / "migrations" / "002_add_alert_deprecation.sql"
MIGRATION_002_ROLLBACK = REPO_ROOT / "scripts" / "migrations" / "002_rollback.sql"
MIGRATION_003 = REPO_ROOT / "scripts" / "migrations" / "003_add_alerts_written_count.sql"
MIGRATION_003_ROLLBACK = REPO_ROOT / "scripts" / "migrations" / "003_rollback.sql"
MIGRATION_004 = REPO_ROOT / "scripts" / "migrations" / "004_canonicalize_alerts_created_at.sql"
MIGRATION_004_ROLLBACK = REPO_ROOT / "scripts" / "migrations" / "004_rollback.sql"
# NOTE: No Migration 005 in chain — slot was reserved during planning then never populated.
# The on-disk chain jumps from 004 to 006. Do NOT "fix" this gap.
MIGRATION_006 = REPO_ROOT / "scripts" / "migrations" / "006_backfill_split_marking.sql"
MIGRATION_006_ROLLBACK = REPO_ROOT / "scripts" / "migrations" / "006_rollback.sql"

# Ensure REPO_ROOT is on sys.path so `import backend` works when this script is
# invoked directly (e.g. `.venv/bin/python scripts/test_models_sync.py`).
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _extract_check(sql: str, col: str) -> str:
    """Extract the CHECK(<col> IN (...)) clause for the given column."""
    # Handles nested parens: CHECK(col IN ('a', 'b', ...))
    pattern = rf"CHECK\(\s*{col}\s+IN\s*\([^)]*\)\s*\)"
    m = re.search(pattern, sql)
    if not m:
        raise AssertionError(f"No CHECK({col} IN ...) clause in provided SQL")
    return _normalize_ws(m.group(0))


def _extract_create_block(models_src: str, const_name: str) -> str:
    pattern = rf'{re.escape(const_name)}\s*=\s*"""(.*?)"""'
    m = re.search(pattern, models_src, re.DOTALL)
    if not m:
        raise AssertionError(f"{const_name} not found in models.py")
    return m.group(1)


class TestModelsSync(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.models_src = MODELS_PATH.read_text(encoding="utf-8")
        cls.migration_src = MIGRATION_001.read_text(encoding="utf-8")

    def test_migration_001_exists(self):
        """Sanity: migration 001 file must be present (prerequisite for other tests)."""
        self.assertTrue(MIGRATION_001.exists(), f"Missing: {MIGRATION_001}")

    def test_channel_group_check_string_byte_identical(self):
        """alerts.channel_group CHECK in models.py must match migration 001 byte-for-byte."""
        alerts_block_models = _extract_create_block(self.models_src, "SQL_CREATE_ALERTS")
        models_check = _extract_check(alerts_block_models, "channel_group")
        # Migration 001 has TWO channel_group CHECKs (alerts + pending_notifications).
        # Both must equal the models.py alerts.channel_group CHECK.
        all_checks = re.findall(r"CHECK\(\s*channel_group\s+IN\s*\([^)]*\)\s*\)", self.migration_src)
        self.assertGreaterEqual(
            len(all_checks), 2,
            "migration 001 must contain at least 2 channel_group CHECKs (alerts + pending_notifications)"
        )
        for check in all_checks:
            self.assertEqual(
                _normalize_ws(check), models_check,
                f"Drift: {check!r} != {models_check!r}"
            )

    def test_alert_rule_check_string_byte_identical(self):
        """alerts.alert_rule CHECK in models.py must match migration 001 byte-for-byte."""
        alerts_block_models = _extract_create_block(self.models_src, "SQL_CREATE_ALERTS")
        models_check = _extract_check(alerts_block_models, "alert_rule")
        migration_check = _extract_check(self.migration_src, "alert_rule")
        self.assertEqual(migration_check, models_check)

    def test_pending_notifications_severity_check_byte_identical(self):
        """pending_notifications.severity CHECK in models.py must match migration 001 byte-for-byte."""
        pn_block_models = _extract_create_block(self.models_src, "SQL_CREATE_PENDING_NOTIFICATIONS")
        models_check = _extract_check(pn_block_models, "severity")
        # Find the severity CHECK in migration 001 inside the pending_notifications block
        pn_blocks = re.findall(
            r"CREATE TABLE pending_notifications\s*\([^;]*?\);",
            self.migration_src, re.DOTALL
        )
        self.assertTrue(pn_blocks, "migration 001 must contain CREATE TABLE pending_notifications")
        migration_check = _extract_check(pn_blocks[0], "severity")
        self.assertEqual(migration_check, models_check)

    def test_pending_notifications_channel_group_check_byte_identical(self):
        """pending_notifications.channel_group CHECK in models.py must match migration 001 byte-for-byte."""
        pn_block_models = _extract_create_block(self.models_src, "SQL_CREATE_PENDING_NOTIFICATIONS")
        models_check = _extract_check(pn_block_models, "channel_group")
        pn_blocks = re.findall(
            r"CREATE TABLE pending_notifications\s*\([^;]*?\);",
            self.migration_src, re.DOTALL
        )
        self.assertTrue(pn_blocks, "migration 001 must contain CREATE TABLE pending_notifications")
        migration_check = _extract_check(pn_blocks[0], "channel_group")
        self.assertEqual(migration_check, models_check)

    def test_channel_group_enum_matches_check_tuple(self):
        """ChannelGroup enum values must match CHANNEL_GROUP_CHECK_VALUES tuple exactly."""
        from backend.db.models import ChannelGroup, CHANNEL_GROUP_CHECK_VALUES
        self.assertEqual(tuple(m.value for m in ChannelGroup), CHANNEL_GROUP_CHECK_VALUES)

    def test_alert_rule_enum_matches_check_tuple(self):
        """AlertRule enum values must match ALERT_RULE_CHECK_VALUES tuple exactly."""
        from backend.db.models import AlertRule, ALERT_RULE_CHECK_VALUES
        self.assertEqual(tuple(m.value for m in AlertRule), ALERT_RULE_CHECK_VALUES)

    def test_a4_absent_everywhere(self):
        """A4 must be absent from enum, tuple, SQL_CREATE_ALERTS, and migration 001."""
        from backend.db.models import AlertRule, ALERT_RULE_CHECK_VALUES, SQL_CREATE_ALERTS
        # 1. Not in AlertRule enum
        self.assertNotIn("A4", [m.value for m in AlertRule])
        # 2. Not in ALERT_RULE_CHECK_VALUES tuple
        self.assertNotIn("A4", ALERT_RULE_CHECK_VALUES)
        # 3. Not in SQL_CREATE_ALERTS string
        self.assertNotIn("'A4'", SQL_CREATE_ALERTS)
        # 4. Not in migration 001 file content
        self.assertNotIn("'A4'", self.migration_src)

    def test_check_values_count_8(self):
        """Both CHANNEL_GROUP_CHECK_VALUES and ALERT_RULE_CHECK_VALUES must have exactly 8 elements."""
        from backend.db.models import CHANNEL_GROUP_CHECK_VALUES, ALERT_RULE_CHECK_VALUES
        self.assertEqual(len(CHANNEL_GROUP_CHECK_VALUES), 8)
        self.assertEqual(len(ALERT_RULE_CHECK_VALUES), 8)

    def test_init_db_on_stale_fixture_produces_correct_check(self):
        """Integration: stale DB + init_db() must reach Phase 08 alerts schema."""
        fd, path = tempfile.mkstemp(suffix=".db", prefix="models_sync_")
        os.close(fd)
        try:
            # Pre-seed STALE alerts table (2-value channel_group, 4-value alert_rule)
            c = sqlite3.connect(path)
            c.executescript("""
                CREATE TABLE alerts (
                    alert_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    severity TEXT NOT NULL CHECK(severity IN ('P0', 'P1', 'P2')),
                    channel_group TEXT NOT NULL CHECK(channel_group IN ('GOOGLE', 'OPEN_BIDDING')),
                    status TEXT NOT NULL DEFAULT 'OPEN' CHECK(status IN ('OPEN', 'ACK', 'RESOLVED', 'SNOOZED')),
                    alert_rule TEXT NOT NULL CHECK(alert_rule IN ('A0', 'A1', 'A2', 'A3')),
                    revenue_current REAL NOT NULL, revenue_baseline REAL NOT NULL,
                    revenue_delta_pct REAL NOT NULL,
                    triage_label TEXT NOT NULL, contributors_json TEXT DEFAULT '[]',
                    geo_breakdown_json TEXT DEFAULT '[]', environment_split_json TEXT DEFAULT '{}',
                    insights_json TEXT DEFAULT '{}', execution_time_sec REAL DEFAULT 0.0,
                    data_source TEXT DEFAULT 'athena', config_version TEXT DEFAULT '1.0.0',
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
            """)
            c.close()
            # Reset module-level DB path state before calling init_db with custom path
            import backend.db.database as db_mod
            db_mod._DB_PATH = None
            from backend.db.database import init_db
            init_db(path)
            c = sqlite3.connect(path)
            alerts_sql = c.execute("SELECT sql FROM sqlite_master WHERE name='alerts'").fetchone()[0]
            self.assertIn("'GOOGLE_ADEX'", alerts_sql, "8-value channel_group CHECK missing after migration")
            self.assertIn("'A8'", alerts_sql, "A8 missing from alert_rule CHECK after migration")
            self.assertNotIn("'A4'", alerts_sql, "A4 must not appear in alert_rule CHECK")
            c.close()
        finally:
            if os.path.exists(path):
                os.unlink(path)


class TestModels002Sync(unittest.TestCase):
    """Phase 09 SCHEMA-02 extension: models.py <-> migration 002 drift guard.

    Added 2026-04-23 for Phase 09 plan 01 (MIGRATE-01). Asserts that the
    `deprecated` and `deprecation_reason` columns in SQL_CREATE_ALERTS stay
    byte-identical to scripts/migrations/002_add_alert_deprecation.sql. Part
    of the HARD-03 drift-detector suite — must stay green in CI (Phase 18).
    """

    @classmethod
    def setUpClass(cls):
        cls.migration_002_src = MIGRATION_002.read_text(encoding="utf-8")
        cls.migration_002_rollback_src = (
            MIGRATION_002_ROLLBACK.read_text(encoding="utf-8")
            if MIGRATION_002_ROLLBACK.exists() else ""
        )
        cls.models_src = MODELS_PATH.read_text(encoding="utf-8")

    # Method name prefix (a01, a02, ...) controls unittest's alphabetical
    # execution order so the file-existence prerequisite runs first.
    def test_a01_migration_002_exists(self):
        """Prerequisite: migration 002 SQL file must be present."""
        self.assertTrue(MIGRATION_002.exists(), f"Missing: {MIGRATION_002}")

    # --- Test A: byte-identity of CHECK(deprecated IN (0, 1)) ---
    def test_a02_deprecated_check_clause_byte_identical(self):
        """Drift gate: CHECK(deprecated IN (0,1)) must be byte-identical between
        models.py SQL_CREATE_ALERTS and migrations/002_add_alert_deprecation.sql.
        """
        check_in_migration = _extract_check(self.migration_002_src, "deprecated")
        alerts_block = _extract_create_block(self.models_src, "SQL_CREATE_ALERTS")
        check_in_models = _extract_check(alerts_block, "deprecated")
        self.assertEqual(
            _normalize_ws(check_in_migration),
            _normalize_ws(check_in_models),
            f"CHECK(deprecated) drift: migration={check_in_migration!r} models={check_in_models!r}",
        )

    # --- Test B: substring presence of deprecated col declaration in models.py ---
    def test_a03_deprecated_column_present_in_models(self):
        """Assert `deprecated INTEGER NOT NULL DEFAULT 0` substring in SQL_CREATE_ALERTS."""
        alerts_block = _extract_create_block(self.models_src, "SQL_CREATE_ALERTS")
        self.assertIn(
            "deprecated INTEGER NOT NULL DEFAULT 0",
            alerts_block,
            "deprecated column declaration missing from SQL_CREATE_ALERTS",
        )

    # --- Test C: substring presence of deprecation_reason col declaration in models.py ---
    def test_a04_deprecation_reason_column_present_in_models(self):
        """Assert `deprecation_reason TEXT` substring in SQL_CREATE_ALERTS."""
        alerts_block = _extract_create_block(self.models_src, "SQL_CREATE_ALERTS")
        self.assertIn(
            "deprecation_reason TEXT",
            alerts_block,
            "deprecation_reason column declaration missing from SQL_CREATE_ALERTS",
        )

    # --- Test E: ledger INSERT without OR REPLACE ---
    def test_a05_migration_002_has_ledger_insert_without_or_replace(self):
        """Assert migration 002 has the exact ledger INSERT statement (no OR REPLACE).

        The OR-REPLACE check is scoped to executable SQL (comment lines stripped)
        — header comments legitimately reference 'OR REPLACE' in prose explaining
        why it's absent. What matters is the INSERT statement itself.
        """
        expected_insert = (
            "INSERT INTO vna_schema_migrations(migration_id, applied_at)\n"
            "    VALUES ('002_add_alert_deprecation', datetime('now'));"
        )
        self.assertIn(expected_insert, self.migration_002_src,
                      "Expected ledger INSERT not found verbatim in migration 002")
        # Strip SQL line comments (-- ...) then assert OR REPLACE absent from executable body.
        executable_lines = [
            ln for ln in self.migration_002_src.splitlines()
            if not ln.lstrip().startswith("--")
        ]
        executable_body = "\n".join(executable_lines)
        self.assertNotIn("OR REPLACE", executable_body,
                         "Migration 002 executable SQL must NOT use OR REPLACE "
                         "(UNIQUE constraint is the idempotency guard)")

    # --- Test F: PRAGMA foreign_keys=OFF BEFORE BEGIN TRANSACTION ---
    def test_a06_migration_002_uses_pragma_foreign_keys_off_before_begin(self):
        """Phase 08 incident learnt: PRAGMA foreign_keys=OFF must precede BEGIN TRANSACTION.
        Inside a transaction, PRAGMA foreign_keys is a silent no-op per SQLite docs.
        """
        src = self.migration_002_src
        # Find line number of first PRAGMA foreign_keys=OFF
        lines = src.splitlines()
        pragma_idx = next(
            (i for i, ln in enumerate(lines) if ln.strip().startswith("PRAGMA foreign_keys=OFF")),
            None,
        )
        begin_idx = next(
            (i for i, ln in enumerate(lines) if ln.strip().startswith("BEGIN TRANSACTION")),
            None,
        )
        self.assertIsNotNone(pragma_idx, "PRAGMA foreign_keys=OFF not found")
        self.assertIsNotNone(begin_idx, "BEGIN TRANSACTION not found")
        self.assertLess(
            pragma_idx, begin_idx,
            f"PRAGMA foreign_keys=OFF (line {pragma_idx + 1}) must precede "
            f"BEGIN TRANSACTION (line {begin_idx + 1})",
        )

    # --- Test G: rollback SQL drops both columns + index + ledger row ---
    def test_a07_rollback_sql_drops_both_columns(self):
        """002_rollback.sql must drop both columns + the idx + delete ledger row."""
        self.assertTrue(
            MIGRATION_002_ROLLBACK.exists(),
            f"Missing: {MIGRATION_002_ROLLBACK}",
        )
        src = self.migration_002_rollback_src
        self.assertIn("ALTER TABLE alerts DROP COLUMN deprecated", src,
                      "rollback must drop deprecated column")
        self.assertIn("ALTER TABLE alerts DROP COLUMN deprecation_reason", src,
                      "rollback must drop deprecation_reason column")
        self.assertIn(
            "DELETE FROM vna_schema_migrations WHERE migration_id = '002_add_alert_deprecation'",
            src,
            "rollback must remove the ledger row for 002",
        )


class TestModels003Sync(unittest.TestCase):
    """Phase 10 MONITOR-03: models.py <-> migration 003 drift guard.

    Added 2026-04-23 for Phase 10 plan 01. Asserts that
    alerts_written_count column in SQL_CREATE_PIPELINE_RUNS stays
    byte-identical to scripts/migrations/003_add_alerts_written_count.sql.
    Part of HARD-03 drift-detector suite.
    """

    @classmethod
    def setUpClass(cls):
        cls.migration_003_src = MIGRATION_003.read_text(encoding="utf-8")
        cls.migration_003_rollback_src = (
            MIGRATION_003_ROLLBACK.read_text(encoding="utf-8")
            if MIGRATION_003_ROLLBACK.exists() else ""
        )
        cls.models_src = MODELS_PATH.read_text(encoding="utf-8")

    def test_a01_migration_003_exists(self):
        self.assertTrue(MIGRATION_003.exists(), f"Missing: {MIGRATION_003}")

    def test_a02_alerts_written_count_check_clause_byte_identical(self):
        """CHECK(alerts_written_count >= 0) must be byte-identical between migration 003 and models.py SQL_CREATE_PIPELINE_RUNS."""
        # Custom extractor for >= CHECK (not IN (...) CHECK).
        pattern = r"CHECK\(\s*alerts_written_count\s*>=\s*0\s*\)"
        m_mig = re.search(pattern, self.migration_003_src)
        self.assertIsNotNone(m_mig, "CHECK(alerts_written_count >= 0) missing from migration 003")
        pipeline_block = _extract_create_block(self.models_src, "SQL_CREATE_PIPELINE_RUNS")
        m_mod = re.search(pattern, pipeline_block)
        self.assertIsNotNone(m_mod, "CHECK(alerts_written_count >= 0) missing from models.py SQL_CREATE_PIPELINE_RUNS")
        self.assertEqual(_normalize_ws(m_mig.group(0)), _normalize_ws(m_mod.group(0)))

    def test_a03_alerts_written_count_column_present_in_models(self):
        pipeline_block = _extract_create_block(self.models_src, "SQL_CREATE_PIPELINE_RUNS")
        self.assertIn(
            "alerts_written_count INTEGER NOT NULL DEFAULT 0",
            pipeline_block,
            "alerts_written_count column declaration missing from SQL_CREATE_PIPELINE_RUNS",
        )

    def test_a04_migration_003_has_ledger_insert_without_or_replace(self):
        expected_insert = (
            "INSERT INTO vna_schema_migrations(migration_id, applied_at)\n"
            "    VALUES ('003_add_alerts_written_count', datetime('now'));"
        )
        self.assertIn(expected_insert, self.migration_003_src)
        executable_lines = [
            ln for ln in self.migration_003_src.splitlines()
            if not ln.lstrip().startswith("--")
        ]
        executable_body = "\n".join(executable_lines)
        self.assertNotIn("OR REPLACE", executable_body)

    def test_a05_migration_003_uses_pragma_foreign_keys_off_before_begin(self):
        src = self.migration_003_src
        lines = src.splitlines()
        pragma_idx = next(
            (i for i, ln in enumerate(lines) if ln.strip().startswith("PRAGMA foreign_keys=OFF")),
            None,
        )
        begin_idx = next(
            (i for i, ln in enumerate(lines) if ln.strip().startswith("BEGIN TRANSACTION")),
            None,
        )
        self.assertIsNotNone(pragma_idx)
        self.assertIsNotNone(begin_idx)
        self.assertLess(pragma_idx, begin_idx)

    def test_a06_rollback_sql_drops_column(self):
        self.assertTrue(MIGRATION_003_ROLLBACK.exists(), f"Missing: {MIGRATION_003_ROLLBACK}")
        src = self.migration_003_rollback_src
        self.assertIn("ALTER TABLE pipeline_runs DROP COLUMN alerts_written_count", src)
        self.assertIn(
            "DELETE FROM vna_schema_migrations WHERE migration_id = '003_add_alerts_written_count'",
            src,
        )


class TestCreatedAtFormatInvariant(unittest.TestCase):
    """HARD-03 extension (Phase 10.1 MONITOR-04 + Phase 10.2 MONITOR-11): drift gate
    over the canonical created_at format contract (D-10.1-01). Fails if any commit
    reintroduces aware '+00:00' or naive T-separator writes/reads in the scoped
    callsites.

    Scope (per D-10.1-03 + D-10.2-01):
      * backend/agents/notifier.py _save_to_pending_notifications + _save_to_db (writes)
      * backend/agents/notifier.py send_daily_digest (cutoff + DELETE reads — Phase 10.2)
      * backend/db/operations.py create_alert + record_pipeline_run (writes)
    Out of scope (not in current migration envelope):
      * backend/db/operations.py create_event, create_recheck (Phase 10.3+ candidates)
      * backend/db/operations.py update_alert_status (WR-04, Phase 10.3+)
    """

    NOTIFIER_PY = REPO_ROOT / "backend" / "agents" / "notifier.py"
    OPERATIONS_PY = REPO_ROOT / "backend" / "db" / "operations.py"
    APPLY_MIGRATION_004 = REPO_ROOT / "scripts" / "apply_migration_004.py"
    TEST_MIGRATION_004 = REPO_ROOT / "scripts" / "test_migration_004_apply.py"
    TEST_OPS_IDEMPOT = REPO_ROOT / "scripts" / "test_operations_idempotency.py"
    CANONICAL_REGEX_LITERAL = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{6}$"

    def _extract_fn(self, src: str, fn_name: str) -> str:
        """Return the body text of the named function (everything after the def line
        up to the next def/class/EOF at the same or lower indentation)."""
        m = re.search(
            rf"def {re.escape(fn_name)}\([^)]*\)[^:]*:\n(.*?)(?=\ndef |\nclass |\Z)",
            src, re.DOTALL,
        )
        self.assertIsNotNone(m, f"Could not extract function body for {fn_name}")
        return m.group(1)

    def test_a01_notifier_uses_canonical_helper(self):
        """notifier.py must define _canonical_utc_now and use it in _save_to_pending_notifications
        and _save_to_db (both UPDATE and INSERT paths — no aware isoformat regression)."""
        src = self.NOTIFIER_PY.read_text(encoding="utf-8")
        self.assertIn("def _canonical_utc_now", src,
                      "notifier.py must define _canonical_utc_now helper")
        # Check _save_to_pending_notifications body does NOT use aware isoformat
        body_pending = self._extract_fn(src, "_save_to_pending_notifications")
        self.assertNotIn("datetime.now(timezone.utc).isoformat()", body_pending,
                         "aware isoformat regression in _save_to_pending_notifications")
        self.assertIn("_canonical_utc_now", body_pending,
                      "_save_to_pending_notifications must call _canonical_utc_now")
        # Check _save_to_db body
        body_save = self._extract_fn(src, "_save_to_db")
        self.assertNotIn("datetime.now(timezone.utc).isoformat()", body_save,
                         "aware isoformat regression in _save_to_db")
        # _save_to_db must use the helper in both UPDATE and INSERT paths
        self.assertGreaterEqual(body_save.count("_canonical_utc_now"), 2,
                                "_save_to_db must call _canonical_utc_now on both UPDATE and INSERT paths")

    def test_a02_create_alert_uses_canonical_format(self):
        """create_alert in operations.py must canonicalize created_at + updated_at
        (>= 2 canonical isoformat calls in function body)."""
        src = self.OPERATIONS_PY.read_text(encoding="utf-8")
        body = self._extract_fn(src, "create_alert")
        canonical_count = body.count(".isoformat(sep=' ', timespec='microseconds')")
        self.assertGreaterEqual(canonical_count, 2,
            f"create_alert must canonicalize created_at + updated_at; "
            f"found {canonical_count} canonical calls")

    def test_a03_record_pipeline_run_uses_canonical_format(self):
        """record_pipeline_run in operations.py must canonicalize created_at."""
        src = self.OPERATIONS_PY.read_text(encoding="utf-8")
        body = self._extract_fn(src, "record_pipeline_run")
        self.assertIn(".isoformat(sep=' ', timespec='microseconds')", body,
                      "record_pipeline_run must canonicalize created_at")
        # Must not fall back to bare .isoformat()
        self.assertNotIn("datetime.utcnow().isoformat(),", body,
                         "record_pipeline_run still uses bare .isoformat()")

    def test_a04_canonical_regex_byte_identical_across_files(self):
        """The canonical regex literal must be byte-identical in all 3 files
        that assert post-migration row shape, to prevent any file from drifting
        a pattern that passes locally but misses elsewhere."""
        files = [
            self.APPLY_MIGRATION_004,
            self.TEST_MIGRATION_004,
            self.TEST_OPS_IDEMPOT,
        ]
        for p in files:
            src = p.read_text(encoding="utf-8")
            self.assertIn(self.CANONICAL_REGEX_LITERAL, src,
                          f"canonical regex literal missing or drifted in {p.name}")

    def test_a05_send_daily_digest_uses_canonical_cutoff(self):
        """send_daily_digest must use _canonical_utc_cutoff(24) (or equivalent
        space-sep helper) for the 24h cutoff variable. NEVER aware-T isoformat().
        Closes CR-01 from .planning/phases/10.1-.../10.1-REVIEW.md."""
        src = self.NOTIFIER_PY.read_text(encoding="utf-8")

        # Helper must be defined alongside _canonical_utc_now
        self.assertIn("def _canonical_utc_cutoff", src,
                      "notifier.py must define _canonical_utc_cutoff helper for MONITOR-11")

        # send_daily_digest body must call the helper and must not contain the
        # aware-T regression pattern that produced CR-01
        body = self._extract_fn(src, "send_daily_digest")
        self.assertIn("_canonical_utc_cutoff", body,
                      "send_daily_digest must build cutoff via _canonical_utc_cutoff "
                      "(MONITOR-11 / CR-01 fix)")
        self.assertNotIn("datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()", body,
                         "CR-01 regression: aware-T cutoff reintroduced in send_daily_digest")
        self.assertNotIn("datetime.now(timezone.utc).isoformat()", body,
                         "CR-01 regression: any aware-T isoformat in send_daily_digest body")


class TestMigration006Sync(unittest.TestCase):
    """Phase 18 HARD-02: Migration 006 (Phase 17.4 backfill split marking) coverage.

    Verifies the 006_backfill_split_marking.sql file is present, is data-only
    (must NOT alter any CHECK constraints), and contains the correct UPDATE
    pattern that marks non-GOOGLE_ADEX backfill alerts as deprecated.

    Part of the HARD-02 drift-detector suite — must stay GREEN in CI.
    """

    def test_migration_006_file_exists(self):
        """Both 006 forward and rollback SQL files must be present on disk."""
        self.assertTrue(MIGRATION_006.exists(), f"Missing: {MIGRATION_006}")
        self.assertTrue(MIGRATION_006_ROLLBACK.exists(), f"Missing: {MIGRATION_006_ROLLBACK}")

    def test_migration_006_does_not_alter_channel_group_check(self):
        """Migration 006 is data-only — it must NOT introduce or modify any
        CHECK(channel_group IN ...) or CHECK(alert_rule IN ...) clause.
        Any such clause would indicate an unintended schema mutation."""
        sql = MIGRATION_006.read_text(encoding="utf-8")
        for col in ("channel_group", "alert_rule"):
            pattern = rf"CHECK\s*\(\s*{col}\s+IN"
            self.assertIsNone(
                re.search(pattern, sql, re.IGNORECASE),
                f"Migration 006 unexpectedly contains CHECK({col} IN ...) — "
                f"006 is data-only and must not alter schema CHECKs",
            )

    def test_migration_006_marks_backfill_alerts_deprecated(self):
        """Migration 006 must contain an UPDATE on alerts that references
        the deprecated column and the 'backfill' data_source literal."""
        sql = MIGRATION_006.read_text(encoding="utf-8")
        self.assertIn(
            "UPDATE alerts",
            sql,
            "Migration 006 must contain 'UPDATE alerts'",
        )
        self.assertIn(
            "deprecated",
            sql.lower(),
            "Migration 006 must reference 'deprecated' column",
        )
        self.assertIn(
            "backfill",
            sql.lower(),
            "Migration 006 must reference 'backfill' literal (data_source filter)",
        )


# ---------------------------------------------------------------------------
# Baseline stale schema (pre-Migration-001) for :memory: chain composition.
# Migration 001 requires `alerts` and `pending_notifications` tables to exist
# before it can rename them; this is the minimal stale schema they start from.
# ---------------------------------------------------------------------------
_STALE_ALERTS_DDL = """
CREATE TABLE IF NOT EXISTS alerts (
    alert_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('P0', 'P1', 'P2')),
    channel_group TEXT NOT NULL CHECK(channel_group IN ('GOOGLE', 'OPEN_BIDDING')),
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK(status IN ('OPEN', 'ACK', 'RESOLVED', 'SNOOZED')),
    alert_rule TEXT NOT NULL CHECK(alert_rule IN ('A0', 'A1', 'A2', 'A3')),
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
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pending_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    channel_group TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL DEFAULT 'RUNNING',
    error_message TEXT
);
-- NOTE: alerts_written_count is NOT in this baseline DDL.
-- Migration 003 adds it via ALTER TABLE; including it here would cause
-- "duplicate column name" when executescript applies 003.
"""


class TestComposeChainAgainstModels(unittest.TestCase):
    """Phase 18 HARD-02 composite check: apply 001 → 002 → 003 → 004 → 006
    sequentially against sqlite3 :memory: and assert the resulting CHECK
    clauses match backend/db/models.py constants exactly.

    This is the canonical drift gate — it makes it structurally impossible to
    merge a commit where models.py and the migration chain disagree.

    NOTE: No Migration 005 in chain — slot was reserved during planning then
    never populated. The on-disk chain jumps from 004 → 006 intentionally.
    Do NOT add 005 to this tuple without also creating the corresponding SQL.
    """

    @classmethod
    def setUpClass(cls):
        cls.conn = sqlite3.connect(":memory:")
        cur = cls.conn.cursor()
        # Step 0: create the pre-001 stale base schema that Migration 001 expects.
        # Migration 001 uses ALTER TABLE ... RENAME TO, which requires the tables
        # to already exist. Without this baseline, executescript raises
        # "no such table: alerts".
        cur.executescript(_STALE_ALERTS_DDL)
        # Step 1..N: apply the migration chain in order.
        # NOTE: No Migration 005 (slot reserved, never populated — intentional gap).
        for mig in (MIGRATION_001, MIGRATION_002, MIGRATION_003, MIGRATION_004, MIGRATION_006):
            cur.executescript(mig.read_text(encoding="utf-8"))
        cls.conn.commit()

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def _table_sql(self, name: str) -> str:
        """Return the CREATE TABLE SQL from sqlite_master for the given table."""
        row = self.conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (name,)
        ).fetchone()
        self.assertIsNotNone(row, f"Table '{name}' not found in :memory: DB after chain")
        return row[0]

    def test_channel_group_check_matches_models_constants(self):
        """Every value in models.CHANNEL_GROUP_CHECK_VALUES must appear as a
        quoted literal in the alerts table channel_group CHECK clause after the
        full migration chain is applied.
        Fails if models.py adds a channel but the migration chain lags behind."""
        from backend.db import models
        schema_sql = self._table_sql("alerts")
        for ch in models.CHANNEL_GROUP_CHECK_VALUES:
            self.assertIn(
                f"'{ch}'",
                schema_sql,
                f"channel_group CHECK drift: models.py declares {ch!r} but "
                f"the migration-derived schema does not list it",
            )

    def test_alert_rule_check_matches_models_constants(self):
        """Every value in models.ALERT_RULE_CHECK_VALUES must appear as a quoted
        literal in the alerts table alert_rule CHECK clause after the full
        migration chain is applied.
        Fails if models.py adds/removes a rule code but the chain lags behind."""
        from backend.db import models
        schema_sql = self._table_sql("alerts")
        for rule in models.ALERT_RULE_CHECK_VALUES:
            self.assertIn(
                f"'{rule}'",
                schema_sql,
                f"alert_rule CHECK drift: models.py declares {rule!r} but "
                f"the migration-derived schema does not list it",
            )

    def test_deprecated_column_present_after_chain(self):
        """The 'deprecated' column must be present in alerts after migration 002."""
        self.assertIn(
            "deprecated",
            self._table_sql("alerts"),
            "deprecated column missing from alerts after migration chain",
        )

    def test_data_source_column_present_after_chain(self):
        """The 'data_source' column must be present in alerts (baseline schema)."""
        self.assertIn(
            "data_source",
            self._table_sql("alerts"),
            "data_source column missing from alerts after migration chain",
        )

    def test_no_orphan_channels_in_schema_vs_models(self):
        """Inverse direction check: every channel_group literal accepted by the
        migration-derived schema must also appear in models.CHANNEL_GROUP_CHECK_VALUES.
        Catches the case where the schema accepts a channel that models.py forgot
        to declare (orphan in the DB, invisible to Python validation)."""
        from backend.db import models
        schema_sql = self._table_sql("alerts")
        m = re.search(
            r"CHECK\(\s*channel_group\s+IN\s*\(([^)]+)\)\s*\)",
            schema_sql,
        )
        self.assertIsNotNone(
            m,
            "Could not find CHECK(channel_group IN (...)) in migration-derived alerts table",
        )
        literals = re.findall(r"'([^']+)'", m.group(1))
        self.assertTrue(literals, "No channel_group literals found in CHECK clause")
        for lit in literals:
            self.assertIn(
                lit,
                models.CHANNEL_GROUP_CHECK_VALUES,
                f"Schema accepts channel_group={lit!r} but models.CHANNEL_GROUP_CHECK_VALUES "
                f"does not include it — orphan channel in migration-derived schema",
            )


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite([
        loader.loadTestsFromTestCase(TestModelsSync),
        loader.loadTestsFromTestCase(TestModels002Sync),
        loader.loadTestsFromTestCase(TestModels003Sync),
        loader.loadTestsFromTestCase(TestCreatedAtFormatInvariant),
        loader.loadTestsFromTestCase(TestMigration006Sync),
        loader.loadTestsFromTestCase(TestComposeChainAgainstModels),
    ])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())

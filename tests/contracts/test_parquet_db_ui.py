"""HARD-01 — Cross-layer contract test: parquet -> DB -> UI consistency.

Phase 18 deliverable (REQUIREMENTS.md HARD-01, 18-CONTEXT.md D-01..D-03).

Pins consistency on one known-good alert per channel (7 cases). GOOGLE_ADEX
is the live anchor (Phase 17.4 Sample 1 byte-perfect EUR 662.67). The other 6
channels SKIP with reason 'Phase 21 v1.4 Athena activation required' -- they
become GREEN automatically when Phase 21 lands real_csv corpora.

Three-layer assertion per non-skipped channel:
  LAYER 1 (DB):   sqlite3 SELECT on data/vna_alerts.db (read-only)
  LAYER 2 (UI):   JSON snapshot at frontend/dist/api/alerts/{id}.json
  LAYER 3 (PBI):  revenue_current in PBI band [expected * (1-tol), expected * (1+tol)]

PBI reference: Marco email 2026-05-19 -- GOOGLE_ADEX Sample 1 gross EUR 662.67
               (D2CLOSE-04, scripts/test_alert_revenue_pbi_parity.py INV-1)

Run: .venv/bin/python -m pytest tests/contracts/test_parquet_db_ui.py -v
"""
from __future__ import annotations

import pytest

# 7 real channels for HARD-01 (excludes 'GOOGLE' legacy alias -- covered
# only in the CHECK constraint regression test below).
SEVEN_CHANNELS = [
    "GOOGLE_ADEX",
    "OPEN_BIDDING",
    "HEADER_BIDDING_MAGNITE",
    "HEADER_BIDDING_PUBMATIC",
    "TAM",
    "DIRECT",
    "DEAL",
]

# The legacy GOOGLE alias is still present in the models.py CHECK constraint;
# include it in the schema regression test but NOT in the channel fixture loop.
MODELS_CHECK_CHANNELS = SEVEN_CHANNELS + ["GOOGLE"]


# ---------------------------------------------------------------------------
# Test 1: Three-layer parquet -> DB -> UI consistency (parametrized x7)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("channel_group", SEVEN_CHANNELS, ids=SEVEN_CHANNELS)
def test_parquet_db_ui_consistency(
    channel_group,
    known_alert_fixture,
    db_conn,
    json_snapshot_loader,
):
    """For each channel, prove DB row + UI JSON snapshot + PBI band all agree.

    GOOGLE_ADEX: ALT-20260322-010000-P2, EUR 662.67, real_csv -- PASS (live anchor).
    Other 6 channels: SKIP (Phase 21 v1.4 Athena dependency -- no real_csv corpus yet).

    Three-layer assertion:
      LAYER 1 (DB)  -- revenue_current in PBI band, data_source == expected, not deprecated
      LAYER 2 (UI)  -- frontend/dist/api/alerts/{id}.json byte-matches DB values
      LAYER 3 (PBI) -- revenue_current in PBI +-tolerance band (independent reassertion)
    """
    fix = known_alert_fixture(channel_group)

    # SKIP: channels gated on Phase 21 v1.4 Athena activation
    if fix["skip_reason"]:
        pytest.skip(fix["skip_reason"])

    alert_id = fix["alert_id"]
    expected_rev = fix["expected_revenue"]
    expected_ds = fix["expected_data_source"]
    tol = fix["tolerance_pct"]
    lower = expected_rev * (1 - tol)
    upper = expected_rev * (1 + tol)

    # ------------------------------------------------------------------
    # LAYER 1 — DB (read-only sqlite3 -- see conftest db_conn fixture)
    # ------------------------------------------------------------------
    row = db_conn.execute(
        "SELECT alert_id, channel_group, revenue_current, data_source, deprecated "
        "FROM alerts WHERE alert_id = ?",
        (alert_id,),
    ).fetchone()

    assert row is not None, (
        f"DB layer: alert {alert_id!r} not found in data/vna_alerts.db. "
        f"Ensure Phase 17.4 Plan 04 rewrite has been applied."
    )
    assert row["channel_group"] == channel_group, (
        f"DB layer channel mismatch for {alert_id!r}: "
        f"row={row['channel_group']!r} vs param={channel_group!r}"
    )
    assert lower <= row["revenue_current"] <= upper, (
        f"DB layer PBI band fail for {alert_id!r}: "
        f"got EUR {row['revenue_current']:.2f}, "
        f"expected band [EUR {lower:.2f}, EUR {upper:.2f}] "
        f"(data_source={row['data_source']!r})"
    )
    assert row["data_source"] == expected_ds, (
        f"DB layer data_source mismatch for {alert_id!r}: "
        f"got {row['data_source']!r}, expected {expected_ds!r}"
    )

    # ------------------------------------------------------------------
    # LAYER 2 — UI (frontend/dist/api/alerts/{id}.json -- Vercel snapshot)
    # The json_snapshot_loader unwraps the {"alert": {...}} top-level wrapper
    # produced by scripts/export_api_json.sh.
    # ------------------------------------------------------------------
    ui = json_snapshot_loader(alert_id)
    if ui is None:
        pytest.skip(
            f"UI snapshot for {alert_id!r} not found in "
            f"frontend/dist/api/alerts/ -- run scripts/export_api_json.sh "
            f"with a running backend to regenerate."
        )

    assert ui.get("revenue_current") == row["revenue_current"], (
        f"UI vs DB drift on revenue_current for {alert_id!r}: "
        f"UI={ui.get('revenue_current')!r} DB={row['revenue_current']!r}"
    )
    assert ui.get("data_source") == row["data_source"], (
        f"UI vs DB drift on data_source for {alert_id!r}: "
        f"UI={ui.get('data_source')!r} DB={row['data_source']!r}"
    )

    # ------------------------------------------------------------------
    # LAYER 3 — PBI band reassertion (independent of DB; this test is the
    # truth source for the tolerance contract per channel)
    # ------------------------------------------------------------------
    ui_rev = ui.get("revenue_current")
    assert ui_rev is not None, (
        f"UI snapshot for {alert_id!r} missing revenue_current field"
    )
    assert lower <= ui_rev <= upper, (
        f"UI layer PBI band fail for {alert_id!r}: "
        f"got EUR {ui_rev:.2f}, expected band [EUR {lower:.2f}, EUR {upper:.2f}]"
    )


# ---------------------------------------------------------------------------
# Test 2: Fixture sanity -- known-good alert must NOT be deprecated (x7)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("channel_group", SEVEN_CHANNELS, ids=SEVEN_CHANNELS)
def test_known_good_alert_id_is_not_deprecated(
    channel_group,
    known_alert_fixture,
    db_conn,
):
    """Fixture sanity: a non-skipped channel's anchor alert must have deprecated=0.

    If the anchor alert is deprecated the fixture is useless as a consistency
    contract -- deprecated alerts are excluded from the active alert surface.
    """
    fix = known_alert_fixture(channel_group)
    if fix["skip_reason"]:
        pytest.skip(fix["skip_reason"])

    row = db_conn.execute(
        "SELECT deprecated, deprecation_reason FROM alerts WHERE alert_id = ?",
        (fix["alert_id"],),
    ).fetchone()

    assert row is not None, (
        f"Fixture alert {fix['alert_id']!r} missing from data/vna_alerts.db -- "
        f"update 18-01-FIXTURES.md if the anchor alert was removed."
    )
    assert row["deprecated"] == 0, (
        f"Fixture alert {fix['alert_id']!r} is deprecated "
        f"(reason: {row['deprecation_reason']!r}) -- "
        f"update 18-01-FIXTURES.md to use a non-deprecated anchor."
    )


# ---------------------------------------------------------------------------
# Test 3: CHECK constraint regression -- all 7 channels + GOOGLE alias (x1)
# ---------------------------------------------------------------------------


def test_models_check_constraint_lists_all_7_channels(db_conn):
    """Regression: DB schema CHECK clause must accept all 7 channels + legacy GOOGLE alias.

    Guards against silent CHECK regression -- the original v1.2 silent-failure class
    (undetected for 2 months: DB accepted rows that should have been rejected
    because the CHECK constraint was stale relative to models.py).

    Source of truth: backend/db/models.py lines 207-210 CHECK constraint.
    Expected channels: GOOGLE_ADEX, OPEN_BIDDING, HEADER_BIDDING_MAGNITE,
    HEADER_BIDDING_PUBMATIC, TAM, DIRECT, DEAL, GOOGLE (legacy alias).
    """
    row = db_conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='alerts'"
    ).fetchone()
    assert row is not None, (
        "alerts table missing from data/vna_alerts.db -- "
        "run backend ETL / migration chain to create the schema."
    )
    sql = row["sql"]

    for ch in MODELS_CHECK_CHANNELS:
        assert f"'{ch}'" in sql, (
            f"CHECK constraint regression: channel {ch!r} missing from alerts DDL. "
            f"This means backend/db/models.py CHECK constraint diverged from the "
            f"migration-derived schema. Run HARD-02 schema drift gate for details."
        )

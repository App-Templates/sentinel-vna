"""Shared pytest fixtures for HARD-01 cross-layer contract tests.

Phase 18 — parquet↔DB↔UI consistency (REQUIREMENTS.md HARD-01).

UI snapshots live in frontend/dist/api/alerts/{alert_id}.json (generated
by scripts/export_api_json.sh). Each snapshot JSON wraps the alert payload
under a top-level {"alert": {...}} key — the loader unwraps transparently.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

try:
    import pyarrow.parquet as pq
    import pandas  # noqa: F401 — needed by pq.read_table(...).to_pandas()
except ImportError:
    pq = None

# Two canonical locations for UI snapshots (dist = Vercel build output;
# public = Vite source assets). The dist path is the live export target.
REPO_ROOT = Path(__file__).resolve().parents[2]
_UI_SEARCH_PATHS = [
    REPO_ROOT / "frontend" / "dist" / "api" / "alerts",
    REPO_ROOT / "frontend" / "public" / "api" / "alerts",
]


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Repository root directory (parent of tests/)."""
    return REPO_ROOT


@pytest.fixture(scope="session")
def db_conn():
    """Read-only sqlite3 connection to data/vna_alerts.db.

    Opens via URI with mode=ro to prevent any accidental mutation.
    row_factory=sqlite3.Row enables column-name access.
    """
    db_path = REPO_ROOT / "data" / "vna_alerts.db"
    if not db_path.exists():
        pytest.skip(f"DB not found at {db_path} — run backend ETL first")
    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture
def json_snapshot_loader():
    """Factory fixture: load a frontend/dist/api/alerts/{alert_id}.json snapshot.

    Returns the alert payload dict (unwrapped from the top-level {"alert": {...}}
    wrapper that export_api_json.sh produces). Returns None if the file is not
    found in any of the canonical search paths — callers should pytest.skip when
    None is returned.
    """
    def _load(alert_id: str):
        for base_dir in _UI_SEARCH_PATHS:
            p = base_dir / f"{alert_id}.json"
            if p.exists():
                raw = json.loads(p.read_text())
                # export_api_json.sh wraps the alert under {"alert": {...}}
                if isinstance(raw, dict) and "alert" in raw and len(raw) == 1:
                    return raw["alert"]
                return raw
        return None
    return _load


@pytest.fixture
def parquet_loader():
    """Factory fixture: load a parquet file from data/baseline/{name}.parquet.

    Returns a pandas DataFrame. Skips the test if pyarrow is not installed
    or if the parquet file does not exist.
    """
    def _load(name: str):
        if pq is None:
            pytest.skip("pyarrow not installed in active venv")
        p = REPO_ROOT / "data" / "baseline" / f"{name}.parquet"
        if not p.exists():
            pytest.skip(f"parquet fixture {name}.parquet not found at {p}")
        return pq.read_table(str(p)).to_pandas()
    return _load


@pytest.fixture
def known_alert_fixture(db_conn):
    """Factory fixture: return the 7-channel fixture mapping for HARD-01.

    Mapping sourced from 18-01-FIXTURES.md (single source of truth).
    GOOGLE_ADEX is the live anchor (Phase 17.4 Sample 1 byte-perfect €662.67).
    The other 6 channels carry skip_reason='Phase 21 v1.4 Athena activation
    required' — they become GREEN automatically when Phase 21 lands real_csv
    corpora.

    Returns a dict with keys:
        alert_id            str | None
        expected_revenue    float | None
        expected_data_source str
        tolerance_pct       float
        skip_reason         str | None   (None = live anchor, no skip)
    """
    # 7-channel mapping — update in lockstep with 18-01-FIXTURES.md when
    # Phase 21 lands real_csv corpora per channel.
    MAPPING = {
        "GOOGLE_ADEX": dict(
            alert_id="ALT-20260322-010000-P2",
            expected_revenue=662.67,
            expected_data_source="real_csv",
            tolerance_pct=0.01,
            skip_reason=None,
        ),
        "OPEN_BIDDING": dict(
            alert_id=None,
            expected_revenue=None,
            expected_data_source="real_csv",
            tolerance_pct=0.02,
            skip_reason="Phase 21 v1.4 Athena activation required",
        ),
        "HEADER_BIDDING_MAGNITE": dict(
            alert_id=None,
            expected_revenue=None,
            expected_data_source="real_csv",
            tolerance_pct=0.02,
            skip_reason="Phase 21 v1.4 Athena activation required",
        ),
        "HEADER_BIDDING_PUBMATIC": dict(
            alert_id=None,
            expected_revenue=None,
            expected_data_source="real_csv",
            tolerance_pct=0.02,
            skip_reason="Phase 21 v1.4 Athena activation required",
        ),
        "TAM": dict(
            alert_id=None,
            expected_revenue=None,
            expected_data_source="real_csv",
            tolerance_pct=0.02,
            skip_reason="Phase 21 v1.4 Athena activation required",
        ),
        "DIRECT": dict(
            alert_id=None,
            expected_revenue=None,
            expected_data_source="real_csv",
            tolerance_pct=0.02,
            skip_reason="Phase 21 v1.4 Athena activation required",
        ),
        "DEAL": dict(
            alert_id=None,
            expected_revenue=None,
            expected_data_source="real_csv",
            tolerance_pct=0.02,
            skip_reason="Phase 21 v1.4 Athena activation required",
        ),
    }

    def _get(channel_group: str) -> dict:
        if channel_group not in MAPPING:
            pytest.fail(f"Unknown channel_group for HARD-01: {channel_group!r}")
        return MAPPING[channel_group]

    return _get

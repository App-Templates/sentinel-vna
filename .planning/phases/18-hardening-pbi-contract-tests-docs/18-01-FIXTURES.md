# 18-01 FIXTURES — Per-channel known-good alert mapping (HARD-01)

Single source of truth for which alert anchors each channel in the parquet↔DB↔UI
contract test. Update this table in lockstep with `tests/contracts/conftest.py`
MAPPING whenever Phase 21 lands real_csv corpora per channel.

## Channel fixture map

| channel_group              | alert_id                  | expected_revenue_eur | expected_data_source | tolerance_pct | skip_reason                                              | rationale                                               |
|----------------------------|---------------------------|----------------------|----------------------|---------------|----------------------------------------------------------|---------------------------------------------------------|
| GOOGLE_ADEX                | ALT-20260322-010000-P2    | 662.67               | real_csv             | 0.01          | (none — live anchor)                                     | Phase 17.4 Sample 1 byte-perfect PBI match (D2CLOSE-04) |
| OPEN_BIDDING               | (none)                    | (n/a)                | real_csv             | 0.02          | Phase 21 v1.4 Athena activation required                 | Synthetic-era deprecated corpus only                    |
| HEADER_BIDDING_MAGNITE     | (none)                    | (n/a)                | real_csv             | 0.02          | Phase 21 v1.4 Athena activation required                 | Synthetic-era deprecated corpus only                    |
| HEADER_BIDDING_PUBMATIC    | (none)                    | (n/a)                | real_csv             | 0.02          | Phase 21 v1.4 Athena activation required                 | Synthetic-era deprecated corpus only                    |
| TAM                        | (none)                    | (n/a)                | real_csv             | 0.02          | Phase 21 v1.4 Athena activation required                 | Synthetic-era deprecated corpus only                    |
| DIRECT                     | (none)                    | (n/a)                | real_csv             | 0.02          | Phase 21 v1.4 Athena activation required                 | Synthetic-era deprecated corpus only                    |
| DEAL                       | (none)                    | (n/a)                | real_csv             | 0.02          | Phase 21 v1.4 Athena activation required                 | Synthetic-era deprecated corpus only                    |

## Rationale for GOOGLE_ADEX anchor

`ALT-20260322-010000-P2` is the Phase 17.4 canonical anchor:

- Verified 2026-05-21 via sqlite3: `revenue_current=662.67`, `data_source='real_csv'`, `deprecated=0`
- PBI source: Marco email 2026-05-19, BigQuery snapshot — Sample 1 gross EUR €662.67
- Path A (`/api/metrics/network-totals?bypass_top50=true`) delivers this value byte-perfect
- D2CLOSE-04 evidence: `scripts/test_alert_revenue_pbi_parity.py` INV-1 GREEN post Phase 17.4 Plan 04
- Tolerance ±1% consistent with `SAMPLE_1_TOLERANCE_PCT = 0.01` in `test_alert_revenue_pbi_parity.py`

## Updating this table

When Phase 21 lands Athena real_csv corpora for a non-GOOGLE_ADEX channel:

1. Identify the byte-perfect anchor alert for the channel (the alert whose
   `revenue_current` matches the PBI value ±tolerance after Athena ingestion)
2. Replace `(none)` in `alert_id` with the real alert_id
3. Replace `(n/a)` in `expected_revenue_eur` with the PBI gross EUR value
4. Clear the `skip_reason` cell (empty = no skip = live assertion)
5. Reduce `tolerance_pct` to `0.01` if the match is byte-perfect, keep `0.02` if ±2%
6. Update `tests/contracts/conftest.py` MAPPING in lockstep (same PR, same commit)
7. Run `.venv/bin/python -m pytest tests/contracts/test_parquet_db_ui.py -v` to confirm GREEN

**Order matters:** table + conftest.py MUST be updated atomically in the same commit.
An out-of-sync FIXTURES.md is a documentation lie — the conftest.py is the runtime truth.

## DB inventory reference (2026-05-21)

Verified via sqlite3 query before Phase 18 planning:

| channel_group              | active real_csv | deprecated backfill | total |
|----------------------------|-----------------|---------------------|-------|
| GOOGLE_ADEX                | 38              | 1 (CSV-EOF edge)    | 39+   |
| OPEN_BIDDING               | 0               | 93 parquet + 30 bf  | 123   |
| HEADER_BIDDING_MAGNITE     | 0               | 29                  | 29    |
| HEADER_BIDDING_PUBMATIC    | 0               | 29                  | 29    |
| TAM                        | 0               | 28                  | 28    |
| DIRECT                     | 0               | 33                  | 33    |
| DEAL                       | 0               | 26                  | 26    |

Source: 18-01-PLAN.md `<interfaces>` block (verified 2026-05-21).

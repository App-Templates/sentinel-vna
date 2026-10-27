# GitHub Actions Workflows

This directory holds CI gates for the Sentinel repo. Each file is one gate.

**First workflow landed:** 2026-05-21 (Phase 18 HARD-02). Prior to Phase 18, the repo had no CI gates; drift was caught manually.

## Current workflows

| File | Gate | Phase | Fails when |
|------|------|-------|------------|
| schema-drift.yml | HARD-02 | Phase 18 | `backend/db/models.py` CHECK constants drift from migrations 001..006 applied in `sqlite3 :memory:` |
| pbi-parity.yml | HARD-03 + HARD-04 | Phase 18 | Path A guard regression in `backend/agents/data_fetcher_real.py` OR silent-failure regression case (CSV-EOF, post-cutoff synthetic) fails. Both gates share one workflow — see the job log to distinguish HARD-03 (silent-failure regression step) vs HARD-04 (PBI parity / Path A guard step). |

## Conventions

- One workflow file per gate. Name = gate purpose, kebab-case (e.g., `schema-drift.yml`, `pbi-parity.yml`).
- Pin action versions explicitly (`@v4`, `@v5`) to avoid silent upstream drift.
- Use Python 3.11 across all jobs (matches `.venv/bin/python --version` on operator machine).
- Install via `pip install -r requirements.txt`; do not duplicate dependency lists in workflow files.
- Every gate must be runnable locally with the exact same command — no GitHub-only magic.

## Adding a new workflow

1. Write a new `.yml` file in this directory; one job per gate.
2. Add a row to the "Current workflows" table above.
3. Reference the corresponding requirement ID (HARD-XX, MONITOR-XX, etc.) in `.planning/REQUIREMENTS.md`.

## Why "schema-drift" first

v1.2 shipped with `backend/db/models.py` declaring 7 channel_group values while the live DB CHECK still accepted only 2 (legacy `GOOGLE` + `OPEN_BIDDING`). Pipeline silently rejected every new-channel alert for 2 months. The drift gate makes this regression class structurally impossible — `git push` is rejected if `models.py` and the migration chain disagree.

Canonical requirement: `.planning/ROADMAP.md` Phase 18 SC #2.

## Why "pbi-parity" second

Phase 17.4 pinned ALT-20260322-010000-P2 to byte-perfect PBI €662.67 via Path A (in-process call to `/api/metrics/network-totals?bypass_top50=true` for GOOGLE_ADEX BACKTEST only). The branch is GOOGLE_ADEX-only by design — accidentally enabling it for other channels would regress them to top-50-filtered values that no longer match PBI. INV-6 in this gate prevents that regression at the source-grep level. INV-5 is a placeholder for Phase 21 v1.4 Athena activation (Sample 2 HBM €688).

The silent-failure regression adds defense-in-depth against H6 (tz-mismatch silent synthetic fallback, Phase 17.3 root cause) by asserting a synthetic-class GOOGLE_ADEX alert post-2026-05-21 trips the canonical watchdog violator query.

CI environment note: this workflow runs without `data/vna_alerts.db` (gitignored). The structural invariants (Path A guard grep, silent-failure ephemeral-DB tests) run in CI. The DB-bound invariants (INV-1..INV-4) run on the operator machine pre-push.

Canonical requirement: `.planning/ROADMAP.md` Phase 18 SC #3 (HARD-03 + HARD-04).

---
phase: 18-hardening-pbi-contract-tests-docs
trigger: ROADMAP scope locked + Stefano direttiva 2026-05-21 "tutto perfetto 10/10" + Phase 17.4 SHIPPED unblock
status: planning
parent: v1.3 milestone (post Phase 17.4)
type: hardening
mode: operator-defined (skip discuss)
---

# Phase 18: Hardening + PBI Contract Tests + Docs — Context

**Gathered:** 2026-05-21 (operator-defined, skip discuss)
**Status:** Ready for planning
**Source:** ROADMAP §"Phase 18" locked scope + REQUIREMENTS.md HARD-01..04 + DOC-01 + Sentinel CLAUDE.md R-13 + post Phase 17.4 ship state

<domain>
## Phase Boundary

Hardening finale v1.3: regressione strutturalmente impossibile sulla silent-failure class + PBI match assertions automatizzate + lineage documentato. Chiude v1.3 milestone. Prepara apertura v1.4 (Phase 19/20/21).

Scope tecnico (4 requirement IDs + 1 DOC):
1. **HARD-01** Contract tests parquet↔DB↔UI — `tests/contracts/test_parquet_db_ui.py` cubre 1 known-good alert per channel (7 cases: GOOGLE_ADEX, OPEN_BIDDING, HEADER_BIDDING_MAGNITE, HEADER_BIDDING_PUBMATIC, TAM, DIRECT, DEAL) + 1 PBI-match assertion per known metric
2. **HARD-02** CI schema drift gate — GitHub Actions fails quando `backend/db/models.py` CHECK diverges da migration-derived expected DB schema
3. **HARD-03** (extended) Pipeline silent-failure regression test — già parziale Phase 10.1, completa cross-channel coverage
4. **HARD-04** PBI parity automation — pin Sample 1 byte-perfect €662.67 + Sample 2 expected band (gated Phase 21 v1.4 reattivazione) come regression test invariants
5. **DOC-01** `DATA_INTEGRATION.md` aggiornato — v1.2 schema + PBI↔Sentinel reproducibility matrix + gap disclosure (OM taxonomy, eCPM/RPM denominator, hourly YoY synthetic, fill rate measurable, Phase 17.4 D2 closure path, riferimento v1.4 Phase 19/20/21 per V1/V2/HBM open)

**Out of scope (gated):**
- Phase 19 V1 Channel granularity refactor — v1.4 milestone
- Phase 20 V2 Open Market distribution study — v1.4
- Phase 21 Athena HBM activation — v1.4
- Email Marco — post Phase 21 close
- 199 deprecated alert rewrite (Phase 21 v1.4 quando Athena live)

</domain>

<decisions>
## Implementation Decisions (operator-defined, locked)

### Contract tests architecture (HARD-01)

- **D-01:** `tests/contracts/test_parquet_db_ui.py` come single test file con 7 channel-specific test cases (parametrized via `@pytest.mark.parametrize`). Pattern: per ogni channel scegliere 1 alert known-good post-Phase 17.4 (GOOGLE_ADEX → ALT-20260322-010000-P2 €662.67 real_csv; altri channel → un alert post-2026-05-21 quando esistono OR mock fixture deterministico se non esistono ancora live alerts).
- **D-02:** Test verifica parquet → DB → UI consistency:
  - Parquet read: alert revenue ≈ expected PBI band ±2%
  - DB read: `revenue_current` matches parquet + `data_source` in `{'real_parquet', 'real_csv'}` (NEVER synthetic-class)
  - UI read: API JSON snapshot `/api/alerts/{id}.json` contains same `revenue_current` + `data_source` byte-identical
- **D-03:** PBI-match assertion separato per ogni metric: revenue gross, impressions, measurable_impressions, fill_rate, eCPM. Per channel/metric combinazioni dove PBI data non disponibile, test SKIP graceful con message documentato.

### CI schema drift gate (HARD-02)

- **D-04:** Estendere GitHub Actions workflow esistente (Phase 10.1 ha già HARD-03 drift gate per `created_at` format) per coprire ALL CHECK constraints in `backend/db/models.py` vs migration-derived schema. New job `schema-drift-check` runs on every PR.
- **D-05:** Migration-derived schema = `sqlite3 :memory:` con migrations 001..006 applicate sequenzialmente, dump schema. Compare con `models.py` CHECK columns. Fail-fast su qualsiasi divergence.
- **D-06:** Workflow file: nuovo `.github/workflows/schema-drift.yml` separato da pipeline esistente (clean separation of concerns).

### Silent-failure regression (HARD-03 extension)

- **D-07:** Extended `scripts/test_silent_failure_watchdog.py` (o equivalente file Phase 10.1 esistente) — aggiungere case per CSV-EOF boundary (Phase 17.4 incident pattern) + Path A fallback path (synthetic_no_athena).
- **D-08:** Test regression specifico Plan 02 Path A guard: `if channel == 'GOOGLE_ADEX' and mode == 'BACKTEST'` MUST NOT regress accidentalmente abilitando altri channel. Source-level grep test (Phase 17.2/17.3 pattern).

### PBI parity automation (HARD-04)

- **D-09:** Re-export `scripts/test_alert_revenue_pbi_parity.py` (Phase 17.4 Plan 01) come canonical PBI parity gate. Aggiunto a CI pipeline (`pytest` job) come blocker.
- **D-10:** Sample 2 HBM byte-perfect test PINNED ma `@pytest.mark.skip(reason='Phase 21 v1.4 Athena activation required')` — diventa GREEN auto quando Phase 21 lands credenziali.

### DOC-01 DATA_INTEGRATION.md gap matrix

- **D-11:** Aggiornare `docs/DATA_INTEGRATION.md` (path verificare in research) con sezione `## v1.3 PBI ↔ Sentinel Reproducibility Matrix`. Tabella row per ogni metric × channel con:
  - PBI source path (BigQuery query / Excel mapping / Adkaora export)
  - Sentinel source path (parquet column / CSV column / endpoint)
  - Match status: byte-perfect / ±X% / structural gap / pending v1.4
  - Riferimento phase chiusura (es. Phase 17.4 per Sample 1, Phase 21 v1.4 per HBM, Phase 19 per V1 channel granularity)
- **D-12:** Sezione gap disclosure esplicita:
  - OM taxonomy (Phase 17.1 publisher mapping)
  - eCPM/RPM denominator definitions
  - Hourly YoY synthetic (Phase 17.3 H6 root cause + Phase 17.4 fix)
  - Fill rate measurable_impressions (Phase 08 SCHEMA-03)
  - Top-50 publisher filter resolution (Phase 17.4 Path A)
  - 200 synthetic-era deprecated alerts (Phase 17.4 backfill split)
  - Phase 21 v1.4 Athena pending (Sample 2 HBM + 199 deprecated rewrite candidate)
  - V1 channel granularity pending (Phase 19 v1.4)
- **D-13:** Cross-link tra `DATA_INTEGRATION.md` + ROADMAP.md + 17.4-SUMMARY.md — agents downstream possano navigare.

### Plan breakdown (planner discretion)

Suggested 4-5 plans:
- 18-01: HARD-01 contract tests (parametrized parquet↔DB↔UI per 7 channel)
- 18-02: HARD-02 CI schema drift gate (.github/workflows/schema-drift.yml)
- 18-03: HARD-03 + HARD-04 regression test extension + PBI parity CI integration
- 18-04: DOC-01 DATA_INTEGRATION.md gap matrix completa
- 18-05: Deploy + UAT + SUMMARY/VERIFICATION (se applicabile — v1.3 close potrebbe non richiedere deploy se DOC-only commits)

### Claude's Discretion

- Specific Pytest fixture organization (conftest.py vs in-test fixtures)
- GitHub Actions cache strategy for schema check
- Markdown structure of DATA_INTEGRATION.md gap matrix (tables vs cards)
- Choice between extending Phase 17.4 `test_alert_revenue_pbi_parity.py` vs new file

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 17.4 D2 closure baseline (immediate predecessor)
- `.planning/phases/17.4-d2-closure-tecnica-post-phase-17-3-downgrade/17.4-CONTEXT.md` — D-01..D-16 decisions Phase 17.4
- `.planning/phases/17.4-d2-closure-tecnica-post-phase-17-3-downgrade/17.4-SUMMARY.md` — Phase 17.4 outcome
- `.planning/phases/17.4-d2-closure-tecnica-post-phase-17-3-downgrade/17.4-VERIFICATION.md` — D2CLOSE-01..04 evidence map
- `.planning/phases/17.4-d2-closure-tecnica-post-phase-17-3-downgrade/17.4-BACKFILL-REWRITE-REPORT.md` — 38+1 split with CSV-EOF section
- `scripts/test_alert_revenue_pbi_parity.py` — 4 invariants (template for HARD-04 extension)

### Phase 10.1 HARD-03 drift gate precedent
- `.planning/phases/10.1-pipeline-monitoring-hotfix-and-hardening/10.1-CONTEXT.md` — HARD-03 created_at canonical format gate
- Existing `.github/workflows/` files (read in research) — pattern to extend

### Schema migrations chain (HARD-02 derivation)
- `scripts/migrations/001_expand_channel_groups.sql` (Phase 08)
- `scripts/migrations/002_*` through `006_backfill_split_marking.sql` (Phase 09+10.1+17.4) — full sequence
- `backend/db/models.py` — CHECK constants source of truth

### PBI baseline data (HARD-04 + DOC-01)
- `.planning/intel/sentinel-2026-04-22/RECONCILIATION.md` — original PBI vs Sentinel numeric mismatch
- `.planning/intel/sentinel-2026-04-28/SYNTHESIS.md` — 5 RC canonical post-audit
- `.planning/intel/marco-2026-05-19/EMAIL-MARCO-FEEDBACK.md` — Sample 1 + Sample 2 PBI values

### Project north star
- `.planning/STELLA-POLARE.md` — v1.3 truth source
- `.planning/PROJECT.md` — milestone v1.3
- `.planning/REQUIREMENTS.md` §"Hardening" — HARD-01..04 + DOC-01 acceptance criteria
- `.planning/ROADMAP.md` §"Phase 18" — 3 SC integrali

### Global hard rules
- `~/.claude/CLAUDE.md` R-03 + R-04 + R-05 + R-13 (Phase 18 = code + CI + docs, no DB mutation, no Vercel deploy required unless DOC changes need re-export)
- Sentinel `CLAUDE.md` R-13 production-grade 10/10 mandate

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Phase 17.4 test scaffolding pattern**: `scripts/test_alert_revenue_pbi_parity.py` (4 invariants, sqlite3 + grep-verifiable) — extend per HARD-04
- **Phase 10.1 HARD-03 drift gate**: existing `.github/workflows/` for created_at format — extend pattern per HARD-02 schema drift
- **Phase 17.4 `_compute_hourly_totals_for_channel` + `_compute_network_totals_for_channel`**: PBI-parity helpers usable in contract tests as fixture source
- **Migration chain 001..006**: applied in sequence reproduces expected schema for HARD-02 comparison
- **`backend/db/models.py` CHECK constraints**: schema source of truth

### Established Patterns
- **TDD posture RED→GREEN** (Phase 17.2/17.3/17.4) — Phase 18 plans dovrebbero seguire stesso commit graph
- **Phase 09 D-14 deprecated soft-delete + Phase 17.4 D-11 audit trail preservation** — DOC-01 deve documentare entrambi
- **Atomic commit R-03 + R-04 chirurgico** — Phase 17.4 5-plan graph è il template

### Integration Points
- **GitHub Actions**: nuovi workflow files in `.github/workflows/` (verifica path esatto in research)
- **CI pipeline**: aggiungere `pytest tests/contracts/` + `python scripts/test_alert_revenue_pbi_parity.py` come blocker
- **`docs/DATA_INTEGRATION.md`** (verifica path esatto in research) — single canonical file aggiornato
- **No DB mutation** Phase 18 (read-only tests + docs + CI) → snapshot byte-identical → no Vercel re-deploy required salvo DOC-01 update tocchi files served by Vercel

</code_context>

<specifics>
## Specific Ideas

- **Phase 18 chiude v1.3 milestone**: post-Phase-18 close, v1.4 milestone formally opens (Phase 19/20/21). v1.3 retrospective + SHIPPED tag candidate.
- **No deploy required default**: Phase 18 = hardening (tests + CI + docs). No production code change (zero `backend/agents/`, `backend/api/`, `frontend/` source mutation unless contract tests reveal regressions). Snapshot byte-identical. Vercel re-deploy ONLY se DOC-01 update tocca files served live (improbable — DATA_INTEGRATION.md è docs/, not frontend/).
- **R-13 mandate**: 10/10 architectural quality non negotiable. Contract tests devono ESSERE 7-channel comprehensive, not "minimal subset". HARD-02 drift gate MUST cover ALL migrations, not "most".
- **Phase 17.4 unblocked Phase 18**: backfill rewrite + Path A live; PBI parity gate ora ha real data (38 GOOGLE_ADEX real_csv) per pinnare invariants byte-perfect.

</specifics>

<deferred>
## Deferred Ideas

### To Phase 19 v1.4
- V1 Channel granularity refactor (Diretta/Deal/Open) — design meeting Iolanda required

### To Phase 20 v1.4
- V2 Open Market distribution study + UI breakdown

### To Phase 21 v1.4
- Athena HBM/HBP/TAM activation (credenziali production)
- Sample 2 HBM byte-perfect closure (€688 PBI)
- Decision: rewrite 199 deprecated alerts post-Athena (operator decide)

### To email-Marco workflow
- 9/9 punti chiusi confirmation
- Bozza email finale + invio (gated Phase 21 close)

### Reviewed Todos
- 0 todos matched Phase 18 scope (verified `gsd-tools todo match-phase 18` returns empty)

</deferred>

---

*Phase: 18-hardening-pbi-contract-tests-docs*
*Context defined: 2026-05-21 (operator-direct definition, skip discuss-phase)*

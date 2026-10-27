---
auditor: B
date: 2026-04-28
status: complete
---

# Audit B — Phase coverage matrix

## Verdict (1 paragraph)

**Phases 07-10.2 fixed a different bug than the email complains about.** The 6 numeric complaints in Vito's 2026-04-22 email map almost entirely to phases that have **not started** (11, 12, 13, 14): network totals + filter API + server-side baseline (#1, #2, #3), gross/net + channel scope + reference-period labels (#5, #6), and bacino/fillrate/eCPM/RPM corrections (#4a-d). Of the 6 numeric complaints, **zero are addressable on the live Vercel deploy today** because the deploy is pinned to a pre-Phase-08 commit (200 legacy alerts only, channel_group enum still `{GOOGLE, OPEN_BIDDING}`, 33 days stale `timestamp=2026-03-26T16:01:12`). Even on local main HEAD, where 6 phases (07, 08, 09, 10, 10.1, 999.1) plus 3/4 plans of 10.2 are fully shipped, the email's UI-visible complaints (#5 timeframe label, #6 missing timeline) and numeric complaints (#1-4) remain entirely unaddressed because they are owned by Phases 11/12/13/14. Best lever in the next 48h: deploy local main to Vercel (closes complaint #4b numerically via SCHEMA-03 + #4a via Phase 09 backfill freshness, partially) — but does NOT close #1/#2/#3/#5/#6. Critical path to address ALL 6 numeric complaints: Phase 11 → 12 → 13 → 14, estimated 4-6 working days at current velocity.

## B.1 Phase ledger

Status verified by SUMMARY.md frontmatter + git log on local `main` HEAD (798df97). REQUIREMENTS.md/`.planning/STATE.md` flags from `wip/pre-10.2-rescue` (current branch) are STALE w.r.t. main; `main:.planning/STATE.md` is the authoritative source.

| Phase | Title | Status | What it actually delivers (from PLAN scope + SUMMARY) | Address email complaints # |
|-------|-------|--------|-------------------------------------------------------|----------------------------|
| 07 | DB WIP Investigation | **Done** (2026-04-22, 1 plan, 15min) | Dual schema dumps WIP+HEAD; FORWARD_PORT decision; idempotent `scripts/migrations/000_wip_drift_baseline.sql` capturing 5 new tables from operator workflow drift | (none — gating diagnostic) |
| 08 | Schema Migration + ETL Extensions | **Done** (2026-04-23, 5 plans, ~89min) | Migration 001 expands channel_group CHECK to 8 values; models.py CHANNEL_GROUP_CHECK_VALUES tuple; ETL preserves `measurable_impressions` (line 187 fix); adds `sell_type_proxy` column; 20-field parquet v2; Mondadori fill-rate regression 35.2% PBI within ±1.5 ppt | Indirect prerequisite for #4b (SCHEMA-03 enables fill rate match), #2/#3/#4a-d (sell_type_proxy enables filter), but UI-visible only after Phase 14 |
| 09 | Alert Backfill + Legacy Migration | **Done** (2026-04-23, 3 plans, ~102min) | 238 fresh BACKTEST alerts across 60 days 2026-01-23→2026-03-23; 200 legacy pre-v1.2 alerts soft-deprecated (`deprecated=1` + D-15 reason); API `?include_deprecated` opt-in; orchestrator channel validation against canonical 8-tuple; COVERAGE-GAP.md documents 31-day gap 2026-03-24→today | Indirect — restores alert list freshness once deployed (currently DB-only, not on Vercel) |
| 10 | Pipeline Silent-Failure Monitoring | **Done** (2026-04-23, 3 plans, ~52min) | Migration 003 adds `pipeline_runs.alerts_written_count`; `GET /api/health/alerts-pipeline` (1.9ms); `silent_failure_watch` APScheduler 60min cycle; Block Kit P0 Slack meta-alert payload | (none — internal observability) |
| 10.1 | Pipeline Monitoring Hotfix & Hardening | **Done** (2026-04-24, 8 plans, ~55min) | Migration 004 normalizes 438 `alerts.created_at` rows to canonical space-sep naive UTC microseconds; HARD-03 drift gate enforces it; watchdog filters `mode='LIVE'`; Slack retry distinguishes HTTPError/URLError + honors `Retry-After`; counter semantics 0/1 on dedup vs new-row; final flip `silent_failure_monitor.enabled=true` | (none — internal observability hardening) |
| 999.1 | Investigate LIVE silent since 2026-03-23 | **Done** (2026-04-25, 2 plans, ~8min) | Read-only diagnostic `scripts/diagnose_live_silence_999_1.py` (663 lines, mode=ro URI); DIAGNOSIS.md ranks H1 HIGH (parquet stale at 2026-03-23) + H2 MEDIUM (legacy 2-channel scheduler dead) + H3; Path A operator-signed in DECISION.md; `phase_10_2_safe: true` | (none — root-cause documentation) |
| 10.2 | Pipeline Monitoring Security Hardening | **Partial 3/4** (2026-04-27, MONITOR-11/13/14 closed; MONITOR-12 deferred) | `send_daily_digest` cutoff canonicalized + HARD-03 drift gate extended (CR-01); `Retry-After` parsing bounded ≤60s anti-DoS; `_restore` atomic across 4 migration drivers. **MONITOR-12 (Slack webhook rotation YAML→null + env-var ingress) deferred via abort signal — operator pivoted to Vercel deploy priority.** | (none — internal hardening) |
| 11 | Network Totals + Filter API + Server-Side Baseline | **Not started** | (per ROADMAP §Phase Details + REQUIREMENTS.md) `GET /api/metrics/network-totals?date=...&channel=...` upstream-CSV streaming; `?sell_type` query param on top-publishers/alerts/revenue-status-24h; alert payload `baseline_bacino`+`baseline_coverage` server-side 7w rolling | **#1** (hourly AdEx PBI parity), **#2** (Triage AdEx imp 14M PBI vs 10M), **#3** (Triage AdEx revenue €27.2k PBI vs €25.9k) — D1 hybrid endpoint is the structural fix |
| 12 | WIP Atomic Commits + Triage Server-Side | **Not started** (WIP commits A+C exist on `wip/pre-10.2-rescue` ONLY, NOT on main; Commit B not committed) | Commit A design+i18n (10 files); Commit B IT→EN (10 files); Commit C backend correctness `routes.py` YoY 7w rolling + complete-day detection + `available_dates` + `publisher_routes.py` bacino dedup (factor in n_channels per cell); CORR-01 server-side baseline consumer; CORR-08 weighted fill rate; CORR-09 i18n keys for KPI cards | **#4a** (bacino dedup — Commit C `publisher_routes.py` directly), **#4b/c/d** (consequences of #4a), CORR-01 supports baseline trust |
| 13 | Dashboard Date Navigation | **Not started** (Commit D not started) | Commit D atomic 8 files: RevenueStatus24h date picker + month selector pages + new API contract consumer (`available_dates`) | Indirectly addresses #5 (date scoping makes UI period explicit at the CONTAINER level, not the metric-card level) |
| 14 | UI Labeling + Filter Exposure | **Not started** | CORR-02 reference-period label "as of [hour] UTC"; CORR-03 gross+net side-by-side D2; CORR-04 channel scope badge "GOOGLE_ADEX only"; CORR-05 timezone+currency on every metric card; CORR-06 PublishersPage URL filter state; CORR-11 derived filters dropdown (sell_type_proxy, geo, env, tier, gross/net toggle) | **#5** (CORR-02 + CORR-05 metric-card label is the direct fix), **#6** (CORR-04 channel badge — explains why "Google" alerts have no full-network timeline) |
| 15 | UI Resilience | **Not started** | CORR-07 diagnostic empty states ("No 7w history. Alert &lt; 7 days old or data not yet aggregated"); CORR-10 ErrorBoundary on chart components | **#6** (CORR-07 is the direct fix for the empty "No revenue trend data available" state) |
| 16 | Vercel Static Export Decision | **Not started** | Operator decision: ship Commit E as v1.3.1 OR shelve with rationale | (none — release vehicle decision) |
| 17 | Data Cleanup | **Not started** | CLEAN-01 floor_cpm dead column decision; CLEAN-02 Mondadori/Mondadori_npa aggregation policy | Latent #4a/e — `Mondadori_npa` is a separate row in publishers/top response; combining or labeling it as GDPR variant changes Vito's mental model |
| 18 | Hardening + PBI Contract Tests + Docs | **Not started** | HARD-01 7-channel parquet↔DB↔UI contract tests; HARD-04 numeric PBI-match gates (Mondadori bacino ≤0.5%, Jan 12 GOOGLE_ADEX gross ≤2%, network total ≤2%); CI gate CHECK drift detection; DATA_INTEGRATION.md + PBI gap disclosure (DOC-01) | Disclosure-side: structurally documents WHY some numbers will never match exactly (OM taxonomy, eCPM denominator) — closes the trust loop on #4e |

**Note on ROADMAP/REQUIREMENTS phase numbering:** ROADMAP §Phase Details lists 07, 08, 09, 10, **10.1, 999.1, 10.2**, 11, 12, 13, 14, 15, 16, 17, 18. REQUIREMENTS.md traceability table uses different decimal numbering (e.g. "10.5 Network Totals" — but the "Phase Details" body and the latest commits use Phase 11 for the same scope). **Discrepancy flagged for operator** — see Open Questions §1.

## B.2 Complaint → blocking phases

For each of Vito's 6 numeric complaints (4a-e collapsed to "the Mondadori cluster" since they share a single root cause):

| # | Complaint | Required phases | Blocking gate | Status |
|---|-----------|-----------------|---------------|--------|
| 1 | Dashboard hourly Revenue AdEx ≠ PBI | 11 (API-01 network-totals streaming endpoint) + 14 (CORR-04 channel scope badge so user knows it's GOOGLE_ADEX-only) | Phase 11 NOT STARTED | Cannot ship today; not addressable by deploy alone |
| 2 | Triage AdEx impressions 14M PBI vs 10M Sentinel (Jan 12) | 11 (API-02 sell_type filter — currently not exposed) + 14 (CORR-03 gross/net + CORR-04 channel scope) | Phase 11 NOT STARTED | Cannot ship today; root cause is sell_type filter not visible to user; numbers themselves are likely correct given filter |
| 3 | Triage AdEx revenue €27.2k PBI vs €25.9k Sentinel | 11 (API-02 sell_type filter) + 14 (CORR-03 gross+net side-by-side) | Phase 11 NOT STARTED | Cannot ship today |
| 4a | Mondadori bacino Feb 366M PBI vs 133M Sentinel | **WIP commit C** `publisher_routes.py` bacino dedup (lives on `wip/pre-10.2-rescue` `7ea4a74` only) → Phase 12 lands it on main → deploy → 14 (CORR-04 sell_type label) | WIP not on main; Phase 12 NOT STARTED; deploy gap | **Closest to addressable**: WIP fix exists, but per email decomposition the fix DECREASES bacino further (Sentinel goes from 36% of PBI to even less) — direction of correction may worsen the symptom; numerical validation needed BEFORE landing |
| 4b | Mondadori fill rate Feb 35.2% PBI vs 41.8% Sentinel | SCHEMA-03 ✓ (Phase 08 done) + 14 (CORR-04 channel scope) | **Source code shipped to main; NOT on Vercel** | Closest to deploy-ready: SCHEMA-03 already validated 35.2% within 1.5 ppt PBI on local data; needs deploy + WIP-04 bacino fix to fully reconcile |
| 4c-d | eCPM €1.51/€2.08, RPM €0.51/€0.87 | Phase 12 (Commit C bacino dedup) + 14 (CORR-04 channel scope) | Phase 12 NOT STARTED | Consequences of 4a/4b; same blockers |
| 4e | Mondadori revenue €188k PBI all / €90k OM PBI / €115k Sentinel | 14 (CORR-03 gross+net D2) + 18/DOC-01 (OM taxonomy disclosure) | Phase 14 NOT STARTED | Structurally cannot exact-match; scope is "label + disclose", not "fix numbers" |
| 5 | Alert UI revenue without temporal reference period | 14 (CORR-02 "as of [hour] UTC" + CORR-05 timestamp+timezone on metric card) | Phase 14 NOT STARTED | Pure UI label addition; smallest blast radius of any complaint |
| 6 | "Google" alerts have no timeline | 14 (CORR-04 channel badge — explains why) + 15 (CORR-07 diagnostic empty state) | Phases 14 + 15 NOT STARTED | Currently shows "No revenue trend data available for this alert period" — generic; needs diagnostic copy + channel scope explanation |

### Addressable RIGHT NOW by deploying current local main + WIP commit C

**Numerically:** Only complaint **#4b (fill rate)** moves toward fix because SCHEMA-03 is shipped to main (parquet now contains `measurable_impressions`). Even this requires the consumer (`avgFillRate` computation in PublishersPage) to switch from `simple_average` to `weighted by impressions` (CORR-08, owned by Phase 12) — which is part of WIP Commit C semantics but not implemented in the current Commit C diff (only `fill_rate = total_impressions / total_bacino` per-publisher); the PublishersPage UI-side simple-average bug is separate.

**UI-wise:** Zero of #5/#6 are addressable today — they require code that doesn't yet exist on any branch.

### Phase 11 unblocks: #1, #2, #3 (numerically)

Phase 11 delivers `/api/metrics/network-totals` (D1 hybrid streaming) which is the only structural fix for #1 (hourly AdEx PBI parity is impossible against top-50-filtered parquet — the email is correct, the numbers cannot match without bypassing the filter). Phase 11 also adds `?sell_type=Open_Market` filter (#2/#3 root cause: PBI shows all-channel, Sentinel shows GOOGLE_ADEX only — making the difference *visible* in the UI is the resolution, not making the numbers identical).

### Phase 12 unblocks: #4a, #4b, #4c, #4d (numerically) + #6 (partially via CORR-01)

Phase 12 lands WIP Commit C (`publisher_routes.py` bacino dedup + `routes.py` YoY 7w + `available_dates`) on main, plus CORR-01 (TriageSection consumes server-side `baseline_bacino`/`baseline_coverage`). Without API-03 (Phase 11 prerequisite for `baseline_bacino` server payload), CORR-01 cannot land — **Phase 12 has a hard dependency on Phase 11.**

### Phase 13 unblocks: nothing in the email directly

Phase 13 (Commit D dashboard date navigation) is a structural pre-requisite — operator can navigate to a specific day, but does not by itself address the email. Email complaints map to Phase 14.

### Phase 14 unblocks: #5 (CORR-02/05) + #6 (CORR-04) + label-side of #2/#3/#4a-e

Phase 14 is **the highest-impact email-fixing phase** because it adds the "as of X UTC" labels, the channel scope badge ("GOOGLE_ADEX only"), the gross+net side-by-side display, and the URL filter state. Most of the email's "non torna" feedback is a UI-clarity problem solvable by labels; the underlying numbers are largely correct (validated in `STATE.md` Numeric validation Mondadori Feb).

### Out-of-scope of v1.3 entirely

- Hourly multi-channel data: source `hour_kpi.csv` is GOOGLE_ADEX-only; PBI Hour Analysis includes more channels — gap disclosed via DOC-01 (Phase 18) but not numerically closed.
- OM revenue PBI exact-match: structural taxonomy delta (PBI bundles ~€40k DIRECT into OM); v1.3 documents the gap, doesn't close it.
- `sell_type` real (not proxy): deferred to v1.4 OPS-02.

## B.3 Critical path

### Dependency graph

```
07 (Done) ──┐
            └─► 08 (Done) ──► 09 (Done) ──► 10 (Done) ──► 10.1 (Done) ──► 999.1 (Done) ──► 10.2 (Partial 3/4)
                                                                                                  │
                                                                                                  ▼
                                                                                          11 (NOT STARTED)
                                                                                          │   API-01 (network-totals streaming)
                                                                                          │   API-02 (sell_type filter)
                                                                                          │   API-03 (baseline_bacino server-side)
                                                                                          ▼
                                                                                          12 (NOT STARTED)
                                                                                          │   Commits A+B+C atomic (WIP land on main)
                                                                                          │   CORR-01 (TriageSection consumes API-03)
                                                                                          │   CORR-08 (weighted fill rate)
                                                                                          │   CORR-09 (i18n keys)
                                                                                          ▼
                                                                                          13 (NOT STARTED) ──► 14 (NOT STARTED) ──► 15 (NOT STARTED)
                                                                                          │ Commit D consumer  │ CORR-02/03/04/05/06 │ CORR-07/10
                                                                                          │ available_dates    │ + filter UI         │ empty states
                                                                                          ▼                    ▼
```

**Why each dep is hard:**

- **12 depends on 11**: Commit C `publisher_routes.py` bacino dedup is independent of 11, BUT CORR-01 (Triage server-side baseline) needs API-03 alert payload `baseline_bacino`/`baseline_coverage` fields to consume — the frontend cannot remove `revenueRatio * 0.95` heuristic without the backend payload.
- **13 depends on 12**: Commit D `RevenueStatus24h` consumes `available_dates` from `routes.py` (Commit C) — without C on main, D's contract is undefined.
- **14 depends on 13**: CORR-04 channel scope badge + CORR-02 reference period label are added to the same metric cards Commit D edits; merge conflicts otherwise.
- **15 depends on 14**: ErrorBoundary wraps charts that 14 may rename / restructure for sell_type filtering.

### Parallelizable work

- Inside Phase 11: API-01 (read-only streaming endpoint, isolated module), API-02 (filter param plumbing), API-03 (alert payload extension) can run in 3 parallel waves.
- Inside Phase 12: Commit A (design system + i18n infra, frontend-only) and Commit B (IT→EN content swap, frontend-only) and Commit C (backend routes/publisher_routes) touch disjoint files — 3 parallel waves; CORR-08/09 fold into Wave 2 (frontend) once i18n keys exist.
- Inside Phase 14: CORR-02/03/04/05 (label additions to metric cards) can be one wave; CORR-06 (URL filter state on PublishersPage) is independent; CORR-11 (filter UI dropdown) needs API-02 (Phase 11) wired through.

### Estimated days at current velocity

Velocity baseline (from `.planning/STATE.md` "Velocity" + SUMMARY frontmatter):

- v1.1 mean plan: ~7 min/plan
- v1.3 mean plan (07-10.2 ledger): plans range 2-85min (median ~10min); ETL/migration plans (08-04, 09-03) are 35-85min outliers
- Wall-clock velocity: ~3-5 plans / hour for code-only plans, ~1-2 plans / hour for migration+verification plans
- Days-of-work calibration: Phase 10.1 = 8 plans = 1 working day end-to-end (operator was online ~3h that day). Phase 10 = 3 plans = ~½ working day.

| Phase | Plans estimated | Hours estimate | Days estimate |
|-------|-----------------|----------------|---------------|
| 11 | 5 (3 endpoints + 1 contract test + 1 BLOCKING apply) | 4-6h | 0.5-1d |
| 12 | 7 (3 commits A/B/C + CORR-01 + CORR-08 + CORR-09 + verification) | 6-10h | 1-1.5d |
| 13 | 3 (Commit D + tests + UI verification) | 3-5h | 0.5d |
| 14 | 8 (CORR-02/03/04/05 in parallel + CORR-06 + CORR-11 + filter dropdown wiring + verification) | 8-12h | 1-2d |
| 15 | 2 (CORR-07 + CORR-10 + verification) | 2-3h | 0.5d |
| **Total to address #1-6** | **20-25 plans** | **23-36h** | **3-5 working days** |

Add: Vercel deploy verification cycles (~30min each x 5 phases) + operator-verification gates (R-04 chirurgico) realistically push this to **4-6 working days** end-to-end.

## B.4 What can ship this week

Ranked by **email impact / blast radius / hours**:

### #1 (highest impact / lowest risk): **Deploy local main HEAD to Vercel** — 2-4 hours

- **Email impact**: Partial #4b (fill rate now reconcilable from `measurable_impressions`); complaint context (#1-6) becomes evaluable on stabilized backend; the silent-failure structural fix that motivated v1.3 finally becomes visible to operators.
- **What still stays broken**: ALL 6 numeric complaints — fill rate UI consumer still uses simple_average (CORR-08), no labels (#5), no channel badge (#6), no filter API (#1/2/3), no server-side baseline (CORR-01).
- **Blast radius**: HIGH if R-16 deploy gate not honored (the wip/pre-10.2-rescue branch has stale `.planning/` files and unmerged main commits). Operator must deploy from `main` not from `wip/pre-10.2-rescue`. STATE.md on main says "operator priority pivoted to Vercel dashboard deploy" — deploy is already the active workstream.
- **Verdict**: Should ship today.

### #2: **Cherry-pick WIP Commit C `publisher_routes.py` bacino dedup ONLY (drop the routes.py YoY changes)** — 4-6 hours

- **Email impact**: Hardens #4a numerically — bacino computation no longer multi-counts across channels.
- **Catch**: Per email decomposition note "fix DIMINUISCE ulteriormente bacino → potrebbe peggiorare il bug nel verso opposto". Sentinel reports 133M; PBI reports 366M; Sentinel is already 36% of PBI; the dedup fix lowers Sentinel further. **Numerical validation MUST run BEFORE land** (compare pre-fix and post-fix Mondadori Feb bacino on parquet v2). If post-fix bacino drops below ~120M, Sentinel diverges further from PBI — this commit becomes a regression.
- **What still stays broken**: #4b/c/d (consumed metrics need re-validation); #1/2/3/5/6.
- **Blast radius**: MEDIUM — single backend file, atomic commit, can revert.
- **Verdict**: Ship only after `scripts/test_mondadori_fill_rate_regression.py`-equivalent regression run validates direction.

### #3: **Single-file CORR-02 prototype: add "as of [timestamp] UTC" label to AlertDetailPage RevenueStatusSection** — 2-3 hours

- **Email impact**: Closes #5 directly. Vito's screenshot literally asks "il dato di revenue a quale periodo fa riferimento?" — the answer "alert generated at [created_at] UTC reflecting data through [hour boundary]" can be a single span.
- **Blast radius**: LOW — one component, one file, no API changes, no backend changes. Frontend-only static text from existing alert.timestamp field.
- **What still stays broken**: #1/2/3/4a-e/6.
- **Verdict**: Should bundle with deploy as `v1.3.0-rc.1` UI fix.

### #4: **Single-file CORR-04 prototype: channel scope badge on AlertDetailPage** — 2-3 hours

- **Email impact**: Closes the *cognitive* part of #6 ("alert con etichetta Google" — operator now sees "GOOGLE_ADEX only — full network timeline unavailable" badge).
- **Blast radius**: LOW — single component, leverages `alert.channel_group` field.
- **What still stays broken**: The empty timeline itself (CORR-07 needed for "No 7-week history" copy); #1/2/3/4/5.
- **Verdict**: Pair with #3 above.

### #5 (lowest leverage): **CORR-09 i18n keys for KpiCards** — 1-2 hours

- **Email impact**: ZERO direct on the 6 complaints (operator language is Italian; KpiCards labels are English).
- **Verdict**: Skip unless bundled into Phase 12 properly.

### Recommended 2-day deliverable bundle

1. **Day 1 morning** (2-4h): Deploy main HEAD to Vercel. Verify `/api/health` reports current build SHA, alert list shows backfill 2026-01-23 → 2026-03-23, channel_group enum accepts 8 values.
2. **Day 1 afternoon** (3-4h): #3 + #4 as one frontend-only commit on a `v1.3.0-rc.1-ui-labels` branch — adds CORR-02 + CORR-04 prototypes to AlertDetailPage. Deploy preview, screenshot to Vito for sign-off.
3. **Day 2** (4-6h): Begin Phase 11 plan-checker iter 1 (do not execute). Ship plan-quality bar before any code on the critical path.

Total realistic email-impact in 2 days: **partial fix on #5 and #6, partial-numerical on #4b** (deploy enables it). #1/#2/#3/#4a are NOT addressable in 2 days.

## B.5 Completion vs deployment

For every requirement marked `[x]` in `main:.planning/REQUIREMENTS.md`, comparing local main HEAD vs origin/main vs Vercel.

| Requirement | Local main | origin/main | Vercel deploy | Notes |
|-------------|------------|-------------|---------------|-------|
| SCHEMA-01 (CHECK 8 channels) | ✓ | ✗ | ✗ | Migration 001 applied to local DB; Vercel DB still has 2-channel CHECK (200 alerts use only GOOGLE/OPEN_BIDDING enum) |
| SCHEMA-02 (models.py sync) | ✓ | ✗ | ✗ | `git diff origin/main main -- backend/db/models.py` shows GOOGLE → GOOGLE_ADEX + 6 new enum values + A8 — NOT on origin |
| SCHEMA-03 (measurable_impressions ETL) | ✓ | ✗ | ✗ | etl_csv_to_parquet.py:187 fixed locally; parquet v2 not deployed |
| SCHEMA-04 (sell_type_proxy column) | ✓ | ✗ | ✗ | Same — local parquet v2 only |
| BACKFILL-01 (60 days alerts) | ✓ | ✗ | ✗ | 238 fresh alerts in local DB only; Vercel DB shows 200 legacy (max date 2026-01-22) |
| MONITOR-01 (`/api/health/alerts-pipeline`) | ✓ | ✗ | ✗ (404) | Endpoint live on local FastAPI; HTTP 404 on Vercel |
| MONITOR-02 (silent_failure_watch) | ✓ | ✗ | ✗ | APScheduler job exists on main; Vercel scheduler running v1.2.0 only |
| MONITOR-03 (alerts_written_count) | ✓ | ✗ | ✗ | Migration 003 applied locally only |
| MONITOR-04 (canonical created_at) | ✓ | ✗ | ✗ | Migration 004 applied locally only |
| MONITOR-05 (LIVE filter watchdog) | ✓ | ✗ | ✗ | Same |
| MONITOR-06 (find_open_alert boundary) | ✓ | ✗ | ✗ | Same |
| MONITOR-07 (Slack retry HTTPError/URLError) | ✓ | ✗ | ✗ | Same |
| MONITOR-08 (counter semantics) | ✓ | ✗ | ✗ | Same |
| MONITOR-09 (diagnose_live_silence script) | ✓ | ✗ | ✗ | Read-only script in scripts/, irrelevant to deploy parity |
| MONITOR-10 (operator decision documented) | ✓ | ✗ | ✗ | Doc-only |
| MONITOR-11 (send_daily_digest cutoff) | ✓ | ✗ | ✗ | Notifier change not deployed |
| MONITOR-13 (Retry-After bounded) | ✓ | ✗ | ✗ | Notifier change not deployed |
| MONITOR-14 (atomic _restore) | ✓ | ✗ | ✗ | Migration drivers updated locally only |
| MIGRATE-01 (legacy alerts deprecated) | ✓ | ✗ | ✗ | Vercel `/api/alerts` serves all 200 legacy with deprecated=undefined (column doesn't exist on deployed DB) |

**Quantified gap:**

- **19 of 19** completed v1.3 requirements are local-main-only.
- **150 commits** on local main not on origin/main.
- **Vercel deploy lag**: 33 days (snapshot timestamp `2026-03-26T16:01:12`); reports `version: 1.2.0` (pre-v1.3).
- **Live deploy commit**: appears to be `7ca7808 fix: remove domain hint from login page error message` or sibling — i.e. the v1.2 deployment scaffolding commits, NOT v1.3.

**Implication**: every "shipped" v1.3 requirement is functionally `[~]` (implemented but not delivered). The single highest-leverage operator action is deploy.

## Open questions for operator

1. **Phase numbering discrepancy**: REQUIREMENTS.md traceability table maps API-01/02 to "Phase 10.5", CORR-02..06 to "Phase 13", CORR-07/10 to "Phase 13.5", WIP-06 to "Phase 14", CLEAN-01/02 to "Phase 14.5", HARD-01..04 to "Phase 15". ROADMAP.md §Phase Details body uses Phase 11 for the same scope, Phase 13/14/15 differently, etc. Which numbering is canonical for execution? (I treated ROADMAP §Phase Details body as authoritative since it carries the active execution checkboxes.)
2. **WIP commit C direction-of-correction risk**: per email decomposition, the bacino dedup fix in `publisher_routes.py` may decrease Sentinel bacino further (Sentinel currently 133M = 36% of PBI 366M; post-fix could be lower). Validation needed: run PublishersPage Mondadori Feb against parquet v2 BOTH pre- and post-WIP-04 fix on local; if post-fix < pre-fix, the commit is a regression vs the email and must NOT land.
3. **Vercel deploy mechanics**: STATE.md notes Plan 10.2-04 was "deferred via abort signal — operator priority pivoted to Vercel dashboard deploy". What is the deploy plan? (Vercel `vercel.json` exists at root and frontend/; `scripts/deploy.sh` exists on `wip/pre-10.2-rescue` only.) Recommend: deploy from main, not from wip branch — wip has stale `.planning/` files (REQUIREMENTS.md / STATE.md / ROADMAP.md regressed to pre-10.2 state; `git diff main wip/pre-10.2-rescue -- .planning/` shows -340 lines of progress).
4. **Phase 11 API-03 vs CORR-01 (Phase 12)**: REQUIREMENTS.md `Phase-to-requirements reverse index` shows API-03 in Phase 11; ROADMAP §Phase Details puts API-03 success-criterion under Phase 11 ("Alert payload contains `baseline_bacino` and `baseline_coverage` computed server-side"); but CORR-01 (consumer) is under Phase 12. Confirm execution order is 11 (producer) → 12 (consumer), and Plan 11 must complete API-03 before Plan 12 Wave 2 (frontend) can land — otherwise CORR-01 cannot be tested.
5. **Plan 10.2-04 MONITOR-12 webhook rotation**: Currently deferred. Phase 11/12 do not depend on it. Recommend: keep deferred until next operator session; not on critical path for email response.
6. **PBI parity acceptance threshold**: HARD-04 specifies Mondadori bacino ≤0.5%, Jan 12 GOOGLE_ADEX gross ≤2%, network total gross ≤2%. The email lists Sentinel-vs-PBI deltas of ~30-70% on Mondadori bacino/eCPM/RPM and ~6% on Triage revenue. Will Vito accept "match within 2%" when his current observed delta is 30-70%? The honest answer is "no, the gap will not close via tolerance — it closes via channel scope label + sell_type filter exposing that he was comparing all-channel PBI to GOOGLE_ADEX-only Sentinel." This is a **communication** answer, not an engineering answer. Operator may want to draft a written reply to Vito establishing this framing BEFORE Phase 11 ships, to avoid the "shipped + still wrong" outcome.

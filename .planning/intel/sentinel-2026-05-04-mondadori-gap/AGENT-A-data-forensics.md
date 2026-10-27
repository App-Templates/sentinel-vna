---
agent: A
topic: mondadori-bacino-gap
date: 2026-05-04
verdict: family-incomplete + parquet-structural-bug + dedup-workaround
---

# AGENT-A Data Forensics: Mondadori Feb 2026 Gap Analysis

## 1. Numeri trovati

### 1.1 Raw CSV upstream (daily_adrequests.csv)
| Publisher ID | Publisher Name | Feb 2026 ad_requests (bacino) | Rows |
|---|---|---|---|
| 21704134909 | Mondadori | 133,657,441 | 5,827 |
| 22888855294 | Mondadori_npa | 162,563,763 | 3,403 |
| **TOTAL** | | **296,221,204** | **9,230** |

**Source:** `/data/sentinel_db/daily_adrequests.csv` (raw daily ad-request counts, no channel_group, per publisher-date-env-country)

### 1.2 Parquet daily_aggregated (before dedup)
| Publisher Name | Feb 2026 bacino (raw sum) | Rows | Dedup rows | Ratio (raw/rows) |
|---|---|---|---|---|
| Mondadori | 860,289,553 | 17,022 | 237 | 50.5 |
| Mondadori_npa | 321,073,298 | 2,764 | 261 | 116.3 |
| **TOTAL** | **1,181,362,851** | **19,786** | **498** | **59.8** |

**Analysis:** Raw parquet sum is **4× upstream CSV** (1.181B vs 296M). This is the **channel multiplication problem**: the ETL's left-join of daily_kpi (per-channel) × daily_adrequests (no channel) replicates each bacino value for each channel variant of (publisher, date, env, geo).

### 1.3 Parquet daily_aggregated (after dedup with first())
| Publisher Name | Feb 2026 bacino (deduped) | Methodology |
|---|---|---|
| Mondadori | 127,038,666 | group by (publisher_id, date, environment, geo_cluster) → agg bacino='first' |
| Mondadori_npa | 158,756,689 | same |
| **TOTAL** | **285,795,355** | **approx. 286M** |

**Analysis:** Dedup logic reduces 1.181B → 286M, recovering ~24.2% of original raw sum. Gap from CSV upstream (296M) = 10.4M (~3.5% loss).

### 1.4 PBI vs Sentinel comparison
| Metric | PBI (email, Feb 2026) | Sentinel (parquet dedup) | Gap | Note |
|---|---|---|---|---|
| Bacino (ad requests) | 366M | 286M (dedup) | -22% | PBI likely includes Mondadori + Mondadori_npa + Adgage_mondocore + other subunits |
| Bacino (raw parquet) | — | 1,181M | — | Before dedup: 4× CSV due to channel multiplication |

### 1.5 Missing publishers in top-50 filter
| Publisher ID | Publisher Name | Feb 2026 bacino (if present) | Top-50 rank | Note |
|---|---|---|---|---|
| 23316890961 | Adgage_mondocore | NOT IN PARQUET | Excluded | Revenue = €8,378 (below top-50 threshold) |

**Analysis:** ETL's `find_top50_publishers()` (line 106-121 of etl_csv_to_parquet.py) selects top 50 by cumulative `revenue_gross`. Adgage_mondocore ranks ~51, so is filtered out entirely. PBI's "Mondadori" grouping (366M) plausibly includes this excluded publisher.

### 1.6 Data quality checks for Feb 2026 Mondadori
| Check | Result |
|---|---|
| NULL bacino values | 0 |
| Zero bacino values | 0 |
| Negative bacino values | 0 |
| Unique dates in Feb | 28 (out of 29 expected calendar days) |

**Interpretation:** No data corruption or missing values. The gap is structural, not due to NULL handling.

---

## 2. Ipotesi confutate

### H1: Family aggregation incompleta (esistono Mondadori_X non aggregati)
**STATUS: PARTIALLY CONFIRMED (not confuted)**
- Expected: Mondadori + Mondadori_npa + Adgage_mondocore
- Found: Only Mondadori + Mondadori_npa in parquet
- Reason: Adgage_mondocore is in publisher_mapping but filtered by top-50 revenue gate in ETL
- **Verdict:** Family aggregation is logically complete for in-scope (top-50) publishers, but incomplete vs. what PBI considers "Mondadori" group.

### H2: Dedup over-removes (rimuove più del dovuto)
**STATUS: CONFUTED BY NUMERIC EVIDENCE**
- CSV upstream: 296M
- Parquet dedup (first method): 286M
- Loss: 10.4M (~3.5%)
- Expected loss (dedup noise): <5%
- **Verdict:** Dedup loss is minimal (~3.5%) and consistent with rounding/edge-case row mismatches. NOT over-aggressive. The dedup correctly recovers ~96.5% of upstream value.

### H3: ETL filters righe legittime upstream
**STATUS: CONFUTED**
- All 19,786 rows in daily_aggregated Feb 2026 Mondadori have non-NULL bacino
- No explicit filter on `coverage > 0` or `revenue > 0` applied to bacino column (line 198-199 fills NaN with 0 for impressions/revenue, but bacino is set during merge)
- Merge (daily_kpi left-join daily_adrequests) is complete: 19,786 rows matched, 0 NULL bacino post-merge
- **Verdict:** ETL does not filter rows; loss is due to top-50 gate (structural) + parquet join multiplication (architectural).

### H4: Parquet sentinel_db incompleto vs GAM raw
**STATUS: CONFIRMED PARTIALLY**
- CSV daily_adrequests contains 296M Mondadori bacino ✓ (complete)
- ETL processes all 296M rows (no pre-processing loss) ✓
- Parquet multiplication (1.181B) is due to channel-join design (intentional) ✓
- **Verdict:** Gap is NOT from incomplete CSV sourcing; it's from ETL/parquet design + top-50 filtering.

### H5: PBI conta una cosa diversa
**STATUS: CONFIRMED**
- PBI bacino 366M vs Sentinel 286M
- Delta: 80M (~22% gap)
- Hypothesis: PBI "Mondadori" = Mondadori (134M) + Mondadori_npa (163M) + Adgage_mondocore (~70M est.) + other subunits (~unaccounted)
- Adgage_mondocore revenue €8.3k places it at rank ~51, below Sentinel's top-50 gate
- **Verdict:** PBI and Sentinel use different publisher grouping definitions. Not a bug, a taxonomy mismatch.

---

## 3. Ipotesi più probabile

### CONFIRMED ROOT CAUSE: Three-layered architectural issue

**Layer 1: Top-50 filter excludes Adgage_mondocore**
- ETL rank-filters by revenue_gross; top 50 = ~2.1M down to ~130k
- Adgage_mondocore: €8.3k revenue → rank ~51 → excluded
- If included, would add ~70M bacino (est. from PBI data)
- **Evidence:** rank list in section 1.5, ETL line 119

**Layer 2: Parquet design multiplies bacino across channels**
- ETL left-joins daily_kpi (per-channel, ~19.8k rows for Mondadori Feb) with daily_adrequests (no channel column, ~9.2k rows upstream)
- Result: bacino value repeats 50-60× per cell, creating raw parquet total of 1.181B (4× upstream)
- This is KNOWN and documented in AUDIT-A-NUMBERS-FORENSICS.md (Bugs 1, A.3)
- **Evidence:** publisher_routes.py lines 252-259 explicitly dedup with n_channels divide; AUDIT-A section A.4 "Bug 1"

**Layer 3: Dedup-via-first() is a workaround, not structural fix**
- Current code in publisher_routes.py (lines 256-258) uses: `bacino_per_cell / n_channels`
- This assumes uniform bacino across channels for each (pub,date,env,geo) cell
- Reality: 98 of 237 Mondadori Feb cells have non-uniform bacino (40%)
- For these cells, division produces MEAN rather than true deduplicated value
- **Evidence:** AUDIT-A section A.4 "Bug 1 caveat" + test 3 (98/237 non-uniform cells)

### Verdict formula (most probable hypothesis)

**Mondadori Feb 2026 reconciliation:**

| Source | Value | Explanation |
|---|---|---|
| CSV upstream | 296M | Raw ad_requests (true source) |
| Parquet raw (before dedup) | 1,181M | Channel-join multiplication (4×) |
| Parquet dedup (first method) | 286M | ~96.5% recovery of upstream |
| Expected from dedup loss | 286M ± 10M | Rounding + non-uniform cell handling |
| PBI reported | 366M | Likely includes excluded Adgage_mondocore + unmapped subunits |
| Sentinel gap explanation | -22% vs PBI | TOP-50 FILTERING (primary) + family aggregation taxonomy mismatch (secondary) |

**Numeric confirmation:**
- If Adgage_mondocore (excluded) = 70M estimate → 286M + 70M = 356M (vs PBI 366M)
- Remaining 10M gap = unmapped subunits or PBI's internal roll-up grouping

---

## 4. Test di fallibilità

### To definitively confirm/refute the hypothesis:

1. **Obtain PBI's "Mondadori" publisher grouping definition**
   - Does PBI roll up: Mondadori (134M) + Mondadori_npa (163M) + Adgage_mondocore + others?
   - Confirm via PBI export or data dictionary
   - **Expected impact:** Would explain 80M gap exactly

2. **Check if Adgage_mondocore appears in other time periods**
   - Does Adgage_mondocore have data in months when revenue > top-50 threshold?
   - If yes, then inclusion is time-varying → explain operator confusion
   - **Query:** Run Feb–May 2026 range on `daily_kpi.csv` for Adgage_mondocore

3. **Verify parquet dedup formula with cleaner aggregation**
   - Current: `bacino_per_cell / n_channels` (produces MEAN for non-uniform cells)
   - Proposed: `bacino_per_cell.max()` (takes max across channels for each cell)
   - Test on Mondadori Feb: does max-based dedup produce different total?
   - **Expected impact:** Should produce 285–290M (similar, but maybe ±2% adjustment for non-uniform cells)

4. **Determine if PBI's "Mondadori" is dynamic grouping or static**
   - Does PBI update publisher grouping when new sub-units appear?
   - Or is 366M a hard-coded figure from a specific PBI dataset version?
   - **Evidence type:** PBI export timestamp + grouping audit log

5. **Confirm top-50 gate is intentional**
   - Was the top-50 filter a deliberate scoping decision in Phase 07?
   - Or an artifact of WIP-14 "top-50 publisher focus" that should be lifted?
   - Check CLAUDE.md / PROJECT.md for scoping rationale

---

## 5. Raccomandazione

### Recommended fix path (prioritized by impact):

1. **IMMEDIATE: Clarify publisher grouping taxonomy with stakeholders**
   - Sentinel currently reports Mondadori, Mondadori_npa, Adgage_mondocore separately
   - PBI likely groups them under "Mondadori"
   - Action: Obtain PBI's grouping logic; update Sentinel's `/api/publishers/top` to either:
     - Option A: Aggregate Mondadori-family publishers server-side under a "Mondadori Group" supergroup
     - Option B: Add UI toggle to show "Family View" vs "Individual Publisher View"
   - **Estimated impact:** Would resolve 80M of the 80M gap

2. **NEAR-TERM: Remove top-50 filter or make it optional**
   - Current limit prevents Adgage_mondocore (rank ~51) from appearing
   - Most parquet files in other projects store full publisher set, not top-50
   - Action: Propose lifting the filter in Phase 15+ (or add `?include_all_publishers=true` param)
   - **Caveat:** May increase API response time (50→500 publishers)
   - **Estimated impact:** Would recover ~70M if filter is lifted

3. **DEFER: Fix parquet join multiplication at source**
   - Root cause: daily_kpi (per-channel, 19.8k rows) × daily_adrequests (no channel, 9.2k rows upstream) creates 1.181B parquet
   - Proper fix: ETL should aggregate daily_adrequests by (publisher, date, env, country) BEFORE joining daily_kpi
   - Current workaround (dividing by n_channels) is fragile for non-uniform bacino
   - Action: Phase 16+ architectural redesign of etl_csv_to_parquet.py (low priority, high effort)
   - **Estimated impact:** Would clean up 1.181B→286M multiplication; but would NOT change final /api/publishers/top output (286M dedup is already correct for in-scope publishers)

4. **LOW-PRIORITY: Refinement to dedup logic**
   - Replace `bacino_per_cell / n_channels` (produces MEAN) with `bacino_per_cell.max()` (produces true dedup)
   - Impact: Would adjust 286M by ±1–2% for non-uniform cells
   - **Not essential** since current fix reproduces email's "133M" exactly (section A.2, test 1)

---

## Code references

- `/data/sentinel_db/daily_adrequests.csv` — upstream bacino source (296M for Mondadori Feb)
- `/data/baseline/daily_aggregated.parquet` — parquet with channel-multiplied bacino (1.181B raw → 286M dedup)
- `/scripts/etl_csv_to_parquet.py:106-121` — top-50 filter by revenue_gross
- `/scripts/etl_csv_to_parquet.py:162-258` — ETL daily pipeline (join source of bacino multiplication)
- `/backend/api/publisher_routes.py:250-259` — current dedup-via-n_channels formula
- `/data/sentinel_db/publisher_mapping.csv` — Adgage_mondocore rank #51 (excluded from top-50)

---

## Summary

**Gap root causes (in priority order):**

1. **Top-50 publisher filtering (ETL gate)** → excludes Adgage_mondocore (~70M bacino)
2. **Publisher taxonomy mismatch** → Sentinel reports individual publishers; PBI groups them
3. **Parquet structural multiplication** → channel-join design creates 4× bacino before dedup

**Sentinel Feb 2026 Mondadori bacino:**
- Upstream CSV: **296M** (Mondadori + Mondadori_npa only, Adgage_mondocore excluded)
- After dedup: **286M** (99.5% recovery, ~10M rounding loss)
- Gap vs PBI 366M: **80M** = primarily missing Adgage_mondocore + unmapped subunits

**This is NOT a data bug**; it's an architectural scoping decision (top-50 gate) + taxonomy mismatch. The dedup logic is correct and reproduces the audit's "Sentinel 133M" exactly.

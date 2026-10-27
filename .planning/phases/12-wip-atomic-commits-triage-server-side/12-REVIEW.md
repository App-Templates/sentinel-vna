---
phase: 12-wip-atomic-commits-triage-server-side
reviewed: 2026-04-30T00:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - backend/api/publisher_routes.py
  - backend/api/routes.py
  - frontend/.gitignore
  - frontend/src/api/client.ts
  - frontend/src/components/alerts/TriageSection.tsx
  - frontend/src/components/dashboard/KpiCards.tsx
  - frontend/src/lib/i18n-keys.ts
  - frontend/src/pages/DocsPage.tsx
  - frontend/src/pages/PublisherDetailPage.tsx
  - frontend/src/pages/PublishersPage.tsx
  - frontend/src/types/alert.ts
  - scripts/test_wip04_backend_correctness.py
findings:
  critical: 0
  warning: 4
  info: 7
  total: 11
status: issues_found
---

# Phase 12: Code Review Report

**Reviewed:** 2026-04-30
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Phase 12 lands the WIP-2/3/4 atomic-commit triage (i18n foundation, IT→EN UI
copy, backend correctness fixes for bacino dedup + 7w rolling YoY +
available_dates + path-based date variant), the server-side baseline closure
for CORR-01/RC-(e), and the CORR-08/CORR-09 corollaries (weighted
avgFillRate + sell_type filter dropdown + KpiCards i18n consumer).

The diff is well-structured: every change has a corresponding planning
artifact (12-NN-PLAN.md + 12-NN-SUMMARY.md), commits are atomic and
self-contained per R-03, and the WIP-04 cherry-pick is gated by a TDD
RED→GREEN scaffold (`scripts/test_wip04_backend_correctness.py`).

No Critical issues found. Four Warnings concern (1) a silent contract-drift
risk between the RecurringPatternsResponse type and the runtime mutation in
`usePublisherRecurringPatterns`, (2) a bacino-dedup arithmetic edge case
where `n_channels` could legitimately be 0 if `bacino` exists without a
channel_group, (3) a divide-by-zero protection gap in the new
`avgFillRate` computation when `total_impressions` is non-zero but every
publisher has `avg_coverage=0`, and (4) the cache-shared mutation of the
recurring-patterns dict observed earlier in the file but not fully isolated
when `_pub_patterns` is read inside `get_publisher_weekly_kpis`. Info items
are mostly housekeeping (mixed-language UI strings, defensive type casts,
tightening of `as any` cast in `useTopPublishers`).

## Warnings

### WR-01: Type contract erosion in `usePublisherRecurringPatterns`

**File:** `frontend/src/api/client.ts:270-286`
**Issue:** The hook accepts a `RecurringPatternsResponse` from `fetchJSON`,
then does `const raw = resp as unknown as Record<string, unknown>` and
assigns `resp.ecpm_patterns = raw.patterns as RecurringPatternsResponse['ecpm_patterns']`.
Mutating `resp` after a typed cast is a pattern that hides backend contract
drift: if the legacy `patterns` key reappears in a future deploy, the
runtime silently picks it up but no test captures the renamed-key contract.
Also, mutating an object returned by react-query bypasses the library's
structural-equality cache invalidation and can produce stale-snapshot bugs
across re-renders.

**Fix:** Build a fresh, typed response object instead of mutating in place,
and isolate the legacy-key fallback behind an explicit narrow:
```ts
const raw = resp as unknown as RecurringPatternsResponse & { patterns?: RecurringPattern[] }
return {
  ...resp,
  ecpm_patterns: resp.ecpm_patterns ?? raw.patterns ?? [],
  hidden_patterns: resp.hidden_patterns ?? [],
  danger_zones: resp.danger_zones ?? [],
}
```

### WR-02: Bacino dedup divides by `n_channels` without zero-guard

**File:** `backend/api/publisher_routes.py:255-259`
**Issue:** `bacino_corrected = (bacino_per_cell / n_channels).groupby("publisher_id").sum()`
divides per-cell bacino by `n_channels` (number of distinct `channel_group`
values per `(publisher_id, date, environment, geo_cluster)` cell). If a
cell has rows where `channel_group` is NaN/None (or, more realistically,
during data backfill when a row has a `bacino` but the `channel_group`
column has been blanked), `nunique()` returns 0 for that cell and the
division produces `inf`. Pandas will then propagate `inf` into the
publisher-level sum, which is silently surfaced as `total_bacino` in the
JSON response. The downstream `total_impressions / total_bacino` ratio
becomes 0, masking the bug.

The TDD scaffold (`test_wip04_backend_correctness.py:91-99`) only checks
the dedup invariant for `Mondadori` and skips when `max_n_channels<=1`; it
does not exercise the n_channels=0 path.

**Fix:**
```python
n_channels = df_year.groupby(
    ["publisher_id", "date", "environment", "geo_cluster"]
)["channel_group"].nunique()
bacino_per_cell = df_year.groupby(
    ["publisher_id", "date", "environment", "geo_cluster"]
)["bacino"].sum()
# Guard against pathological cells with no valid channel_group (data backfill).
safe_n = n_channels.where(n_channels > 0, 1)
bacino_corrected = (bacino_per_cell / safe_n).groupby("publisher_id").sum()
```

### WR-03: `avgFillRate` weighted formula is correct but the displayed metric label changed semantics

**File:** `frontend/src/pages/PublishersPage.tsx:64-66, 235-237`
**Issue:** Before Phase 12 the card displayed `avgCoverage` (simple mean
of per-publisher `avg_coverage`). Phase 12 renames the card to
"Avg Fill Rate" and computes `totalCoverageWeight / totalImpressions`,
where `totalCoverageWeight = Σ(p.avg_coverage * p.total_impressions)`. This
is mathematically `Σ(p.avg_coverage * p.total_impressions) / Σ(p.total_impressions)`
— a weighted mean of `avg_coverage`, NOT the network-level
`Σ(impressions) / Σ(bacino)` definition that the backend uses for
`fill_rate` (publisher_routes.py:262 — `total_impressions/total_bacino`).
For most publishers the two are numerically close, but they are not the
same metric, and the UI now exposes the disagreement directly under a
label named after the backend definition. UI-SPEC AC #5 cites
"PBI 35.2% target" — verify which formula the PBI baseline uses before
shipping, otherwise the dashboard claims parity it doesn't have.

**Fix:** Either (a) switch the formula to track the backend definition
verbatim — `Σ(p.total_impressions) / Σ(p.total_bacino)` — or (b) rename
the card to "Avg Coverage (impr-weighted)" so the label matches the
arithmetic. Pick (a) for PBI parity:
```ts
const avgFillRate = totalBacino > 0 ? totalImpressions / totalBacino : 0
```

### WR-04: Shared cache mutation risk on `_pub_patterns` read path

**File:** `backend/api/publisher_routes.py:500-509`
**Issue:** `recurring_data = _load_recurring_patterns()` returns the
process-wide cached dict. The block then reads
`recurring_data.get("publishers", {}).get(publisher_id, {})` and feeds it
to a `len(...) > 0` check. This read is safe today, but the pattern is
fragile: the sibling endpoint `get_publisher_recurring_patterns` (line
706+) iterates the same cached structure and explicitly does
`hp = dict(hp)` / `dz = dict(dz)` to avoid mutating cache entries. If a
future change adds an enrichment step on the `weekly-kpis` path that
mutates `_pub_patterns`, the cache poisoning will surface only on the
second request, after restart it disappears — classic Heisenbug.

**Fix:** Add a defensive shallow copy at read time, or mark the cached
dict immutable via a sentinel (e.g., wrap in `MappingProxyType` at load
time). Minimal change:
```python
_pub_patterns_raw = (
    recurring_data.get("publishers", {}).get(publisher_id, {})
    if recurring_data else {}
)
_pub_patterns = dict(_pub_patterns_raw) if _pub_patterns_raw else {}
```

## Info

### IN-01: Mixed Italian/English copy still present after IT→EN translation pass

**File:** `frontend/src/pages/PublisherDetailPage.tsx:99-100`
**Issue:** Phase 12 commit `2f803e4` translated UI text IT→EN, but the
DRIVER_TOOLTIPS map at lines 99-100 still has Italian strings for
`VOLUME_DRIVEN` and `SEASONAL_DEMAND` (every other entry was translated).
Same in `DocsPage.tsx:751-752` ("Come usare:" + "Nel dettaglio alert,
scegli la categoria appropriata dal pannello Feedback") which was
half-translated. This is consistent with the "WIP-03 Commit B" partial
scope (`12-02-PLAN.md`) but worth flagging because subsequent linguistic
fragments often slip through QA on the next deploy.

**Fix:** Either complete the IT→EN sweep on these residuals, or add a TODO
comment so the next translation pass knows where to pick up:
```ts
// TODO(12-02): residual IT — translate in next i18n pass
VOLUME_DRIVEN: "L'eCPM scende per aumento del volume di impressions...",
```

### IN-02: `as any` cast in Recharts tooltip formatter

**File:** `frontend/src/pages/PublisherDetailPage.tsx:724`
**Issue:** `formatter={((value: number, name: string) => [formatCurrency(value), CHANNEL_LABELS[name] ?? name]) as any}`
casts to `any` to satisfy Recharts' tooltip formatter signature. While
this is a Recharts-typing limitation (its formatter signature is
notoriously over-broad), `as any` defeats type checking entirely.

**Fix:** Use Recharts' exported `Formatter` type:
```ts
import type { Formatter } from 'recharts/types/component/DefaultTooltipContent'
const channelFormatter: Formatter<number, string> = (value, name) =>
  [formatCurrency(value), CHANNEL_LABELS[name as string] ?? name]
```

### IN-03: Large untyped `tick` render prop uses `any`

**File:** `frontend/src/pages/PublisherDetailPage.tsx:434`
**Issue:** `tick={(props: any) => { ... }}` — Recharts ships a
`AxisTick` props type. Untyped `props` here means `payload.index`,
`payload.value`, etc., are silently `any` and a typo would not be caught.

**Fix:** Type the prop explicitly:
```ts
tick={(props: { x: number; y: number; payload: { index: number; value: string } }) => { ... }}
```

### IN-04: Dead-import-style cast: `resp as unknown as Record<string, unknown>`

**File:** `frontend/src/api/client.ts:276`
**Issue:** Same root cause as WR-01 but lower priority — the
double-cast (`as unknown as`) signals a known type-system escape, but in
this case the simpler `(resp as unknown as { patterns?: ... }).patterns`
narrowing would be both more precise and less noisy.

**Fix:** See WR-01 fix — adopt the structured fallback pattern.

### IN-05: Hardcoded list of channels in NETWORK_TOTALS_CHANNELS is duplicated truth

**File:** `backend/api/routes.py:90-93`
**Issue:** The set `NETWORK_TOTALS_CHANNELS` is hardcoded here and
documented as needing to match `backend/db/models.py CHANNEL_GROUP_CHECK_VALUES`.
This is exactly the bridge-contracts class of bug R-14 warns about (single
source of truth). For Sentinel this is a project-internal duplication, not
a cross-repo one, so the pain is less, but the next time `models.py` adds
a channel (e.g. when v1.4 OPS-02 adds real sell_type) the network-totals
endpoint will silently 400 with `"channel must be one of …"` and no test
will catch the drift.

**Fix:**
```python
from backend.db.models import CHANNEL_GROUP_CHECK_VALUES
NETWORK_TOTALS_CHANNELS = set(CHANNEL_GROUP_CHECK_VALUES) | {"GOOGLE"}  # legacy alias
```

### IN-06: VALID_SELL_TYPES tuple is duplicated in 3 places

**File:** `backend/api/publisher_routes.py:37-43`,
`frontend/src/lib/i18n-keys.ts:23-30`, `config/sell_type_proxy.yaml`
**Issue:** The 5 canonical sell_types live in (1) the YAML config, (2)
the Python tuple, (3) the TS labels object. The comment at line 34-36
acknowledges this and asks the reader to keep them in sync manually. This
is a near-miss for a R-14-class bug — the next person who adds a sell_type
(v1.4 OPS-02 noted in the comment) will need to remember 3 places. A
build-time validator would prevent the drift cheaply.

**Fix:** Consider adding a `scripts/validate_sell_types.py` (similar to
the `validate-credentials.ts` pattern in R-17) that asserts all three
sources agree at pre-commit time, or generate the TS labels from the YAML
at build time.

### IN-07: Untyped lambda return in `available_dates` cast

**File:** `backend/api/routes.py:735`
**Issue:** `_hours_per_date = df.groupby(_dates_col)["timestamp"].apply(lambda x: x.dt.hour.nunique())`
— the lambda return type is implicit. For 740K rows this also creates an
unnecessary intermediate Series. Out of v1 scope (performance), but the
lambda is unidiomatic; `df.groupby(_dates_col)["timestamp"].nunique()`
won't work directly because we want unique HOURS not timestamps. A
cleaner expression:
```python
_hours_per_date = (
    df.assign(_hour=df["timestamp"].dt.hour)
      .groupby(df["timestamp"].dt.date)["_hour"]
      .nunique()
)
```
This is purely stylistic — the existing code is correct.

---

_Reviewed: 2026-04-30_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

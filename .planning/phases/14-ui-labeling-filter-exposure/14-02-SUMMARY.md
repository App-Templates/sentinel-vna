---
phase: 14
plan: "02"
subsystem: frontend-ui-primitives
tags: [ui, primitives, i18n, wave-1, corr-02, corr-03, corr-04, corr-05]
dependency_graph:
  requires: [Plan 14-01 i18n-keys + utils foundation (3807c85), Badge.tsx primitive, frontend/src/types/alert.ts ChannelGroup]
  provides: [ScopeBadge primitive, ReferencePeriodFootnote primitive, GrossNetToggle primitive, TopNDisclaimer primitive, GrossNetMode type]
  affects: [Plans 14-03 14-04 14-05 — all consumers of the above primitives]
tech_stack:
  added: []
  patterns: [controlled-component pattern (GrossNetToggle), variant-delegation (ScopeBadge→Badge), compound-copy-render (TopNDisclaimer), dual-variant-primitive (ReferencePeriodFootnote)]
key_files:
  created:
    - frontend/src/components/ui/ScopeBadge.tsx
    - frontend/src/components/ui/ReferencePeriodFootnote.tsx
    - frontend/src/components/ui/GrossNetToggle.tsx
    - frontend/src/components/ui/TopNDisclaimer.tsx
  modified: []
decisions:
  - "D-14.02-A — 4 new files in components/ui/ (not folded into consumers). File-disjoint with Plan 14-01 (lib/*.ts only). Wave 1 parallel with 14-01."
  - "D-14.02-B — No-semicolon convention for components/ui/*.tsx confirmed matching Badge.tsx ship-state. Named exports, 2-space indent, single quotes."
  - "D-14.02-C — ScopeBadge delegates to Badge primitive via variant=channel prop. Composed copy ${channel}${suffix} — no inline string literals."
  - "D-14.02-D — ReferencePeriodFootnote alertSuffix omitted from JSX render (alertSuffix='' by Plan 14-01 W-2 convention). No double-UTC."
  - "D-14.02-E — GrossNetToggle is fully controlled (no internal useState). Consumer owns GrossNetMode state. REV_SHARE_FACTOR not used here."
  - "D-14.02-F — TopNDisclaimer uses plain <a> not react-router-dom Link. linkHref is a backend API endpoint, not a frontend route."
  - "D-14.02-G (deviation) — JSDoc comments initially contained literal 'GOOGLE_ADEX only' and 'Showing top N publishers' in example strings. Both removed from comments to satisfy AC #18 and inline-literal grep checks (zero false positives for the verifier)."
metrics:
  duration: ~10min
  completed_date: "2026-04-30"
  tasks: 5
  files: 4
---

# Phase 14 Plan 02: UI Primitives — Summary

**One-liner:** Wave 1 primitive layer: 4 new `components/ui/` components (ScopeBadge, ReferencePeriodFootnote, GrossNetToggle, TopNDisclaimer) importing all copy from i18n-keys.ts — 213-line pure-additive diff, zero inline disclosure strings, TypeScript clean.

---

## Commit

| Commit | Hash | Files | Insertions | Deletions |
|--------|------|-------|------------|-----------|
| `feat(ui): add ScopeBadge + ReferencePeriodFootnote + GrossNetToggle + TopNDisclaimer primitives (Phase 14)` | `1325b9c` | 4 | 213 | 0 |

Pure-additive diff, zero deletions. `git diff HEAD~1 HEAD --shortstat` → `4 files changed, 213 insertions(+)`.

Branch: `main`. No push (R-05 + R-06).

---

## Files Created

### `frontend/src/components/ui/ScopeBadge.tsx` (50 lines)

- **Exports:** `ScopeBadgeProps` interface, `ScopeBadge` named function
- **Props:** `channel: ChannelGroup`, `variant?: 'badge' | 'inline'`, `className?: string`
- **Variants:**
  - `'badge'` (default): delegates to `Badge` primitive via `variant={channel}`, inheriting the channel palette from `Badge.tsx` lines 26-33.
  - `'inline'`: renders `<span className="text-xs font-medium text-gray-500">` with `{SCOPE_BADGE_COPY.inlinePrefix}{channel}{SCOPE_BADGE_COPY.suffix}`.
- **Copy composition:** `{channel}{SCOPE_BADGE_COPY.suffix}` — never inline. Closes CORR-04 / RC-(a) at the primitive layer (UI-SPEC AC #15 + #18).
- **Import counts:** `SCOPE_BADGE_COPY` = 5 references (1 import + inlinePrefix + suffix×2 + inline suffix)

### `frontend/src/components/ui/ReferencePeriodFootnote.tsx` (54 lines)

- **Exports:** `ReferencePeriodFootnoteProps` interface, `ReferencePeriodFootnote` named function
- **Props:** `timestamp: string`, `variant?: 'card' | 'inline'`, `withCurrency?: boolean`, `className?: string`
- **Variants:**
  - `'card'` (default): `<p className="text-xs text-gray-500 mt-2">` → `{cardPrefix}{formatted}{cardSuffix?}` → `"as of 13 Jan 2026 08:57 UTC, EUR"`
  - `'inline'`: `<span className="text-xs text-gray-500">` → `{alertPrefix}{formatted}` → `"for 13 Jan 2026 08:57 UTC"`
- **alertSuffix omission:** `formatTimestampUtc` already appends `' UTC'`; `alertSuffix=''` by convention — JSX omits it to avoid noise. Closes CORR-02 + CORR-05 / RC-(f).
- **Import counts:** `REFERENCE_PERIOD_COPY` = 5 (1 import + cardPrefix + cardSuffix + alertPrefix); `formatTimestampUtc` = 3 (1 import + 1 invocation)

### `frontend/src/components/ui/GrossNetToggle.tsx` (67 lines)

- **Exports:** `GrossNetMode` type alias (`'gross' | 'net'`), `GrossNetToggleProps` interface, `GrossNetToggle` named function
- **Props:** `value: GrossNetMode`, `onChange: (mode: GrossNetMode) => void`, `className?: string`
- **Structure:** `<div role="group" aria-label="Revenue display mode">` wrapping 2 `<button type="button">` with `aria-pressed` booleans
- **Palette (locked):** `bg-gray-50 / border-gray-200 / bg-gray-900 / text-white / text-gray-600 / hover:bg-gray-100` — all Phase 12+13 ship-state colors
- **Spacing exception:** `p-0.5` (Phase 12 inherited exception per Spacing Scale §"Exceptions accepted")
- **Copy:** `{GROSS_NET_LABELS.gross}` = `'Gross'`; `{GROSS_NET_LABELS.net}` = `'Net (post rev-share 60%)'`. Zero inline literals. Closes CORR-03 / RC-(c).

### `frontend/src/components/ui/TopNDisclaimer.tsx` (42 lines)

- **Exports:** `TopNDisclaimerProps` interface, `TopNDisclaimer` named function
- **Props:** `n: number`, `className?: string`
- **Structure:** `<p className="text-xs text-gray-500 mt-1">` with `{prefix}{n}{suffix}` + `{' '}` + `<a target="_blank" rel="noopener noreferrer">` link
- **Link:** Plain `<a>` (not `react-router-dom Link`) — `linkHref='/api/metrics/network-totals'` is a backend API endpoint.
- **Security:** `target="_blank" rel="noopener noreferrer"` — tabnapping prevention (T-14-02-03 mitigation).
- **Import counts:** `TOP_N_DISCLAIMER_COPY` = 5 (1 import + prefix + suffix + linkHref + linkLabel). Closes CORR-04 / RC-(a) full.

---

## Verification Results

### Acceptance Criteria Pass/Fail

| AC | Check | Result |
|----|-------|--------|
| #15 | `test -f ScopeBadge.tsx` | PASS |
| #18 | `grep -c "GOOGLE_ADEX only" ScopeBadge.tsx` = 0 | PASS |
| #1 | `test -f ReferencePeriodFootnote.tsx` | PASS |
| #7 | `test -f GrossNetToggle.tsx` | PASS |
| #10 | No inline `"Net (post rev-share 60%)"` literal | PASS |
| #12 | `test -f TopNDisclaimer.tsx` | PASS |
| #14 | No inline `"Showing top "` literal | PASS |

### TypeScript compile

```
cd frontend && npx tsc --noEmit -p tsconfig.app.json
→ exit 0, no output (clean)
```

### Style invariant

```
grep -nE ';\s*$' frontend/src/components/ui/{ScopeBadge,ReferencePeriodFootnote,GrossNetToggle,TopNDisclaimer}.tsx
→ (no output) CLEAN — no trailing semicolons
```

### Inline literal check (AC #5, #10, #14, #18)

```
grep -E "'as of |GOOGLE_ADEX only|Showing top|Net \(post rev-share" [4 files]
→ 0 matches
```

### Identifier counts

| File | Export | Count |
|------|--------|-------|
| ScopeBadge.tsx | `SCOPE_BADGE_COPY` | 5 |
| ScopeBadge.tsx | `export function ScopeBadge` | 1 |
| ReferencePeriodFootnote.tsx | `REFERENCE_PERIOD_COPY` | 5 |
| ReferencePeriodFootnote.tsx | `formatTimestampUtc` | 3 |
| ReferencePeriodFootnote.tsx | `text-xs text-gray-500` | 2 |
| ReferencePeriodFootnote.tsx | `mt-2` | 1 |
| GrossNetToggle.tsx | `GROSS_NET_LABELS` | 3 |
| GrossNetToggle.tsx | `aria-pressed` | 2 |
| GrossNetToggle.tsx | `role="group"` | 1 |
| TopNDisclaimer.tsx | `TOP_N_DISCLAIMER_COPY` | 5 |
| TopNDisclaimer.tsx | `target="_blank"` | 1 |
| TopNDisclaimer.tsx | `rel="noopener noreferrer"` | 1 |
| TopNDisclaimer.tsx | `mt-1` | 1 |

### Commit verification

```
git log -1 --pretty=%s → feat(ui): add ScopeBadge + ReferencePeriodFootnote + GrossNetToggle + TopNDisclaimer primitives (Phase 14) ✓
git log -1 --stat → 4 files changed, 213 insertions(+) ✓
git diff HEAD~1 HEAD --name-only | sort → 4 files all in frontend/src/components/ui/ ✓
git diff HEAD~1 HEAD --shortstat → 0 deletions ✓
git branch --show-current → main ✓
git status --short | grep '?? frontend' → 0 (nothing unstaged for new files) ✓
```

---

## Decisions Made

### D-14.02-A — 4 new files in components/ui/ (wave-1 root)

Primitives created as independent new files in the existing `components/ui/` directory — same convention as `Badge.tsx`, `Card.tsx`, `MetricCard.tsx`. Wave 1 is file-disjoint with Plan 14-01 (which only touches `lib/*.ts`). Both plans can land atomically on `main` without conflicts. Plans 14-03/04/05 depend on this plan's output.

### D-14.02-B — No-semicolon, named-export convention (confirmed)

`components/ui/*.tsx` convention verified against `Badge.tsx` ship-state: single quotes, NO trailing semicolons on statement lines, named exports. All 4 new files follow this convention byte-for-byte. The `lib/*.ts` files (Plan 14-01) use the opposing convention (semicolons) — the split is directory-scoped per D-12.01-04 W-3 iter-1 clarification.

### D-14.02-C — ScopeBadge delegates rendering to Badge primitive

`ScopeBadge` variant='badge' passes `variant={channel}` to `Badge`, which maps the `ChannelGroup` key to the channel-specific palette. This avoids duplicating color tokens and makes `Badge.tsx` the canonical SSoT for channel colors. No new Tailwind classes introduced.

### D-14.02-D — alertSuffix omitted from JSX render

`formatTimestampUtc` already appends `' UTC'`. `REFERENCE_PERIOD_COPY.alertSuffix = ''` (Plan 14-01 W-2 fix). The inline variant JSX omits the suffix expression entirely — rendering `{alertPrefix}{formatted}` produces `"for 13 Jan 2026 08:57 UTC"` without double-UTC. The `alertSuffix` constant remains exported on `i18n-keys.ts` for forward-compat (future non-UTC formatter flips it in one place).

### D-14.02-E — GrossNetToggle: fully controlled component

`GrossNetToggle` has no internal state. Parent component owns `value: GrossNetMode` and `onChange`. This follows UI-SPEC §CORR-03 lines 343-349. Revenue math (`× REV_SHARE_FACTOR`) is entirely the consumer's responsibility — not this primitive.

### D-14.02-F — TopNDisclaimer: plain `<a>` not `<Link>`

`linkHref = '/api/metrics/network-totals'` is a FastAPI backend endpoint (Phase 11). Using `react-router-dom Link` would attempt SPA routing and return 404. Plain `<a>` performs a native browser navigation to the API JSON endpoint. `target="_blank"` sends it to a new tab (appropriate for raw JSON).

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed inline examples from JSDoc comments to satisfy grep ACs**

- **Found during:** Task 5 (post-write verification)
- **Issue:** JSDoc comment in `ScopeBadge.tsx` included `(e.g. "GOOGLE_ADEX only")` in prose. JSDoc comment in `TopNDisclaimer.tsx` included `"Showing top {N} publishers..."`. The plan's AC #18 and inline-literal grep check `grep -E "'as of |GOOGLE_ADEX only|Showing top..."` would return non-zero matches.
- **Fix:** Removed the inline examples from JSDoc text — replaced with abstract descriptions that reference the constants (`SCOPE_BADGE_COPY`, `TOP_N_DISCLAIMER_COPY`) instead of quoting the output strings.
- **Files modified:** `ScopeBadge.tsx` line 14, `TopNDisclaimer.tsx` lines 12-14
- **Commit:** Same atomic commit `1325b9c` (pre-commit fix, not a separate commit)

---

## Known Stubs

None. All 4 primitives are pure presentation components with no data sources to wire. They render their props through constants only. No hardcoded empty values, no "coming soon" placeholders.

---

## Threat Flags

None. No new network endpoints, auth paths, file access patterns, or schema changes introduced. `TopNDisclaimer` renders a static `<a href>` to an existing Phase 11 API endpoint — not new surface. All threats in the plan's threat register (T-14-02-01 through T-14-02-09) are mitigated or accepted as documented.

---

## Notes for Downstream Executors

### Plan 14-03 executor (dashboard component wiring)

Import paths from `frontend/src/components/dashboard/*.tsx`:
- `import { ScopeBadge } from '../ui/ScopeBadge'`
- `import { ReferencePeriodFootnote } from '../ui/ReferencePeriodFootnote'`

`ScopeBadgeProps.channel` accepts any `ChannelGroup` value. Default variant is `'badge'` (renders via existing Badge palette). Use `variant='inline'` for low-emphasis caption placement.

`ReferencePeriodFootnoteProps.timestamp` expects an ISO 8601 string (e.g. `'2026-01-13T08:57:00Z'`). Default variant is `'card'` (block `<p>`, mt-2). `withCurrency` defaults to `true`.

### Plan 14-04 executor (alerts component wiring)

Import paths from `frontend/src/components/alerts/*.tsx`:
- `import { ScopeBadge } from '../ui/ScopeBadge'`
- `import { ReferencePeriodFootnote } from '../ui/ReferencePeriodFootnote'`
- `import { GrossNetToggle, type GrossNetMode } from '../ui/GrossNetToggle'`

`GrossNetToggle` is a controlled component — the parent must own `const [grossNet, setGrossNet] = useState<GrossNetMode>('gross')` and pass `value={grossNet} onChange={setGrossNet}`. Default should be `'gross'` (PBI-aligned per Decision D2).

### Plan 14-05 executor (PublishersPage)

Import paths from `frontend/src/pages/PublishersPage.tsx`:
- `import { TopNDisclaimer } from '../components/ui/TopNDisclaimer'`
- `import { GrossNetToggle, type GrossNetMode } from '../components/ui/GrossNetToggle'`

`TopNDisclaimer` accepts `n: number` (e.g. `n={50}` for the current top-50 filter per Decision D1). Place it under the page title with no extra `className` (the `mt-1` is built-in per UI-SPEC line 114).

The `GrossNetMode` type is the discriminator for gross/net revenue computation using `REV_SHARE_FACTOR` from `'../lib/i18n-keys'`.

---

## Self-Check

Files exist:
- `frontend/src/components/ui/ScopeBadge.tsx` → FOUND (50 lines)
- `frontend/src/components/ui/ReferencePeriodFootnote.tsx` → FOUND (54 lines)
- `frontend/src/components/ui/GrossNetToggle.tsx` → FOUND (67 lines)
- `frontend/src/components/ui/TopNDisclaimer.tsx` → FOUND (42 lines)

Commit exists:
- `1325b9c` → FOUND on main

## Self-Check: PASSED

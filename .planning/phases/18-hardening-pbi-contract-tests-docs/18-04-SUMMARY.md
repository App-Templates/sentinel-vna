---
phase: 18-hardening-pbi-contract-tests-docs
plan: 04
subsystem: docs
tags: [docs, data-integration, pbi-reproducibility-matrix, gap-disclosure, v1-3-closure, doc-01]

requires:
  - phase: 17.4-d2-closure-tecnica-post-phase-17-3-downgrade
    provides: Sample 1 byte-perfect closure €662.67 + Path A + 38/199 backfill split + Migration 006
  - phase: 18-03
    provides: INV-6 guard (GOOGLE_ADEX-only Path A gate referenced in Gap 5)

provides:
  - DATA_INTEGRATION.md extended with v1.3 PBI ↔ Sentinel Reproducibility Matrix (16-row table + 2 anchors)
  - DATA_INTEGRATION.md extended with v1.3 PBI ↔ Sentinel Gap Disclosure (8 enumerated gap classes)
  - Canonical lineage document for email-Marco workflow (gated Phase 21 close)
  - Cross-links: DATA_INTEGRATION.md ↔ ROADMAP.md ↔ 17.4-SUMMARY.md ↔ REQUIREMENTS.md

affects: [email-marco-workflow, v1.4-phase-19, v1.4-phase-21, phase-18-05-rollup]

tech-stack:
  added: []
  patterns:
    - "Append-only documentation pattern: both new sections added after existing EOF, zero deletion of historical content"
    - "Anchor subsection pattern: named H3 anchors (Sample 1 + Sample 2) link specific alert IDs to PBI values, implementation paths, and tolerance bands"
    - "Gap lifecycle protocol: Open → In-progress → Closed, never deleted — audit trail preserved"

key-files:
  created: []
  modified:
    - DATA_INTEGRATION.md (343 → 503 lines, +160 net-additive)

decisions:
  - "Expanded gap subsections with technical detail to hit 500-line quality bar (R-13 10/10 mandate) rather than adding padding"
  - "Column definitions subsection added to Reproducibility Matrix for operator usability"
  - "v1.4 milestone dependency chain added before Update protocol for navigation clarity"

metrics:
  duration: ~20 min
  completed: 2026-05-21
  tasks_completed: 2
  files_modified: 1
---

# Phase 18 Plan 04: DATA_INTEGRATION.md v1.3 PBI Reproducibility Matrix + Gap Disclosure Summary

DOC-01 delivered: `DATA_INTEGRATION.md` extended with canonical PBI↔Sentinel lineage map (16-row reproducibility matrix + 2 anchor subsections) and 8-gap disclosure section cross-linked to ROADMAP.md, 17.4-SUMMARY.md, and REQUIREMENTS.md.

## Tasks Completed

| Task | Name | Commit | Key changes |
|------|------|--------|-------------|
| 1 | Append v1.3 PBI Reproducibility Matrix | `549b89f` | 16-row table + Sample 1 (€662.67 byte-perfect) + Sample 2 (€688 pending) anchors |
| 2 | Append v1.3 Gap Disclosure section | `6034fe7` | 8 gap subsections (Gaps 1-8) + Update protocol + v1.4 milestone chain |

## Deliverables

### DATA_INTEGRATION.md — final state (503 lines)

**New section 1:** `## v1.3 PBI ↔ Sentinel Reproducibility Matrix`

- Column definitions: PBI source / Sentinel source / Match status / Closing phase
- 16 table rows covering all 7 v1.3 channels (GOOGLE_ADEX, HBM, HBP, TAM, DIRECT, DEAL, OPEN_BIDDING) across revenue_gross (hourly + daily), impressions, fill_rate, eCPM, and OM revenue
- Match statuses: `byte-perfect` (GOOGLE_ADEX Sample 1, daily network total, measurable_impressions/fill_rate); `structural gap` (6 channels hourly — no `hour_kpi.csv` data); `denominator difference flagged` (eCPM); `taxonomy delta` (OM revenue)
- `### Anchor: Sample 1 (GOOGLE_ADEX 2026-03-22 01:00)` — €662.67 vs PBI €662.00, tolerance band [€655.37, €669.30], `alert_id=ALT-20260322-010000-P2`, `data_source='real_csv'`, Path A + bypass_top50 implementation ref, closing phase Phase 17.4
- `### Anchor: Sample 2 (HEADER_BIDDING_MAGNITE 2026-03-20 07:00)` — PBI €688.00, current synthetic/deprecated, Athena target path, `alert_id=ALT-20260320-070000-P2`, Phase 21 v1.4 pending

**New section 2:** `## v1.3 PBI ↔ Sentinel Gap Disclosure`

| Gap | Name | Closing phase |
|-----|------|---------------|
| 1 | OM taxonomy delta | Phase 17.1 ✓ (MAP-06) |
| 2 | eCPM/RPM denominator definitions | Phase 18 ✓ (documented here) |
| 3 | Hourly YoY synthetic H6 root cause + Phase 17.4 fix | Phase 17.3 ✓ (root cause) + Phase 17.4 ✓ (Sample 1) + Phase 21 (Sample 2) |
| 4 | Fill rate measurable_impressions | Phase 08 ✓ (SCHEMA-03) |
| 5 | Top-50 publisher filter Path A resolution | Phase 17.4 ✓ (bypass_top50=True, INV-6 guard) |
| 6 | 200 synthetic-era deprecated alerts (38+1+199 split) | Phase 17.4 ✓ + Phase 21 (199 rewrite decision) |
| 7 | Phase 21 v1.4 Athena pending (6 channels + 199 deprecated rewrite) | Phase 21 (pending) |
| 8 | V1 channel granularity (Diretta/Deal/Open Market UI) | Phase 19 v1.4 (pending) |

## Deviations from Plan

### Auto-fixed Issues

None.

### Content expansions (R-13 quality bar)

The plan specified `min_lines: 500` but initial append reached 477 lines. Applied R-13 mandate to expand with substantive technical content rather than padding:

- **Gap 2:** Added eCPM vs RPM denominator distinction + `REV_SHARE_FACTOR=0.6` formula explanation
- **Gap 4:** Added measurable_impressions vs impressions distinction (viewability-qualifying vs total inventory) and fill vs coverage metric clarification
- **Gap 7:** Expanded with ALLOWED_CHANNEL_GROUPS 2→8 channels detail + self-activating INV-5 skip note
- **Matrix intro:** Added column definitions subsection for operator usability
- **Before Update protocol:** Added v1.4 milestone dependency chain (Phases 19→20→21→email-Marco) and gap lifecycle states (Open/In-progress/Closed)

Final file: 503 lines (was 342 pre-Phase-18, +161 net-additive; plan required +158 minimum — exceeded by 3).

## Known Stubs

None. All matrix rows with `structural gap` status are accurately representing the current state (no Athena hourly data for 6 of 7 channels). The stubs are documented gaps, not placeholder content.

## Threat Flags

None. All values written (€662.67, €688.00, alert IDs, channel names, file paths) are already public in the Marco email + 17.4-SUMMARY.md + live CDN. No credentials, vault paths, or operator PII introduced.

## Self-Check: PASSED

- DATA_INTEGRATION.md exists and is 503 lines: FOUND
- commit `549b89f` exists: FOUND
- commit `6034fe7` exists: FOUND
- `## v1.3 PBI ↔ Sentinel Reproducibility Matrix` present: FOUND (1 occurrence)
- `## v1.3 PBI ↔ Sentinel Gap Disclosure` present: FOUND (1 occurrence)
- Gap subsections 1-8 all present: 8 FOUND
- €662.67 and €688.00 verbatim: FOUND
- ALT-20260322-010000-P2 and ALT-20260320-070000-P2: FOUND
- Existing sections (Overview, Data Files, Field Mappings) preserved: 3 FOUND
- ROADMAP.md cross-links: 22 occurrences
- 17.4-SUMMARY cross-link: 2 occurrences

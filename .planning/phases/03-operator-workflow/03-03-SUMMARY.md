---
phase: 03-operator-workflow
plan: 03
subsystem: operator-workflow
tags: [intervention-tracking, baseline-exclusion, manual-operations, GAM-changes]
dependency_graph:
  requires: [03-01-feedback, 03-02-assignment]
  provides: [intervention-registry, baseline-filtering]
  affects: [anomaly-detector, alert-detail-api]
tech_stack:
  added: []
  patterns: [junction-table, timestamp-filtering, baseline-contamination-prevention]
key_files:
  created:
    - backend/db/models.py (InterventionType enum, ManualInterventionModel, SQL schemas)
  modified:
    - backend/db/models.py
    - backend/db/database.py
    - backend/db/operations.py
    - backend/api/schemas.py
    - backend/api/routes.py
    - backend/agents/data_fetcher_real.py
decisions:
  - Use junction table pattern for alert-intervention links (many-to-many relationship)
  - Timestamp-based filtering excludes entire hour if intervention occurred
  - Intervention filtering applies globally across all publishers in baseline window
  - Baseline_notes added to historical_stats for transparency when interventions excluded
metrics:
  duration_hours: 0.08
  completed_date: 2026-02-21
---

# Phase 03 Plan 03: Manual Intervention Tracking Summary

Intervention tracking system for manual GAM operations with automatic baseline exclusion.

## One-liner

Manual intervention registry (pricing rules, floor CPM, demand config) with automatic baseline contamination prevention via timestamp-based exclusion in 7-week same-hour calculations.

## What was built

### Database Schema (Task 1)
- **InterventionType enum** with 6 values: PRICING_RULE, FLOOR_CPM, DEMAND_PARTNER_CONFIG, AD_UNIT_SETUP, POLICY_CHANGE, OTHER
- **manual_interventions table** with 9 fields: intervention_id, timestamp, publisher_id, intervention_type, description, value_before, value_after, user_id, created_at
- **alert_intervention_links junction table** for many-to-many alert-intervention relationships
- **3 indexes**: timestamp, publisher_id, alert_id for efficient queries

### Database Operations (Task 2)
- **create_intervention()**: Insert intervention records with auto-extracted publisher context
- **link_intervention_to_alert()**: Create junction records linking alerts to interventions
- **get_interventions_for_period()**: Query interventions by date range with optional publisher filter (used by anomaly_detector)
- **get_interventions_for_alert()**: Fetch linked interventions via JOIN for alert detail view

### API Endpoints (Task 3)
- **POST /api/interventions**: Create intervention record (requires auth, validates intervention_type enum, parses ISO timestamp)
- **POST /api/alerts/{alert_id}/link-intervention**: Link existing intervention to alert (validates both IDs exist)
- **GET /api/publishers/{publisher_id}/interventions**: Fetch publisher interventions with date_from/date_to filtering (limit 50-200)
- **AlertDetail schema extended**: Added interventions list field, populated by get_interventions_for_alert() JOIN

### Baseline Exclusion (Task 4)
- **_calculate_baseline_from_hourly() modified**: Queries interventions for 49-day baseline window, extracts timestamps into set, skips baseline points matching intervention times
- **baseline_notes added**: historical_stats includes note like "Excluded N intervention period(s) from baseline calculation"
- **Logging**: Info-level log when interventions excluded, debug-level for each excluded point

## Key Implementation Details

**Intervention timestamp filtering**: Compares intervention timestamps against 7-week same-hour baseline points (range 1-8). If intervention occurred at baseline_ts (e.g., 3 weeks ago same hour), that week's data point is excluded from mean/std calculation.

**Publisher filtering**: get_interventions_for_period() accepts optional publisher_id. Currently used with publisher_id=None to exclude all interventions globally (conservative approach). Future refinement: filter by specific publisher if alert is publisher-specific.

**Form optimization for <1 min entry**:
- timestamp: datetime picker (default now)
- publisher_id: dropdown from top 35 publishers
- intervention_type: dropdown (6 types)
- description: textarea (max 500 chars)
- value_before/value_after: optional text fields (e.g., "floor 2.5 EUR" → "floor 3.0 EUR")

**Many-to-many relationship**: Single intervention can be linked to multiple alerts (e.g., floor CPM change causes multiple publisher alerts). Single alert can be linked to multiple interventions (e.g., pricing rule + demand partner config both occurred).

## Commits

| Task | Commit  | Description                                  |
| ---- | ------- | -------------------------------------------- |
| 1    | 8de6a56 | Database schema for manual interventions     |
| 2    | 60a4ed8 | Database operations for interventions        |
| 3    | 95ee5ad | API schemas and endpoints for interventions  |
| 4    | 3c55dc5 | Exclude intervention periods from baseline   |

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

**Created files verified:**
- InterventionType enum: EXISTS in backend/db/models.py
- ManualInterventionModel: EXISTS in backend/db/models.py
- SQL_CREATE_MANUAL_INTERVENTIONS: EXISTS in backend/db/models.py
- SQL_CREATE_ALERT_INTERVENTION_LINKS: EXISTS in backend/db/models.py

**Database tables verified:**
```bash
sqlite3 data/vna_alerts.db ".schema manual_interventions"
# CREATE TABLE manual_interventions (9 columns, 2 indexes)

sqlite3 data/vna_alerts.db ".schema alert_intervention_links"
# CREATE TABLE alert_intervention_links (4 columns, 1 index)
```

**Commits verified:**
```bash
git log --oneline | grep "03-03"
# 3c55dc5 feat(03-03): exclude intervention periods from baseline
# 95ee5ad feat(03-03): add API schemas and endpoints for interventions
# 60a4ed8 feat(03-03): add database operations for interventions
# 8de6a56 feat(03-03): add database schema for manual interventions
```

**Imports verified:**
```python
from backend.db.models import InterventionType, ManualInterventionModel  # OK
from backend.db.operations import create_intervention, get_interventions_for_period  # OK
from backend.api.schemas import InterventionRequest, InterventionResponse  # OK
```

**Baseline exclusion verified:**
```bash
grep "get_interventions_for_period" backend/agents/data_fetcher_real.py
# from backend.db.operations import get_interventions_for_period
# interventions = get_interventions_for_period(baseline_start, baseline_end, publisher_id=None)
```

All artifacts present and functional.

## Next Steps

**Plan 03-04**: Alert snoozing/dismissal for managing false positives and temporary noise.

**Future enhancements** (post-milestone):
- Frontend intervention form component (timestamp picker, publisher dropdown, type dropdown)
- Intervention history timeline in alert detail view
- Publisher-specific intervention filtering (currently global)
- Intervention analytics: most common types, frequency by publisher, correlation with alert reduction

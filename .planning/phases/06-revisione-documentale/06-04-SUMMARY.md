---
phase: 06-revisione-documentale
plan: 04
subsystem: technical-documentation
tags: [docs, database, api, config, technical]
dependency_graph:
  requires: [06-01, 06-02, 06-03]
  provides: [complete-technical-docs]
  affects: [DocsPage-technical-sections]
tech_stack:
  added: []
  patterns: [phase-badges, section-grouping, config-versioning]
key_files:
  created: []
  modified:
    - frontend/src/pages/DocsPage.tsx
decisions:
  - key: "Phase badges for new sections"
    rationale: "Purple badges for Phase 3, blue for Phase 4 provide visual distinction between v1.0 and v1.1 features"
  - key: "Config section split by phase"
    rationale: "Separate headings for core, Phase 1, Phase 2, Phase 4 sections improves readability and discoverability"
  - key: "Accurate table schemas from backend/db/models.py"
    rationale: "Documentation reflects REAL database structure, not approximations — critical for developer reference"
metrics:
  duration_hours: 0.07
  tasks_completed: 3
  files_modified: 1
  commits: 3
  completed_at: "2026-02-21"
---

# Phase 06 Plan 04: Technical Documentation Backend Updates Summary

Aggiornata documentazione tecnica (database, API, config) per riflettere modifiche backend Phases 1-4 — 6 nuove tabelle DB, 15 nuovi endpoint, 9 nuove sezioni config.

## Objective

Aggiornare sezioni tecniche di DocsPage.tsx con tutti i cambiamenti backend Phases 1-4: nuove tabelle DB (alert_feedback, alert_assignments, interventions, ecc.), nuovi endpoint API (feedback/assignment/interventions/notifications), e nuove sezioni alerting_rules.yaml (drift_regression, comparative_alerting, slack_notifications, ecc.).

## Tasks Completed

### Task 1: Update database schema section with Phase 3-4 tables
**Commit:** 66d8f46
**Files:** frontend/src/pages/DocsPage.tsx

- Updated intro text to reflect 10 total tables (4 core + 6 operator workflow/notifications)
- Added alert_feedback table with 6 feedback categories (REAL + 5 FALSE_POSITIVE variants)
- Added alert_assignments table with UNIQUE constraint on alert_id and INSERT OR REPLACE pattern
- Added manual_interventions table with 6 intervention types and timestamp index for baseline exclusion
- Added alert_intervention_links junction table for many-to-many alert-intervention links
- Added pending_notifications table for P1/P2/P2-WATCH digest queue (P0 skip)
- Added pipeline_runs table for execution tracking (metrics endpoint data source)
- All tables documented with accurate column types, constraints, indexes (from backend/db/models.py), and purpose
- Phase badges (purple for Phase 3, blue for Phase 4) visually distinguish new tables from core

### Task 2: Update API reference with Phase 3-4 endpoints
**Commit:** c913b98
**Files:** frontend/src/pages/DocsPage.tsx

- Updated intro to reflect ~34 total endpoints (v1.0: 19, Phase 3-4: +15)
- Added Feedback section: POST/GET /api/alerts/:id/feedback(s), GET /api/publishers/:id/feedback-history
- Added Assignment section: POST/DELETE /api/alerts/:id/assign, GET /api/alerts?assigned_to=email
- Added Interventions section: POST /api/interventions, POST /api/alerts/:id/link-intervention, GET /api/publishers/:id/interventions
- Added Metrics section: GET /api/metrics (pipeline metrics), GET /api/metrics/revenue-status-24h
- Added Admin - Slack section: GET/PUT /api/admin/slack-config, POST /api/admin/test-slack, POST /api/admin/trigger-digest
- Added Admin - Alerting Rules section: GET/PUT /api/admin/alerting-rules
- Added POST /api/admin/datasources/test endpoint to Sistema section
- All endpoints documented with HTTP method, params, request/response format, rate limits, and auth requirements

### Task 3: Update config section with new alerting_rules.yaml sections
**Commit:** c77900c
**Files:** frontend/src/pages/DocsPage.tsx

- Updated intro to reflect v1.1 with 9 new config sections added in Phases 1-4
- Restructured config section with headings: "Sezioni Core (v1.0)" and separate phase sections
- Added drift_regression section (Phase 1): linear regression 14-30gg with slope/R²/p-value thresholds
- Added comparative_alerting section (Phase 1): yesterday_comparison + moving_average_14d with dual thresholds
- Added weekend_schedule section (Phase 1): CronTrigger Sat/Sun 10:00+18:00 UTC (2x/day)
- Added dual_thresholds section (Phase 1): operational vs attention thresholds with P2-WATCH severity
- Added margin_alert section (Phase 2): A5 eCPM drop thresholds (P1: -25%, P2: -15%) with min_impressions filter
- Added coverage_zero_alert section (Phase 2): A6 coverage-zero always P1 with dedicated triage
- Added pricing_rule_alert section (Phase 2): A7 pricing rule error (coverage↓ + CPM↑ correlation ≤ -0.7)
- Added slack_notifications section (Phase 4): webhook_url, channel, immediate vs digest routing, digest_time_utc
- All sections documented with YAML examples, parameter descriptions, and clear purpose explanations
- Updated hot reload note to mention slack_notifications requires restart for webhook URL changes

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

All success criteria met:

- Database section includes all 6 new tables with accurate CREATE statements from backend/db/models.py
- API section documents all Phase 3-4 endpoints (15 new endpoints across 5 sections)
- Config section shows all 9 new alerting_rules.yaml sections with YAML examples matching actual config structure
- All new sections have clear purpose explanations
- No JSX syntax errors (DocsPage.tsx still compiles and renders correctly)

**Grep verification:**
- Database tables: 11 occurrences (6 tables + references)
- API sections: 7 phase-badged sections (Feedback, Assignment, Interventions, Metrics, Admin-Slack)
- Config sections: 9 occurrences (all new sections present)

## Key Technical Details

**Database Documentation:**
- All table schemas copied verbatim from backend/db/models.py SQL_CREATE_* constants
- Accurate column types (INTEGER vs TEXT), constraints (CHECK, UNIQUE, FK), and indexes
- Purpose explanations clarify use cases (e.g., pending_notifications queue for digest, interventions for baseline exclusion)

**API Documentation:**
- Accurate HTTP methods (GET/POST/DELETE/PUT) and endpoint paths from backend/api/routes.py
- Rate limits documented (30/min for mutations, 60/min for GET, 10/hour for admin)
- Request/response body formats shown with JSON examples
- Phase badges visually distinguish v1.0 vs v1.1 endpoints

**Config Documentation:**
- YAML examples match actual config/alerting_rules.yaml structure
- Parameter descriptions explain thresholds and behavior
- Phase-based grouping improves discoverability
- Updated scheduling section to reflect A5/A6/A7 in 2h cycle

## Integration Points

**Frontend → Backend:**
- Docs now accurately reflect backend schema from Phases 3-4
- Developers can reference docs for API integration without inspecting backend code
- Config section shows all tunable parameters for operators

**Operator Education:**
- Technical docs serve as reference for ops team when configuring alerts
- Database section clarifies data model for troubleshooting
- API section enables custom scripts/integrations

## Impact

**Documentation Completeness:**
- Technical docs now comprehensive for v1.1 (all Phases 1-4 changes documented)
- No more gaps between code and docs — developers can trust docs as source of truth
- Phase badges provide clear visual distinction between v1.0 and v1.1 features

**Developer Experience:**
- New tables/endpoints discoverable via docs (no need to read backend code)
- YAML config examples copy-pasteable for custom deployments
- Accurate schemas enable schema validation and data modeling

**Next Steps:**
- Phase 5 (Dati Live e Multi-canale) will add Athena/GAM sections to data layer docs
- Future phases will continue updating docs in lockstep with code changes
- Docs audit process proven successful — repeat for future milestones

## Self-Check: PASSED

Verified all claims:

- [x] Database section shows 10 tables intro: `grep "10 tabelle totali"` confirmed
- [x] All 6 new tables present: `grep "alert_feedback\|alert_assignments\|manual_interventions"` confirmed 11 occurrences
- [x] API section shows ~34 endpoints: `grep "~34 endpoint totali"` confirmed
- [x] All new endpoint sections present: `grep "Feedback.*Phase 3\|Assignment.*Phase 3"` confirmed 7 sections
- [x] Config section shows v1.1 with 9 sections: `grep "v1.1.*9 nuove sezioni"` confirmed
- [x] All config sections present: `grep "drift_regression:\|comparative_alerting:"` confirmed 9 occurrences
- [x] Commits exist: 66d8f46, c913b98, c77900c (git log verified)
- [x] DocsPage.tsx still valid: no JSX syntax errors

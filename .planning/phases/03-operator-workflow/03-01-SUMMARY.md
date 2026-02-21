---
phase: 03-operator-workflow
plan: 01
subsystem: operator-feedback
tags: [feedback, false-positives, learning, database]
dependency_graph:
  requires: [02-nuovi-tipi-alert]
  provides: [feedback-api, feedback-db, publisher-history]
  affects: [alert-detail, publisher-detail]
tech_stack:
  added: []
  patterns: [feedback-categories, auto-publisher-extraction, historical-tracking]
key_files:
  created:
    - backend/db/models.py::SQL_CREATE_ALERT_FEEDBACK
  modified:
    - backend/db/models.py
    - backend/db/database.py
    - backend/db/operations.py
    - backend/api/schemas.py
    - backend/api/routes.py
decisions:
  - key: "6-category feedback taxonomy"
    rationale: "REAL + 5 FALSE_POSITIVE variants (MANUAL_INTERVENTION, SEASONALITY, TECHNICAL, PUBLISHER_CAMPAIGN, MARKET_NOISE) cover all common false positive root causes observed in production"
  - key: "Automatic publisher_id extraction"
    rationale: "Extract from alert contributors automatically to enable historical tracking without frontend complexity"
  - key: "Publisher feedback history includes alert context"
    rationale: "JOIN with alerts table to provide alert_rule and timestamp for historical pattern analysis"
metrics:
  duration_hours: 0.05
  tasks_completed: 3
  files_modified: 5
  commits: 3
  completed_at: "2026-02-21"
---

# Phase 03 Plan 01: Operator Feedback System Summary

Sistema di feedback operatore implementato per alert — l'operatore può confermare un alert come reale o segnalarlo come falso positivo con categoria predefinita, aggiungere commenti, e il sistema mostra lo storico dei feedback sullo stesso publisher.

## Objective

Abilitare il ciclo di feedback operativo che permette al sistema di accumulare conoscenza su quali pattern sono reali vs rumore per publisher specifici.

## Tasks Completed

### Task 1: Database schema for alert feedback
**Commit:** 2abbf49
**Files:** backend/db/models.py, backend/db/database.py

- Added `FeedbackCategory` enum with 6 values (REAL + 5 FALSE_POSITIVE variants)
- Added `AlertFeedbackModel` Pydantic model with all required fields
- Added `SQL_CREATE_ALERT_FEEDBACK` table schema with CHECK constraint
- Added `idx_feedback_publisher` index for publisher_id queries
- Initialized table in database.py init_db sequence

### Task 2: Database operations for feedback
**Commit:** 0006255
**Files:** backend/db/operations.py

- Added `create_feedback()` with automatic publisher_id extraction from alert contributors
- Added `get_feedbacks_for_alert()` to retrieve all feedbacks for an alert
- Added `get_publisher_feedback_history()` with JOIN to alerts for context (alert_rule, alert_timestamp)
- All operations use get_db() pattern with proper error handling

### Task 3: API schemas and endpoints for feedback
**Commit:** f1adbbf
**Files:** backend/api/schemas.py, backend/api/routes.py

- Added `FeedbackRequest`, `FeedbackResponse`, `FeedbackHistoryResponse` schemas
- Added `POST /api/alerts/{alert_id}/feedback` with FeedbackCategory enum validation
- Added `GET /api/alerts/{alert_id}/feedbacks` to list alert feedbacks
- Added `GET /api/publishers/{publisher_id}/feedback-history` with limit param (default 50, max 200)
- All endpoints use require_auth and rate limiting (30/min for POST, 60/min for GET)

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

All success criteria met:

- alert_feedback table exists in SQLite with 7 columns (feedback_id, alert_id, user_id, feedback_type, comment, publisher_id, timestamp)
- FeedbackCategory enum has 6 values (REAL + 5 FALSE_POSITIVE variants)
- create_feedback() extracts publisher_id from alert contributors automatically
- POST /api/alerts/{alert_id}/feedback accepts feedback_type and optional comment, returns feedback_id
- GET /api/alerts/{alert_id}/feedbacks returns all feedbacks for alert ordered by timestamp DESC
- GET /api/publishers/{publisher_id}/feedback-history returns historical feedbacks with alert context (alert_rule, alert_timestamp)
- All operations handle errors gracefully with logging

## Key Technical Details

**Database Schema:**
```sql
CREATE TABLE alert_feedback (
    feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    feedback_type TEXT NOT NULL CHECK(...),
    comment TEXT,
    publisher_id TEXT,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id)
);
CREATE INDEX idx_feedback_publisher ON alert_feedback(publisher_id);
```

**Feedback Categories:**
- REAL
- FALSE_POSITIVE_MANUAL_INTERVENTION
- FALSE_POSITIVE_SEASONALITY
- FALSE_POSITIVE_TECHNICAL
- FALSE_POSITIVE_PUBLISHER_CAMPAIGN
- FALSE_POSITIVE_MARKET_NOISE

**Publisher ID Extraction:**
The `create_feedback()` function automatically extracts `publisher_id` from the first contributor in the alert's `contributors_json` field. This enables historical tracking without requiring the frontend to pass publisher_id explicitly.

**Historical Context:**
The `get_publisher_feedback_history()` function performs a JOIN with the alerts table to include `alert_rule` and `alert_timestamp` alongside each feedback entry, providing full context for pattern analysis.

## Integration Points

**Backend → Frontend (Phase 03 Plan 02):**
- POST /api/alerts/{alert_id}/feedback - Submit feedback from alert detail page
- GET /api/alerts/{alert_id}/feedbacks - Display feedback history on alert detail
- GET /api/publishers/{publisher_id}/feedback-history - Show publisher's past feedback patterns

**Database:**
- alert_feedback table joins with alerts table via alert_id
- publisher_id enables historical queries for pattern learning (future Phase 5)

## Impact

**Operator Capability:**
- Operators can now classify alerts as REAL or FALSE_POSITIVE with specific root cause
- Operators can add free-text comments explaining their decision
- System tracks who provided feedback and when

**Historical Knowledge:**
- Publisher feedback history available via API
- Foundation for future ML-based false positive detection
- Enables pattern analysis across alert types for the same publisher

**Next Steps (Phase 03 Plan 02):**
- Frontend UI for feedback submission on alert detail page
- Display feedback history section on alert detail
- Publisher detail page integration with feedback history

## Self-Check: PASSED

Verified all claims:

- [x] alert_feedback table exists with correct schema: sqlite3 confirmed 7 columns + CHECK constraint + index
- [x] FeedbackCategory enum exists: 6 values confirmed via Python import
- [x] AlertFeedbackModel importable: confirmed via Python import
- [x] create_feedback, get_feedbacks_for_alert, get_publisher_feedback_history importable: confirmed
- [x] FeedbackRequest, FeedbackResponse schemas importable: confirmed
- [x] POST /api/alerts/{alert_id}/feedback endpoint exists: grep confirmed @router.post decorator
- [x] Commits exist: 2abbf49, 0006255, f1adbbf (git log verified)

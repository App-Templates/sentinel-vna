"""Phase 10 MONITOR-02: silent-failure watchdog package.

Watertight boundary per R-13 — monitoring concerns do not leak into
pipeline execution, scheduler, or API layers. Scheduler registers the
cron hook; API endpoint (/api/health/alerts-pipeline, Plan 10-02) exposes
the same metrics the watchdog keys on.
"""

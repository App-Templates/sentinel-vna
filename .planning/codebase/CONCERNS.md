# Codebase Concerns

**Analysis Date:** 2026-02-18

## Production Gaps

### Scheduler-to-Pipeline Integration [Critical]
- Issue: The scheduler (`backend/scheduler/scheduler.py`) calls `run_pipeline()` which compiles a new LangGraph graph on every invocation (line 192-193 of `backend/workflow/graph.py`). Each call to `compile_graph()` creates a new `MemorySaver()` checkpointer, meaning no pipeline state is ever reused or persisted across runs.
- Files: `backend/workflow/graph.py:145-149`, `backend/scheduler/scheduler.py:43-47`
- Impact: The scheduler does call the pipeline, but graph compilation overhead is paid every run. MemorySaver is ephemeral (in-memory only), so LangGraph checkpointing provides zero value — pipeline state is discarded after each invocation.
- Fix approach: Either use a persistent checkpointer (SqliteSaver) or remove the checkpointer entirely since each run is independent. Pre-compile the graph once at module level and reuse it.

### Recheck Does Not Compare Results [High]
- Issue: The recheck queue processor (`backend/scheduler/scheduler.py:110-141`) runs the pipeline but ignores the result. It marks the recheck as COMPLETED regardless of whether the anomaly persists, resolves, or worsens. There is no comparison between the original alert and the recheck outcome.
- Files: `backend/scheduler/scheduler.py:128-133`
- Impact: Rechecks are cosmetic — they cannot auto-resolve alerts or escalate severity. Operators get no signal from rechecks.
- Fix approach: Compare recheck pipeline output (severity, delta) against the original alert. Auto-resolve if anomaly is gone, escalate if worsened, or keep as-is with a RECHECK event recording the finding.

### Athena/GAM Connectors Untested [High]
- Issue: Both connectors (`backend/connectors/athena.py`, `backend/connectors/gam.py`) are structurally complete with retry logic, input validation, and parameterized queries, but have never been tested against real AWS/GAM infrastructure. The GAM connector has 4 TODO comments indicating unconfirmed column mappings and dimension names.
- Files: `backend/connectors/athena.py`, `backend/connectors/gam.py:109,123,213,227`
- Impact: The Athena->GAM->Parquet fallback chain works at the parquet level only. Enabling Athena or GAM in production without integration testing will likely fail on schema mismatches.
- Fix approach: Create integration test scripts with real AWS/GAM credentials in a staging environment. Verify column mappings before enabling.

### Notifier Slack/Email Not Exercised [Medium]
- Issue: The notifier (`backend/agents/notifier.py`) has full Slack Block Kit message building and SMTP email logic, but these are guarded by env vars (`SLACK_WEBHOOK_URL`, `SMTP_HOST`). Without these configured, notifications silently skip. There is no dry-run or test mode for notifications.
- Files: `backend/agents/notifier.py:158-203` (Slack), `backend/agents/notifier.py:206-259` (email)
- Impact: No way to verify notification formatting or delivery without actually configuring production webhooks/SMTP. First real alert notification may be malformed.
- Fix approach: Add a `/api/admin/test-notification` endpoint that sends a sample alert to configured channels.

### Synthetic Data Mixed with Real [Medium]
- Issue: The database contains 179 alerts where revenue/baseline/contributors/geo/env data is REAL (from parquet), but alert statuses (OPEN/ACK/RESOLVED) and events are SYNTHETIC (randomly assigned by `scripts/regenerate_alerts.py`). There is no flag distinguishing real pipeline-generated alerts from seeded demo data.
- Files: `scripts/regenerate_alerts.py`, `data/vna_alerts.db`
- Impact: If the scheduler starts generating real alerts, they will be mixed with seed data. Operators cannot distinguish real from demo alerts. Metrics/health dashboards will report inaccurate statistics.
- Fix approach: Add a `source` column or tag to alerts (e.g., "seed", "pipeline", "backtest"). Provide a cleanup endpoint or migration to purge seed data before going live.

### Two Data Fetcher Implementations [Medium]
- Issue: There are two data fetcher files: `backend/agents/data_fetcher.py` (generates synthetic data) and `backend/agents/data_fetcher_real.py` (uses parquet with Athena/GAM fallback). The LangGraph graph (`backend/workflow/graph.py:22`) imports and uses `data_fetcher.py` (synthetic), not the real one.
- Files: `backend/workflow/graph.py:22`, `backend/agents/data_fetcher.py`, `backend/agents/data_fetcher_real.py`
- Impact: The LIVE pipeline currently uses synthetic data generation, not real parquet data. Only the backtest runner and direct route handlers use real data.
- Fix approach: Switch the graph import to `data_fetcher_real.py` and remove or archive the synthetic fetcher.

## Security

### Auth Bypassed in Development [Medium]
- Issue: When `ENVIRONMENT=development` (the default), `require_auth()` in `backend/api/auth.py:56-58` returns a hardcoded user `{"email": "stefano@hej.ia", ...}` without any authentication check. All API routes including admin endpoints are fully open.
- Files: `backend/api/auth.py:25-26,56-58`
- Impact: Acceptable for local development, but if accidentally deployed to production without `ENVIRONMENT=production`, all endpoints are unauthenticated. The `main.py:34-38` fail-fast check for SESSION_SECRET partially mitigates this.
- Fix approach: Add a startup warning banner when running in development mode. Consider requiring explicit opt-in for auth bypass.

### In-Memory Session Store [Medium]
- Issue: Auth sessions are stored in a Python dict (`_sessions` in `backend/api/auth.py:19`). Sessions are lost on server restart and cannot be shared across multiple processes/workers.
- Files: `backend/api/auth.py:19-20`
- Impact: Every server restart logs out all users. The comment says "sufficient for team <20" which is fair for the current scope, but prevents horizontal scaling.
- Fix approach: For production, use SQLite-backed sessions or Redis. For the current single-worker setup, this is acceptable.

### CORS Open in Development [Low]
- Issue: In development mode, CORS allows `*` origins with credentials (`backend/main.py:103-109`). `allow_credentials=True` with `allow_origins=["*"]` is technically invalid per the CORS spec — browsers will reject it. In production, CORS is properly restricted to `FRONTEND_URL`.
- Files: `backend/main.py:93-109`
- Impact: Low risk — development only, and browsers will actually block `credentials: true` with `*` origin. The real concern is that Vite's dev proxy bypasses CORS entirely, masking any CORS bugs until production.
- Fix approach: In development mode, set `allow_origins=["http://localhost:5173"]` instead of `*` to match the Vite dev server.

### Admin Routes Lack Role-Based Access [Medium]
- Issue: All admin endpoints (`/api/admin/*`) use the same `require_auth` dependency as regular alert endpoints. Any authenticated `@adkaora.com` user can modify data sources, alerting rules, and scheduler config. There is no admin vs. operator role distinction.
- Files: `backend/main.py:116-117`, `backend/api/admin_routes.py`
- Impact: Any team member can accidentally change alerting thresholds or switch data sources. This is acceptable for a small team but risky as usage grows.
- Fix approach: Add a role field to auth (e.g., admin vs. viewer) and restrict admin routes accordingly.

### Credential Path Validation Allows Project Root [Low]
- Issue: `_validate_credentials_path()` in `backend/api/admin_routes.py:27-31` allows credentials files under the entire project root `BASE_DIR`. While it prevents path traversal above the project, it still allows pointing to any file within the project (e.g., `config/alerting_rules.yaml`).
- Files: `backend/api/admin_routes.py:27-50`
- Impact: Low — the credentials path is only used by the GAM connector to load a service account JSON file. An attacker with admin access could point it to a non-credential file, but this requires authenticated access already.
- Fix approach: Restrict to `data/credentials/` subdirectory only.

## Data Integrity

### No Alert Deduplication [High]
- Issue: The pipeline and notifier insert alerts using `INSERT OR REPLACE` keyed on `alert_id`, which is derived from `ALT-{date}-{time}-{severity}`. If two pipeline runs execute at the exact same second with the same severity, one alert overwrites the other. There is no deduplication logic to prevent duplicate alerts for the same ongoing anomaly across consecutive scheduler runs.
- Files: `backend/agents/notifier.py:46-54`, `backend/db/models.py:113-115`
- Impact: The scheduler runs A1+A3 every 2 hours. If an anomaly persists across runs, each run generates a new alert for the same ongoing issue, leading to alert fatigue. Conversely, second-level collisions (unlikely but possible) silently overwrite alerts.
- Fix approach: Before creating an alert, check if an OPEN alert exists for the same channel_group+alert_rule within a configurable dedup window. Merge or suppress duplicates.

### Parquet Cache Invalidation Is Time-Based Only [Medium]
- Issue: Multiple modules cache parquet DataFrames with TTL-based invalidation: `backend/agents/data_fetcher_real.py` (24h TTL), `backend/agents/anomaly_detector.py` (1h TTL), `backend/api/routes.py` (no expiry — indefinite). If parquet files are updated on disk, cached data may be stale.
- Files: `backend/agents/data_fetcher_real.py:30-36`, `backend/agents/anomaly_detector.py:34-36`, `backend/api/routes.py:57-64`
- Impact: After a parquet file refresh, different modules may use different data versions for up to 24 hours. The routes module never refreshes unless the server restarts.
- Fix approach: Centralize parquet loading into a single cache manager that checks file modification time (mtime). All modules should use the same cache instance.

### SQLite Timestamp Stored as Text [Low]
- Issue: All timestamp columns in SQLite are stored as TEXT (`backend/db/models.py:118-139`). While SQLite has no native datetime type, this means all date comparisons are string-based, which works for ISO 8601 format but prevents using SQLite date functions efficiently.
- Files: `backend/db/models.py:118-139`, `backend/db/operations.py`
- Impact: Queries like `WHERE timestamp >= ?` work correctly because ISO 8601 strings sort lexicographically. However, operations like "get alerts from last 7 days" require `datetime('now', '-7 days')` which is fragile with TEXT columns.
- Fix approach: This is acceptable for the current scale. If query performance becomes an issue, add INTEGER epoch columns alongside TEXT for indexed date range queries.

### Backtest Alerts Stored in Same Table as Live [Medium]
- Issue: Backtest-generated alerts and live pipeline alerts share the `alerts` table. The `data_source` column distinguishes them ("parquet" vs "backtest"), but there is no strong isolation. Alert counts, metrics, and dashboard views include backtest alerts unless explicitly filtered.
- Files: `backend/db/operations.py:66-113`, `backend/api/routes.py:86-108`
- Impact: The dashboard `/api/alerts` endpoint does not filter out backtest alerts by default. The 179 current alerts include 29 backtest alerts that inflate statistics.
- Fix approach: Either use a separate table for backtest results (already exists as `backtest_results`) and stop inserting backtest alerts into the main table, or add a default filter excluding backtest alerts from the main list endpoint.

## Scalability

### SQLite Single-Writer Bottleneck [Medium]
- Issue: SQLite with WAL mode supports concurrent reads but only one writer at a time. The `busy_timeout=5000` (`backend/db/database.py:43`) means writers wait up to 5 seconds for a lock. With a single uvicorn worker (`backend/main.py:148`), this is fine, but prevents scaling to multiple workers.
- Files: `backend/db/database.py:40-43`, `backend/main.py:148`
- Impact: Single-worker deployment limits throughput to one API request at a time for write operations. For a team of <20 users this is acceptable. Horizontal scaling requires migrating to PostgreSQL.
- Fix approach: For the foreseeable use case (small ops team), SQLite WAL is adequate. Document the single-worker constraint. Plan PostgreSQL migration for if/when multi-user concurrency becomes an issue.

### Thread-Local DB Connections [Low]
- Issue: Database connections use `threading.local()` (`backend/db/database.py:23`), creating one connection per thread. FastAPI with uvicorn uses an async event loop, but sync route handlers run in a thread pool. Connections are never explicitly closed per-request.
- Files: `backend/db/database.py:23,36-46`
- Impact: With a single worker, the thread pool is bounded (default 40 threads in Starlette). Each thread gets a persistent connection. This is fine for the current scale but connections accumulate if thread pool grows.
- Fix approach: Acceptable for current architecture. If moving to async database access, switch to aiosqlite which is already in requirements.

### No Pagination on Backtest Results [Low]
- Issue: `get_all_backtest_results()` fetches ALL backtest results with no limit or pagination (`backend/db/operations.py:312-317`).
- Files: `backend/db/operations.py:312-317`, `backend/api/routes.py:280-284`
- Impact: If many backtests are run, this query returns an unbounded result set. Currently negligible with <30 backtests.
- Fix approach: Add `LIMIT/OFFSET` parameters matching the alerts endpoint pattern.

### Parquet Files Loaded Into Memory [Medium]
- Issue: All three parquet files (360K + 650K + 740K rows) are loaded entirely into memory as pandas DataFrames. Multiple modules cache separate copies: `data_fetcher_real.py`, `anomaly_detector.py`, `routes.py`, and `publisher_routes.py` each maintain independent caches.
- Files: `backend/agents/data_fetcher_real.py:29-35`, `backend/agents/anomaly_detector.py:33-36`, `backend/api/routes.py:57-64`
- Impact: Memory usage is ~500MB-1GB for the parquet caches alone (multiple copies of overlapping data). On constrained environments this matters. With Athena as the primary source, parquet serves as fallback — but currently all data comes from parquet.
- Fix approach: Centralize into a single DataCache service. Use DuckDB (already in requirements) for query-on-parquet without full DataFrame materialization.

## Monitoring

### No Alerting on the Alerting System [High]
- Issue: The health endpoint (`backend/api/routes.py:431-464`) checks DB connectivity and scheduler status, and reports 24h pipeline metrics. However, there is no mechanism to alert the team if the alerting system itself fails — no heartbeat monitoring, no dead-man's switch, no external health check.
- Files: `backend/api/routes.py:431-464`
- Impact: If the scheduler silently fails, the pipeline crashes, or the server goes down, no one is notified. An alerting system that cannot alert about its own failures is a critical gap for production.
- Fix approach: Implement a dead-man's switch: if no pipeline run has completed in 3x the expected interval, send a meta-alert via a separate channel (e.g., direct Slack webhook or PagerDuty). Add an external uptime monitor hitting `/api/health`.

### Logging to stdout Only [Medium]
- Issue: The logger (`backend/utils/logger.py`) outputs to stdout only with a plain text format. There is no structured (JSON) logging, no log rotation, no persistent log storage, and no log aggregation.
- Files: `backend/utils/logger.py:1-40`
- Impact: Logs are lost when the container restarts. No way to search historical logs for debugging production issues. Docker captures stdout, but without structured logging, parsing is difficult.
- Fix approach: Add JSON structured logging (python-json-logger is in root `requirements.txt` but not in `backend/requirements.txt`). In Docker, stdout goes to the container runtime log driver which handles rotation.

### Pipeline Run Metrics Are Basic [Low]
- Issue: `pipeline_runs` table records run_id, duration, status, and whether LLM was used. It does not capture per-agent timing, memory usage, data source actually used, or number of data points processed.
- Files: `backend/db/models.py:165-180`, `backend/db/operations.py:212-237`
- Impact: When debugging slow or failed pipeline runs, there is no granular telemetry to identify which agent is the bottleneck.
- Fix approach: Add per-agent timing to the AlertState (execution_times dict) and persist it. Log data source fallback chain outcomes.

## Missing Features

### No Alert Suppression / Maintenance Windows [High]
- Issue: There is no mechanism to suppress alerts during known maintenance windows, deployments, or expected low-traffic periods (holidays, weekends). The off-peak z-score suppression in `anomaly_detector.py:384-388` is the only noise reduction, and it is hardcoded.
- Files: `backend/agents/anomaly_detector.py:384-388`
- Impact: Scheduled maintenance or known events will trigger false alerts. Operators must manually acknowledge each one, leading to alert fatigue.
- Fix approach: Add a maintenance_windows table and API. Suppress alert generation (or auto-acknowledge) during configured windows.

### No Alert Grouping / Correlation [Medium]
- Issue: Each pipeline run for each channel generates an independent alert. Related alerts (e.g., both GOOGLE and OPEN_BIDDING dropping at the same time due to the same root cause) are not correlated. There is no incident grouping.
- Files: `backend/workflow/graph.py:154-204`, `backend/scheduler/scheduler.py:34-78`
- Impact: A single infrastructure event affecting all channels generates 2+ separate alerts. Operators must manually correlate related alerts.
- Fix approach: Add an incident abstraction that groups alerts with overlapping time windows and similar characteristics.

### No Historical Trend Analysis on Dashboard [Low]
- Issue: The dashboard shows current alerts and 24h revenue status, but no week-over-week or month-over-month trend views. The alert detail page has a 7-day trend chart, but there is no system-wide trend.
- Files: `frontend/src/pages/DashboardPage.tsx`, `backend/api/routes.py:330-424`
- Impact: Operators see individual anomalies but lack context for slow degradation patterns. A2 (drift) alerts partially cover this, but only at the channel level.
- Fix approach: Add a trend endpoint aggregating daily revenue/bacino/coverage for the last 30/90 days.

### No Audit Log for Config Changes [Medium]
- Issue: When alerting rules are modified via `PUT /api/admin/alerting-rules`, the YAML file is overwritten in-place with no backup, no diff, and no audit trail of who changed what when.
- Files: `backend/api/admin_routes.py:331-368`
- Impact: Misconfigured thresholds could cause alert storms or missed alerts, with no way to trace or rollback the change.
- Fix approach: Store config change history in an `audit_log` table: timestamp, user, old_value, new_value. Create a YAML backup before each write.

## Dependency Risks

### Version Pinning Inconsistency [Medium]
- Issue: Root `requirements.txt` uses loose version ranges (`>=`), while `backend/requirements.txt` uses exact pins (`==`). The root file references `sqlalchemy>=2.0.0` but SQLAlchemy is not used anywhere — the project uses raw `sqlite3`. The root file is stale/disconnected from the actual backend deps.
- Files: `requirements.txt` (root), `backend/requirements.txt`
- Impact: The root `requirements.txt` may mislead contributors. `sqlalchemy` is listed but unused, adding unnecessary install time. Loose pins risk breaking changes.
- Fix approach: Delete or rename root `requirements.txt`. Use only `backend/requirements.txt` with exact pins. Remove unused `sqlalchemy` dependency.

### LangGraph Rapid Version Churn [Low]
- Issue: LangGraph is at v0.2.65 (pre-1.0). The API surface has changed significantly between minor versions. No lockfile pins transitive dependencies.
- Files: `backend/requirements.txt:5`
- Impact: Upgrading LangGraph may break the graph construction, state typing, or checkpointer API. The project uses `StateGraph`, `MemorySaver`, and `END` which are core primitives likely to remain stable, but the risk exists.
- Fix approach: Pin langgraph precisely and test before upgrading. Consider generating a `pip freeze` lockfile.

### Unused Dependencies in Backend Requirements [Low]
- Issue: `aiosqlite==0.20.0` and `duckdb==1.1.3` are in `backend/requirements.txt` but not imported anywhere in the backend code. `pyathena==3.12.2` is listed but the Athena connector uses `boto3` directly, not pyathena.
- Files: `backend/requirements.txt:10,11,19`
- Impact: Adds unnecessary install size and potential supply chain surface. No functional impact.
- Fix approach: Remove `aiosqlite`, `duckdb`, and `pyathena` unless there are plans to use them.

## Frontend Concerns

### No Error Boundaries [Medium]
- Issue: The React app has no `ErrorBoundary` component. If any component throws during rendering (e.g., null data from API, unexpected shape), the entire app crashes with a white screen.
- Files: `frontend/src/App.tsx`, all page components
- Impact: A single malformed API response or rendering bug takes down the entire UI. Users must manually refresh.
- Fix approach: Add a top-level ErrorBoundary wrapping `<Routes>` that catches rendering errors and shows a fallback UI with a retry button.

### No Loading/Error States on Some Pages [Low]
- Issue: Most pages handle `isLoading` and `error` states from TanStack Query, but some hooks (e.g., `useDataSources`, `useAlertingRules` in `frontend/src/api/client.ts:135-137`) return untyped data, making it easy to miss null checks.
- Files: `frontend/src/api/client.ts:135-137`
- Impact: Minor — TanStack Query provides loading/error states automatically. The risk is in component code not checking them.
- Fix approach: Add TypeScript generics to all hook return types.

### No Accessibility (a11y) Audit [Low]
- Issue: The UI uses Tailwind CSS utility classes with no ARIA attributes observed on interactive elements. No evidence of screen reader testing, keyboard navigation testing, or color contrast verification.
- Files: All components under `frontend/src/components/`, `frontend/src/pages/`
- Impact: Low priority for an internal ops tool used by a small team. However, color-coded severity badges (red/orange/yellow) may be indistinguishable for colorblind users.
- Fix approach: Add `aria-label` to icon buttons, ensure keyboard navigability on tables and filters. Use severity text labels alongside color.

### Frontend Test Coverage: Zero [Medium]
- Issue: There are no frontend tests. No Vitest/Jest config, no test files, no testing-library dependency. The `package.json` has no `test` script.
- Files: `frontend/package.json`
- Impact: All frontend changes are manually verified. Regressions in data display, filtering, or chart rendering are caught only by visual inspection.
- Fix approach: Add Vitest + React Testing Library. Prioritize tests for critical flows: alert list rendering, filter application, alert detail data parsing.

## Operational Concerns

### No Database Backup Strategy [High]
- Issue: The SQLite database (`data/vna_alerts.db`) is the single source of truth for all alerts, events, pipeline runs, and backtest results. There is no backup mechanism, no WAL checkpointing schedule, and no export/restore tooling. The Docker volume mount (`docker-compose.yml:8`) persists data but does not back it up.
- Files: `docker-compose.yml:8`, `backend/db/database.py`
- Impact: A corrupted or deleted SQLite file means total data loss. WAL mode helps prevent corruption during crashes, but does not protect against disk failure or accidental deletion.
- Fix approach: Add a cron job to copy/compress the SQLite database to a remote location (S3/GCS). Use `sqlite3 .backup` for consistent snapshots. Document recovery procedure.

### No CI/CD Pipeline [Medium]
- Issue: There is no `.github/workflows/`, no Makefile, no CI configuration of any kind. The Dockerfile exists but there is no automated build, test, or deploy pipeline.
- Files: (absent) `.github/workflows/`, `Makefile`
- Impact: All deployments are manual. No automated testing on PRs. No build verification.
- Fix approach: Add a minimal GitHub Actions workflow: lint, type-check, and run integration tests (if/when tests are added).

### Single Container / No Health-Based Restart [Low]
- Issue: `docker-compose.yml` uses `restart: unless-stopped` but has no `healthcheck`. If the application enters a degraded state (e.g., scheduler thread dies but HTTP still responds), it will not be restarted.
- Files: `docker-compose.yml`
- Impact: Silent degradation — the server is "up" but not functioning correctly.
- Fix approach: Add a `healthcheck` that curls `/api/health` and verifies both `db_ok` and `scheduler_running` are true.

### No Graceful Shutdown of Scheduler [Low]
- Issue: `stop_scheduler()` calls `scheduler.shutdown(wait=True)` which waits for running jobs. However, SIGTERM handler in `backend/main.py:41-46` calls `stop_scheduler()` then raises `SystemExit(0)`. If a pipeline run is in progress (which can take 10-30s), the SIGTERM handler may block uvicorn's graceful shutdown timeout.
- Files: `backend/main.py:41-46`, `backend/scheduler/scheduler.py:188-193`
- Impact: During deployment restarts, in-flight pipeline runs may be interrupted or block shutdown.
- Fix approach: Set a timeout on `scheduler.shutdown(wait=False)` during SIGTERM, or use uvicorn's lifespan shutdown which already calls `stop_scheduler()`.

### Config File Lives in Working Directory [Low]
- Issue: `config/alerting_rules.yaml` and `data/datasource_config.json` are writable config files that live in the project directory. The admin API modifies `alerting_rules.yaml` in-place. In a Docker deployment, these are on the container filesystem (config) or mounted volume (data).
- Files: `config/alerting_rules.yaml`, `backend/api/admin_routes.py:360-363`
- Impact: If the Docker image is rebuilt without the volume mount, config changes are lost. The `alerting_rules.yaml` is baked into the Docker image but modified at runtime — this creates a split-brain between the image and runtime config.
- Fix approach: Move runtime-modifiable config to the `data/` volume (which is already mounted). Keep `config/alerting_rules.yaml` as the default template only.

## Test Coverage Gaps

### Backend: No Test Suite [Critical]
- Issue: There are no pytest test files in the project. The only test-like file is `scripts/test_integration.py` which is a manual integration test script, not a pytest suite. No unit tests for agents, DB operations, or API routes.
- Files: (absent) `tests/`, `scripts/test_integration.py` (manual only)
- Impact: All code changes are verified only by manual testing or production observation. The complex anomaly detection logic (Z-scores, consecutive hours, threshold multipliers) has zero automated verification. Regressions in triage classification, contributor analysis, or geo breakdown are undetectable.
- Fix approach: Create `tests/` directory with unit tests for: (1) anomaly_detector thresholds and consecutive-hours logic, (2) data_validator delta computations, (3) triage_classifier label assignment, (4) API route responses. Use pytest fixtures with a test SQLite database.

### Integration Test Script Is Read-Only [Low]
- Issue: `scripts/test_integration.py` (288 lines) tests API endpoints via HTTP but must be run manually against a running server. It is not integrated with pytest and has no assertions — it prints results for human inspection.
- Files: `scripts/test_integration.py`
- Impact: Not usable in CI. Does not catch regressions automatically.
- Fix approach: Convert to pytest with FastAPI's TestClient for in-process testing.

---

*Concerns audit: 2026-02-18*

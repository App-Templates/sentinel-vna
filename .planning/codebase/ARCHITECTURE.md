# Architecture

**Analysis Date:** 2026-02-18

## Pattern Overview

**Overall:** Multi-agent pipeline (LangGraph StateGraph) wrapped in a FastAPI monolith with React SPA frontend.

**Key Characteristics:**
- 11-agent LangGraph pipeline for anomaly detection, triage, analysis, and notification
- FastAPI serves both the REST API and (in production) the built React SPA
- SQLite (WAL mode) as the sole persistent store
- APScheduler runs periodic alerting cycles inside the same process (single worker)
- Dual-mode operation: LIVE (real-time monitoring) and BACKTEST (historical simulation)
- LLM-optional design: every agent has a pure-Python statistical fallback when no `ANTHROPIC_API_KEY` is set
- Data source fallback chain: Athena -> GAM -> Parquet -> BLOCKED (no synthetic in LIVE mode)

## Layers

**Presentation Layer (Frontend):**
- Purpose: React 18 SPA for ops dashboard, alert management, publisher analytics
- Location: `frontend/src/`
- Contains: Pages, components, hooks, API client, TypeScript types
- Depends on: Backend REST API at `/api/*` and `/auth/*`
- Used by: End users (Adkaora ops team)

**API Layer:**
- Purpose: HTTP REST interface for alerts, publishers, backtest, admin, health
- Location: `backend/api/`
- Contains: FastAPI routers, Pydantic request/response schemas, rate limiting, auth middleware
- Depends on: DB operations, config loader, data fetcher (for trend), scheduler status
- Used by: Frontend, potential external clients

**Agent Layer (LangGraph Pipeline):**
- Purpose: Anomaly detection, classification, analysis, and report generation
- Location: `backend/agents/`, `backend/workflow/`
- Contains: 11 agent functions, state definition, graph construction, conditional edges
- Depends on: Data connectors (parquet/Athena/GAM), config loader, LLM retry utility, DB operations (notifier)
- Used by: Scheduler jobs, backtest runner

**Data Access Layer:**
- Purpose: SQLite database operations and parquet data loading
- Location: `backend/db/`, `backend/connectors/`
- Contains: Database init/migration, CRUD operations, Athena/GAM connectors
- Depends on: SQLite, PyArrow/Pandas, boto3 (optional), Google API (optional)
- Used by: API routes, agents, scheduler

**Scheduler Layer:**
- Purpose: Periodic execution of alerting cycles (A1+A3, A2, rechecks)
- Location: `backend/scheduler/scheduler.py`
- Contains: APScheduler job definitions, cycle runners
- Depends on: Pipeline runner (workflow/graph), DB operations, config
- Used by: Application lifespan (started/stopped automatically)

**Configuration Layer:**
- Purpose: Centralized threshold/rule configuration
- Location: `config/alerting_rules.yaml`, `backend/utils/config_loader.py`
- Contains: YAML config file, Pydantic validation models, thread-safe singleton loader
- Depends on: PyYAML, Pydantic
- Used by: Every agent, scheduler, API routes

## LangGraph Pipeline (11 Agents)

**Graph Definition:** `backend/workflow/graph.py`
**State Type:** `backend/workflow/state.py` — `AlertState(TypedDict, total=False)`

### Pipeline Flow

```
orchestrator -> data_fetcher -> data_validator -> anomaly_detector
                                                       |
                                          [A0?] ------+------- [normal]
                                          |                       |
                                    report_builder          triage_classifier
                                          |                       |
                                    [BACKTEST?]            [alert_triggered?]
                                     |      |              |            |
                                    END   notifier->END  END    parallel_analysis
                                                                      |
                                                              insight_generator
                                                                      |
                                                              report_builder
                                                                      |
                                                              [BACKTEST?]
                                                               |      |
                                                              END   notifier->END
```

### Conditional Edges

1. **after_anomaly_detector:** A0 data gap alerts bypass triage and analysis, go directly to `report_builder`
2. **should_continue_analysis:** After triage, proceed to `parallel_analysis` only if `alert_triggered=True`, else END
3. **should_notify:** After `report_builder`, skip notifier in BACKTEST mode, else proceed to `notifier`

### Agent Details

| # | Agent | File | LLM? | Purpose |
|---|-------|------|-------|---------|
| 1 | orchestrator | `backend/agents/orchestrator.py` | No | Validates inputs, sets execution plan |
| 2 | data_fetcher | `backend/agents/data_fetcher.py` + `data_fetcher_real.py` | No | Loads current + 7-week baseline metrics. Real parquet first, synthetic fallback |
| 3 | data_validator | `backend/agents/data_validator.py` | No | Schema validation, gap detection (A0), delta computation |
| 4 | anomaly_detector | `backend/agents/anomaly_detector.py` | Optional (Haiku) | Z-score analysis, threshold comparison with consecutive-hours validation |
| 5 | triage_classifier | `backend/agents/triage_classifier.py` | No | Classifies as TRAFFIC_DRIVEN, COVERAGE_DRIVEN, MIXED, or REVENUE_ONLY |
| 6a | contributor_analyzer | `backend/agents/contributor_analyzer.py` | Optional (Haiku) | Per-publisher contribution to revenue drop |
| 6b | geo_analyzer | `backend/agents/geo_analyzer.py` | Optional (Haiku) | Per-geo-cluster (ITA/ES/OTHER) breakdown |
| 6c | environment_splitter | `backend/agents/environment_splitter.py` | No | Per-environment (WEB/AMP/APP) metrics + AMP drift detection |
| 7 | insight_generator | `backend/agents/insight_generator.py` | Optional (Sonnet) | Cross-dimensional correlation, prioritized findings |
| 8 | report_builder | `backend/agents/report_builder.py` | Optional (Haiku) | Alert ID generation, JSON payload, markdown report |
| 9 | notifier | `backend/agents/notifier.py` | No | SQLite save (sync), Slack + email delivery (ThreadPoolExecutor) |

**Parallel Analysis (6a/6b/6c):** Wrapped in `run_parallel_analyzers()` in `backend/workflow/graph.py`. Currently runs sequentially (no shared state conflicts). Each writes to its own state keys (`contributors`, `geo_breakdown`, `environment_split`).

### AlertState (TypedDict)

Defined in `backend/workflow/state.py`. Key fields flow through the pipeline:

- **Input:** `trigger_type` (A1/A2/A3), `timestamp`, `channel_group` (GOOGLE/OPEN_BIDDING), `mode` (LIVE/BACKTEST)
- **Data:** `current_metrics`, `baseline_metrics`, `delta`, `historical_stats`
- **Results:** `validation_status`, `alert_triggered`, `alert_rule`, `severity`, `z_score`, `confidence`, `triage_label`, `contributors`, `geo_breakdown`, `environment_split`
- **Output:** `insights`, `alert_payload`, `markdown_report`, `delivery_status`
- **Metadata:** `execution_start`, `execution_errors`, `data_source`

## API Layer

### Router Structure

| Router | Prefix | File | Auth | Purpose |
|--------|--------|------|------|---------|
| `router` | `/api` | `backend/api/routes.py` | Required | Alerts CRUD, backtest, metrics, health |
| `publisher_router` | `/api/publishers` | `backend/api/publisher_routes.py` | Required | Top publishers, weekly KPIs, eCPM analysis, recurring patterns |
| `admin_router` | `/api/admin` | `backend/api/admin_routes.py` | Required | Data source config, alerting rules CRUD |
| `auth_router` | `/auth` | `backend/api/auth.py` | None | Google OAuth login/callback/logout/me |

### Alert Endpoints

- `GET /api/alerts` — List with filters (severity, status, channel, date range) + pagination
- `GET /api/alerts/{id}` — Full detail with parsed JSON blob fields + events
- `GET /api/alerts/{id}/trend` — 7-day revenue trend from daily_channel parquet
- `POST /api/alerts/{id}/ack` — Acknowledge (OPEN -> ACK)
- `POST /api/alerts/{id}/resolve` — Resolve (any -> RESOLVED)
- `POST /api/alerts/{id}/recheck` — Schedule recheck (1h from now)
- `POST /api/alerts/{id}/comment` — Add comment event

### Publisher Endpoints

- `GET /api/publishers/top` — Top N publishers by revenue (year param)
- `GET /api/publishers/{id}/weekly-kpis` — Weekly KPI time series with seasonal annotations and optional YoY comparison
- `GET /api/publishers/{id}/ecpm-analysis` — eCPM seasonal analysis with optimization windows
- `GET /api/publishers/{id}/recurring-patterns` — Enriched recurring eCPM/hidden patterns with Italian business impact text

### Admin Endpoints

- `GET /api/admin/datasources` — Current config with live parquet stats
- `POST /api/admin/datasources` — Update data source config
- `POST /api/admin/datasources/test` — Test connection (parquet/Athena/GAM)
- `GET /api/admin/alerting-rules` — Current alerting rules as JSON
- `PUT /api/admin/alerting-rules` — Update rules, validate, persist YAML, reload singleton

### Rate Limiting

All endpoints use `slowapi` rate limiter (configured in `backend/api/rate_limit.py`). Typical limits: 60/min for reads, 30/min for mutations, 5/hour for backtest, 10/hour for admin writes.

### Authentication

Defined in `backend/api/auth.py`. Two modes:
- **Development:** Auth bypassed entirely. `require_auth` returns a hardcoded user.
- **Production:** Google OAuth via `authlib`. Only `@adkaora.com` emails allowed. In-memory session store with 24h TTL. Session cookie (`session_id`, httponly, secure in prod).

## Database

**Engine:** SQLite 3 with WAL journal mode
**Location:** `data/vna_alerts.db` (configurable via `VNA_DB_PATH` env var)
**Connection:** Thread-local via `threading.local()`, context manager with auto-commit/rollback (`backend/db/database.py`)

### Tables

| Table | File | Purpose |
|-------|------|---------|
| `alerts` | `backend/db/models.py:118` | Core alert records with revenue/baseline/delta and JSON blob columns |
| `alert_events` | `backend/db/models.py:142` | ACK/RESOLVE/RECHECK/COMMENT audit trail |
| `recheck_queue` | `backend/db/models.py:154` | Scheduled recheck jobs (PENDING/COMPLETED/FAILED) |
| `pipeline_runs` | `backend/db/models.py:165` | Execution logs (run_id, status, duration, LLM usage) |
| `backtest_results` | `backend/db/models.py:183` | Backtest metadata + alerts_json blob |

### Indexes

- `idx_alerts_timestamp`, `idx_alerts_status`, `idx_alerts_severity` on `alerts`
- `idx_pipeline_runs_created` on `pipeline_runs`

### JSON Blob Fields

Alert detail data is stored as JSON strings in the `alerts` table: `contributors_json`, `geo_breakdown_json`, `environment_split_json`, `insights_json`. Parsed to Python objects at API response time in `routes.py:get_alert()`.

### Migration

`backend/db/database.py:_migrate_alerts_check_constraint()` handles adding `A0` to the `alert_rule` CHECK constraint via rename-create-copy-drop pattern (SQLite limitation).

## Data Sources

### Parquet Files (Primary)

Located in `data/baseline/`:

| File | Key | Rows | Date Range |
|------|-----|------|------------|
| `hourly_aggregated.parquet` | timestamp, channel_group, publisher_id, geo_cluster, environment | ~740K | Jan 2024 - Jan 2026 |
| `daily_channel_aggregated.parquet` | date, channel_group, publisher_id | ~650K | Jan 2024 - Jan 2026 |
| `daily_adrequests_aggregated.parquet` | date, publisher_id, geo_cluster, environment | ~360K | Jan 2024 - Jan 2026 |

All parquet files are loaded into memory with module-level caching and configurable TTL (`data_sources.cache_ttl_hours` in YAML config, default 24h).

### Seasonal/Pattern Data

Located in `data/seasonal/`:

| File | Purpose |
|------|---------|
| `ecpm-seasonal-analysis.json` | 15 seasonal periods with week-to-period mapping |
| `enriched-recurring-patterns.json` | Per-publisher recurring eCPM, hidden, and danger zone patterns |
| `optimization-windows-enriched.json` | Per-publisher optimization windows with driver labels |

### External Connectors (Future)

| Connector | File | Status |
|-----------|------|--------|
| AWS Athena | `backend/connectors/athena.py` | Implemented, not connected (needs AWS credentials) |
| Google Ad Manager | `backend/connectors/gam.py` | Implemented, not connected (needs GAM credentials) |

**Fallback chain:** Athena -> GAM -> Parquet -> BLOCKED (in LIVE mode, no synthetic fallback)

### Data Source Selection

Configured via `data/datasource_config.json` (managed by admin API). The `active_source` field determines which connector the `data_fetcher_real` agent tries first.

## Frontend Structure

### Page Architecture

React Router v6 with layout wrapper. All routes wrapped in `AuthGuard`.

| Route | Page Component | File |
|-------|---------------|------|
| `/dashboard` | `DashboardPage` | `frontend/src/pages/DashboardPage.tsx` |
| `/alerts` | `AlertsListPage` | `frontend/src/pages/AlertsListPage.tsx` |
| `/alerts/:alertId` | `AlertDetailPage` | `frontend/src/pages/AlertDetailPage.tsx` |
| `/publishers` | `PublishersPage` | `frontend/src/pages/PublishersPage.tsx` |
| `/publishers/:publisherId` | `PublisherDetailPage` | `frontend/src/pages/PublisherDetailPage.tsx` |
| `/backtest` | `BacktestPage` | `frontend/src/pages/BacktestPage.tsx` |
| `/health` | `HealthPage` | `frontend/src/pages/HealthPage.tsx` |
| `/admin/datasources` | `DataSourcesPage` | `frontend/src/pages/AdminPage.tsx` |
| `/admin/rules` | `AlertingRulesPage` | `frontend/src/pages/AdminPage.tsx` |
| `/docs/operativo` | `OperationalDocsPage` | `frontend/src/pages/DocsPage.tsx` |
| `/docs/tecnico` | `TechnicalDocsPage` | `frontend/src/pages/DocsPage.tsx` |

### Component Organization

```
frontend/src/components/
├── alerts/            # Alert detail sections (Revenue, Triage, Contributors, Geo, Env, Insights, Cache)
├── auth/              # AuthGuard (Google OAuth wrapper)
├── charts/            # Recharts visualizations (RevenueTrend, GeoBreakdownPie, EnvironmentBar)
├── dashboard/         # Dashboard-specific (Stats, Filter, Table, RevenueStatus24h)
├── layout/            # App shell (AppLayout, Header, Sidebar, PageContainer)
└── ui/                # Reusable primitives (Badge, Button, Card, MetricCard, Skeleton, AlertBox, DeltaIndicator, DataTable)
```

### Data Fetching

All API calls via TanStack Query hooks in `frontend/src/api/client.ts`:

- `useAlerts(filters)` — Alert list with 30s auto-refetch
- `useAlert(id)` — Single alert detail
- `useAlertTrend(id)` — 7-day trend data
- `useHealth()` — Health status with 60s auto-refetch
- `useTopPublishers(year, limit)` — Publisher ranking
- `usePublisherWeeklyKpis(id, year)` — Weekly KPI series
- `usePublisherEcpmAnalysis(id, year)` — eCPM seasonal analysis
- `usePublisherRecurringPatterns(id)` — Recurring patterns
- `useRevenueStatus24h(date)` — Hourly revenue status
- `useAckAlert()`, `useResolveAlert()`, `useRecheckAlert()`, `useAddComment()` — Mutation hooks
- `useRunBacktest()` — Start backtest
- `useDataSources()`, `useUpdateDataSources()`, `useTestDataSource()` — Admin hooks
- `useAlertingRules()`, `useUpdateAlertingRules()` — Rules management hooks

Base URL: `/api` (proxied to backend:8000 in dev via Vite).

### Types

- `frontend/src/types/alert.ts` — Alert, AlertSummary, Contributor, GeoBreakdown, EnvironmentMetrics, AlertInsights, etc.
- `frontend/src/types/publisher.ts` — PublisherSummary, PublisherDetail, EcpmAnalysis, RecurringPatternsResponse

## Scheduler

Defined in `backend/scheduler/scheduler.py`. Uses `AsyncIOScheduler` from APScheduler with UTC timezone.

### Jobs

| Job ID | Schedule | Function | Purpose |
|--------|----------|----------|---------|
| `alerting_cycle` | Every 2h | `run_alerting_cycle()` | Run A1 + A3 checks for all channels |
| `drift_cycle` | Every 6h | `run_drift_cycle()` | Run A2 drift checks for all channels |
| `recheck_queue` | Every 5min | `check_recheck_queue()` | Process pending rechecks |

Each cycle iterates over configured channels (GOOGLE, OPEN_BIDDING), invokes `run_pipeline()`, and records the result in `pipeline_runs`.

### Lifecycle

Started in FastAPI `lifespan` context. Graceful shutdown via `scheduler.shutdown(wait=True)`. Also handles `SIGTERM` for graceful container stops.

## Backtest

**Entry point:** `POST /api/backtest` -> `BackgroundTasks` -> `BacktestRunner.run()`

**Files:**
- `backend/backtest/runner.py` — Coordinator. Tries `BacktestRunnerReal` first, falls back to synthetic
- `backend/backtest/runner_real.py` — Real-data backtest using parquet files and the full pipeline

The backtest iterates time windows (`step_hours`), runs the pipeline for each channel at each timestamp, and collects generated alerts. Results stored in `backtest_results` table.

## Cross-Cutting Concerns

**Logging:** Structured Python logging via `backend/utils/logger.py`. Each agent/module uses `get_logger(name)`.

**LLM Retry:** Shared utility in `backend/utils/llm_retry.py` — `call_llm_with_retry()` wraps Anthropic SDK with exponential backoff (3 retries, handles rate limits, timeouts, server errors). Returns `None` on failure so callers fall back to statistical methods.

**Configuration:** Thread-safe singleton `ConfigLoader` in `backend/utils/config_loader.py`. Loads `config/alerting_rules.yaml` once, validates with Pydantic. Supports `reload()` for admin API updates.

**Error Handling:**
- Pipeline errors accumulate in `AlertState["execution_errors"]` list, never abort the pipeline
- API errors use FastAPI HTTPException with appropriate status codes
- LLM failures trigger graceful fallback to pure-Python implementations
- DB errors use context manager with rollback on exception

**Security:**
- Google OAuth with domain restriction (`@adkaora.com`)
- Rate limiting on all endpoints via slowapi
- Credentials path validation (directory traversal prevention) in admin routes
- Athena queries use parameterized values (ExecutionParameters)
- Session cookies: httponly, secure (in prod), samesite=lax
- CORS restricted to frontend URL in production
- `SESSION_SECRET` fail-fast check in production

---

*Architecture analysis: 2026-02-18*

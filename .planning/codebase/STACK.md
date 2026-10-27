# Technology Stack

**Analysis Date:** 2026-02-18

## Languages

**Primary:**
- Python 3.11 - Backend API, LangGraph agents, data processing, scripts
- TypeScript ~5.9.3 - Frontend React application (`frontend/src/`)

**Secondary:**
- SQL (SQLite dialect) - Database schema and queries (`backend/db/models.py`)
- YAML - Configuration (`config/alerting_rules.yaml`)
- Bash - DevOps scripts (`scripts/backup_db.sh`, `scripts/run_full_integration.sh`)

## Runtime

**Backend:**
- Python 3.11 (pinned in `Dockerfile`: `python:3.11-slim`)
- Uvicorn ASGI server v0.34.0 with single worker (prevents duplicate scheduler)

**Frontend:**
- Node.js 20 (pinned in `Dockerfile`: `node:20-slim`)
- Vite 7.3.1 dev server with proxy to backend at `localhost:8000`

**Package Managers:**
- pip (backend) - `backend/requirements.txt` with pinned versions
- npm (frontend) - `frontend/package-lock.json` present
- No Python lockfile (pip-compile/Poetry not used)

## Frameworks

### Backend

**Core:**
- FastAPI 0.115.6 - REST API framework (`backend/main.py`)
- Pydantic 2.10.4 + pydantic-settings 2.7.1 - Data validation and config models (`backend/db/models.py`, `backend/utils/config_loader.py`)
- LangGraph 0.2.65 - Multi-agent workflow orchestration (`backend/workflow/graph.py`)
- LangChain Core 0.3.29 + langchain-anthropic 0.3.4 - LLM integration layer

**Scheduling:**
- APScheduler 3.11.0 (AsyncIOScheduler) - 3 recurring jobs: A1+A3 every 2h, A2 drift every 6h, recheck every 5min (`backend/scheduler/scheduler.py`)

**Authentication:**
- Authlib 1.3.2 - Google OAuth integration (`backend/api/auth.py`)
- itsdangerous 2.2.0 - Session token signing
- Starlette SessionMiddleware - Cookie-based sessions

**Rate Limiting:**
- slowapi 0.1.9 - Per-IP rate limiting (`backend/api/rate_limit.py`)

### Frontend

**Core:**
- React 19.2.0 - UI framework
- React Router DOM 7.13.0 - Client-side routing
- TanStack React Query 5.90.21 - Server state management and caching (`frontend/src/api/client.ts`)

**Styling:**
- Tailwind CSS 4.1.18 - Utility-first CSS (via `@tailwindcss/vite` plugin)
- class-variance-authority 0.7.1 - Component variant management
- clsx 2.1.1 + tailwind-merge 3.4.0 - Conditional class utilities (`frontend/src/lib/utils.ts`)

**Charts:**
- Recharts 3.7.0 - Data visualization (revenue trends, geo pie charts, environment bar charts)

**Icons:**
- lucide-react 0.563.0 - Icon library

**Build:**
- Vite 7.3.1 - Bundler and dev server (`frontend/vite.config.ts`)
- @vitejs/plugin-react 5.1.1 - React Fast Refresh
- TypeScript ~5.9.3 - Type checking (strict mode, `frontend/tsconfig.app.json`)

**Linting:**
- ESLint 9.39.1 (flat config) (`frontend/eslint.config.js`)
- typescript-eslint 8.48.0 - TypeScript rules
- eslint-plugin-react-hooks 7.0.1 - Hooks rules
- eslint-plugin-react-refresh 0.4.24 - HMR validation

## Database

**Engine:** SQLite 3 with WAL journal mode (`backend/db/database.py`)
- Connection: thread-local with `check_same_thread=False`
- Pragmas: `journal_mode=WAL`, `busy_timeout=5000`, `foreign_keys=ON`
- DB path: `data/vna_alerts.db` (configurable via `VNA_DB_PATH` env var)
- No ORM - raw `sqlite3` module with `Row` factory
- Migration: manual rename-create-copy-drop pattern for schema changes

**Tables:**
- `alerts` - Core alert records with JSON columns for structured data
- `alert_events` - Audit trail (ACK, RESOLVE, RECHECK, COMMENT)
- `recheck_queue` - Scheduled re-evaluation queue
- `pipeline_runs` - Execution history for observability
- `backtest_results` - Historical backtest outputs

**Async support:**
- aiosqlite 0.20.0 listed in deps (not actively used; sync sqlite3 in practice)

## Data Processing

**Libraries:**
- Pandas 2.2.3 - DataFrame operations for metrics aggregation and analysis
- PyArrow 18.1.0 - Parquet file I/O (read-only, no writes)
- DuckDB 1.1.3 - Listed in deps (available for analytical queries)
- NumPy (transitive via Pandas) - Numerical operations, z-score calculations

**Data Files (read-only, in `data/baseline/`):**
- `hourly_aggregated.parquet` - 5.7 MB, ~740K rows (hourly granularity)
- `daily_channel_aggregated.parquet` - 3.6 MB, ~650K rows (daily by channel)
- `daily_adrequests_aggregated.parquet` - 4.2 MB, ~360K rows (daily ad requests)
- Date range: January 2024 - January 2026

**Data caching:** In-memory DataFrame cache with TTL in `backend/agents/data_fetcher_real.py`

## AI / LLM Integration

**LLM Provider:**
- Anthropic Claude via `langchain-anthropic` 0.3.4
- Direct Anthropic SDK calls in `backend/utils/llm_retry.py` with exponential backoff (3 retries, handles RateLimit/Timeout/5xx)
- Used by: insight_generator agent (template-based fallback when LLM unavailable)

**Agent Framework:**
- LangGraph 0.2.65 - StateGraph with 9 nodes (11 logical agents, 3 run in parallel analysis node)
- MemorySaver checkpointer for thread-level state
- `AlertState` TypedDict for typed state passing (`backend/workflow/state.py`)

**Pipeline Flow:**
```
orchestrator → data_fetcher → data_validator → anomaly_detector
  → [A0 bypass → report_builder]
  → triage_classifier → [no alert → END]
  → parallel_analysis (contributor + geo + env) → insight_generator
  → report_builder → [BACKTEST → END] → notifier → END
```

## External Service Connectors (Future)

**AWS Athena** (`backend/connectors/athena.py`):
- boto3 1.36.4 + pyathena 3.12.2
- Parameterized queries with input validation (whitelist channel groups, regex dates, identifier validation)
- Retry: max 2 attempts, exponential backoff, 30s timeout
- Currently disabled (`data/datasource_config.json`: `enabled: false`)

**Google Ad Manager** (`backend/connectors/gam.py`):
- google-auth + google-api-python-client (optional import)
- Service account credentials, report-based data extraction
- Currently disabled; TODO markers for field mapping

**Notifications:**
- slack-sdk 3.34.0 - Slack webhook integration (placeholder in notifier agent)
- aiosmtplib 3.0.2 - Email notifications (placeholder)

## HTTP Client

- httpx 0.28.1 - Async HTTP client (available for external calls)

## Configuration Management

**Primary config:** `config/alerting_rules.yaml`
- Loaded via singleton `ConfigLoader` with thread-safe lazy init (`backend/utils/config_loader.py`)
- Validated into `AlertingConfig` Pydantic model (nested models for each section)
- Path override via `VNA_CONFIG_PATH` env var

**Data source config:** `data/datasource_config.json`
- Active source selection (parquet/athena/gam)
- Athena and GAM connection parameters

**Environment:**
- python-dotenv 1.0.1 - Loads `.env` file at startup (`backend/main.py`)
- `.env.example` present for reference
- Key env vars: `ENVIRONMENT`, `SESSION_SECRET`, `FRONTEND_URL`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `ANTHROPIC_API_KEY`, `VNA_DB_PATH`, `VNA_CONFIG_PATH`, `ALLOWED_DOMAIN`, `OAUTH_REDIRECT_URI`

## Logging

- Python stdlib `logging` with custom format (`backend/utils/logger.py`)
- Format: `%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s`
- Noisy loggers suppressed: uvicorn.access, httpx, boto3, botocore → WARNING level
- python-json-logger 2.0.0+ in root `requirements.txt` (not actively used in backend)

## Infrastructure

**Docker:**
- Multi-stage Dockerfile (`Dockerfile`):
  - Stage 1: `node:20-slim` builds frontend with `npm ci && npm run build`
  - Stage 2: `python:3.11-slim` runs backend, serves frontend from `frontend/dist/`
- `docker-compose.yml`: single `sentinel` service on port 8000, `.env` file, `data/` volume mount, `unless-stopped` restart

**Production:**
- Single uvicorn worker (required by APScheduler to avoid duplicate jobs)
- CORS restricted to `FRONTEND_URL` in production
- SPA serving: FastAPI mounts `frontend/dist/assets` and serves `index.html` for all non-API routes
- Session secret validation: fails fast if `SESSION_SECRET` is default in production

**Development:**
- Backend: `uvicorn backend.main:app --reload` on port 8000
- Frontend: `vite` dev server with proxy to backend (`/api` and `/auth` routes)
- Auth bypassed in development mode (returns hardcoded user)

## Scripts

**Data processing (`scripts/`):**
- `aggregate_parquet.py` - Pre-aggregate raw data into baseline parquet files
- `generate_real_alerts.py` / `regenerate_alerts.py` - Generate alerts from real parquet data
- `seed_alerts_from_parquet.py` - Seed DB with parquet-derived alerts
- `generate_seasonal_analysis.py` - Compute eCPM seasonal patterns
- `audit_data_coherence.py` - Data quality validation
- `translate_patterns_to_italian.py` - Localize text patterns
- `verify_data_paths.py` - Verify data file accessibility
- `test_integration.py` - Integration test suite
- `backup_db.sh` - SQLite backup script (to `data/backups/`)
- `run_full_integration.sh` - End-to-end integration runner

## Development Tools

**Python (listed in root `requirements.txt`, not backend):**
- black >=23.0.0 - Code formatter
- ruff >=0.0.280 - Linter
- mypy >=1.5.0 - Type checker
- pytest >=7.4.0 + pytest-asyncio >=0.21.0 - Testing

**Frontend:**
- ESLint 9 (flat config) with TypeScript + React rules
- TypeScript strict mode with `noUnusedLocals`, `noUnusedParameters`

## Dependency Notes

**Version pinning:**
- `backend/requirements.txt`: Exact versions (e.g., `fastapi==0.115.6`) - production deps
- Root `requirements.txt`: Minimum versions (e.g., `fastapi>=0.100.0`) - development reference
- `frontend/package.json`: Caret ranges (e.g., `^19.2.0`)

**Notable inclusions:**
- DuckDB 1.1.3 in backend deps but no observed usage in source code
- python-json-logger in root deps but custom logging format used instead
- aiosqlite in backend deps but synchronous sqlite3 used in practice

---

*Stack analysis: 2026-02-18*

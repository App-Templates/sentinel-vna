# External Integrations

**Analysis Date:** 2026-02-18

## APIs & External Services

### AI / LLM

**Anthropic Claude API:**
- Used for: Natural language insight generation in alerting pipeline
- SDK/Client: `langchain-anthropic` 0.3.4 (LangGraph agents) + direct `anthropic` SDK (`backend/utils/llm_retry.py`)
- Auth: `ANTHROPIC_API_KEY` env var
- Retry: 3 attempts with exponential backoff (1s base), handles RateLimit/Timeout/5xx
- Fallback: Template-based insights when LLM unavailable
- Status: **Active** (optional - system works without it)

### Cloud Data

**AWS Athena** (`backend/connectors/athena.py`):
- Used for: Primary production data source (revenue/bacino/coverage metrics)
- SDK/Client: `boto3` 1.36.4 + `pyathena` 3.12.2
- Auth: AWS credentials (IAM role or env vars `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
- Config: `data/datasource_config.json` → `athena` section (region, database, workgroup, s3_output, table_name)
- Query: Parameterized SQL with whitelist validation (channel groups, date formats, identifiers)
- Retry: 2 total attempts (1 retry), 30s timeout, exponential backoff
- Status: **Not connected** (disabled in config, no AWS credentials)

**Google Ad Manager API** (`backend/connectors/gam.py`):
- Used for: Fallback data source when Athena unavailable
- SDK/Client: `google-auth` + `google-api-python-client` (optional import)
- Auth: Service account JSON credentials file
- Config: `data/datasource_config.json` → `gam` section (network_code, credentials_path, timeout_seconds)
- API Version: v202405
- Status: **Not connected** (disabled in config, TODO markers for field mapping)

### Notifications

**Slack** (`backend/agents/notifier.py`):
- Used for: Alert delivery to ops team
- SDK: `slack-sdk` 3.34.0
- Auth: Slack webhook URL or bot token (env var)
- Status: **Placeholder** (notifier agent structure exists, no active integration)

**Email / SMTP** (`backend/agents/notifier.py`):
- Used for: Alert delivery via email
- SDK: `aiosmtplib` 3.0.2
- Auth: SMTP credentials (env vars)
- Status: **Placeholder** (listed in deps, not wired)

### Authentication

**Google OAuth 2.0** (`backend/api/auth.py`):
- Used for: User authentication (production only)
- SDK: `authlib` 1.3.2 (Starlette OAuth integration)
- Auth: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` env vars
- Flow: Authorization code grant → callback → session cookie
- Domain restriction: Only `@adkaora.com` emails (configurable via `ALLOWED_DOMAIN`)
- Session: In-memory dict store (24h TTL), cookie-based (`session_id`, httponly, samesite=lax)
- Status: **Active in production** (bypassed in development → hardcoded dev user)

## Data Storage

### Primary Database

**SQLite 3 with WAL:**
- Location: `data/vna_alerts.db` (configurable via `VNA_DB_PATH`)
- Client: Python stdlib `sqlite3` (no ORM)
- Connection: Thread-local, `check_same_thread=False`
- Pragmas: WAL journal, 5s busy timeout, foreign keys ON
- Backups: `scripts/backup_db.sh` → `data/backups/`
- Tables: `alerts`, `alert_events`, `recheck_queue`, `pipeline_runs`, `backtest_results`

### File-based Data

**Parquet Files (read-only):**
- Location: `data/baseline/`
- Files:
  - `hourly_aggregated.parquet` (5.7 MB, ~740K rows)
  - `daily_channel_aggregated.parquet` (3.6 MB, ~650K rows)
  - `daily_adrequests_aggregated.parquet` (4.2 MB, ~360K rows)
- Reader: PyArrow 18.1.0 via Pandas `pd.read_parquet()`
- Caching: In-memory DataFrame cache with TTL (`backend/agents/data_fetcher_real.py`)

**Seasonal Analysis Data:**
- Location: `data/seasonal/` directory
- Format: JSON files with precomputed eCPM seasonal patterns

### Configuration Store

**Data Source Config:**
- Location: `data/datasource_config.json`
- Content: Active source selection, Athena params, GAM params, scheduler intervals
- Updated via: Admin API (`backend/api/admin_routes.py`)

**File Storage:**
- Local filesystem only (no S3/cloud storage for application data)

**Caching:**
- In-memory DataFrame cache for parquet data (TTL-based)
- In-memory session store for auth (`backend/api/auth.py`)
- No Redis or external cache

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry, Datadog, or similar)

**Logging:**
- Python stdlib `logging` to stdout (`backend/utils/logger.py`)
- Format: `%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s`
- Pipeline runs recorded to `pipeline_runs` table (duration, errors, LLM usage)

**Health Check:**
- `GET /api/health` endpoint (DB connectivity, scheduler status, data source availability)
- Frontend health page at `/health`

## CI/CD & Deployment

**Hosting:**
- Docker (single container via `docker-compose.yml`)
- Target: any Docker-compatible host

**CI Pipeline:**
- None detected (no `.github/workflows/`, `.gitlab-ci.yml`, or similar)

**Build:**
- Multi-stage Docker build: frontend npm build → backend pip install → single image
- Production: `uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1`

## Environment Configuration

**Required env vars (production):**
- `SESSION_SECRET` - Must be set to a secure value (fail-fast validation at startup)
- `GOOGLE_CLIENT_ID` - Google OAuth client ID
- `GOOGLE_CLIENT_SECRET` - Google OAuth client secret

**Optional env vars:**
- `ENVIRONMENT` - `development` (default) or `production`
- `FRONTEND_URL` - Frontend URL for CORS/redirects (default: `http://localhost:5173`)
- `ANTHROPIC_API_KEY` - Enables LLM-based insights
- `VNA_DB_PATH` - Custom database location
- `VNA_CONFIG_PATH` - Custom alerting_rules.yaml path
- `ALLOWED_DOMAIN` - OAuth email domain restriction (default: `adkaora.com`)
- `OAUTH_REDIRECT_URI` - OAuth callback URL (default: `http://localhost:8000/auth/callback`)
- `AWS_*` - AWS credentials for Athena connector

**Secrets location:**
- `.env` file (loaded via python-dotenv at startup)
- `.env.example` present as template

## Webhooks & Callbacks

**Incoming:**
- `GET /auth/callback` - Google OAuth callback endpoint

**Outgoing:**
- None currently active (Slack/email notification placeholders)

## Data Flow: Fallback Chain

The system uses a prioritized data source chain:

1. **Athena** (primary, production) → returns DataFrame or None
2. **GAM** (fallback) → returns DataFrame or None
3. **Parquet** (local fallback) → always available
4. **BLOCKED** - No synthetic data generation in LIVE mode

Implementation: `backend/agents/data_fetcher_real.py` attempts each source in order.

---

*Integration audit: 2026-02-18*

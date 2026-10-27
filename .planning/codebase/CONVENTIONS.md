# Coding Conventions

**Analysis Date:** 2026-02-18

## Naming Patterns

**Files (Python):**
- Snake_case for all Python modules: `anomaly_detector.py`, `config_loader.py`, `publisher_routes.py`
- `__init__.py` in every package (all empty, used only for package recognition)
- Scripts in `scripts/` use snake_case with descriptive verbs: `regenerate_alerts.py`, `audit_data_coherence.py`

**Files (TypeScript):**
- PascalCase for React components: `AlertDetailPage.tsx`, `DashboardStats.tsx`, `ErrorBoundary.tsx`
- camelCase for hooks: `useAlertFilters.ts`, `useAutoRefresh.ts`
- camelCase for utilities: `client.ts`, `utils.ts`
- camelCase for type definition files: `alert.ts`, `publisher.ts`

**Functions (Python):**
- snake_case for all functions: `get_alerts()`, `anomaly_detector_agent()`, `_load_hourly_data()`
- Private helpers prefixed with underscore: `_row_to_dict()`, `_statistical_fallback()`, `_finalize_window()`
- Agent entry points follow `{name}_agent(state: AlertState) -> AlertState` pattern

**Functions (TypeScript):**
- camelCase for utility functions: `formatCurrency()`, `formatTimestamp()`, `fetchJSON()`
- PascalCase for React components: `DashboardPage()`, `AlertsTable()`, `ErrorBoundary`
- Hook functions always start with `use`: `useAlerts()`, `useAlertFilters()`, `useAutoRefresh()`

**Variables (Python):**
- snake_case: `_hourly_cache`, `total_revenue`, `baseline_revs`
- Module-level constants in UPPER_SNAKE: `BASE_DIR`, `HOURLY_PARQUET`, `DAILY_ADREQUESTS_PARQUET`
- Global mutable state prefixed with underscore: `_hourly_cache`, `_adrequests_cache`, `_scheduler`

**Variables (TypeScript):**
- camelCase: `queryClient`, `alertId`, `pagedData`
- Constants in UPPER_SNAKE for mappings: `FILTER_KEY_MAP`, `BASE_URL`

**Types (Python):**
- Enums: PascalCase with UPPER_SNAKE values: `Severity.P0`, `AlertStatus.OPEN`, `ChannelGroup.GOOGLE`
- Pydantic models: PascalCase with `Model` or `Config` suffix: `AlertModel`, `AlertingConfig`, `SeverityLevel`
- TypedDict: PascalCase: `AlertState`

**Types (TypeScript):**
- Type aliases: PascalCase: `Severity`, `AlertStatus`, `ChannelGroup`, `TriageLabel`
- Interfaces: PascalCase: `Alert`, `AlertSummary`, `Contributor`, `PublisherDetail`
- Union types for string literals: `type Severity = 'P0' | 'P1' | 'P2'`

## Code Style

**Formatting (Python):**
- No `.prettierrc` or `pyproject.toml` formatting config detected in project root
- `requirements.txt` lists `black>=23.0.0` and `ruff>=0.0.280` as dev dependencies, but no config files
- Indentation: 4 spaces (standard Python)
- Line length: generally under 120 chars, no enforced limit detected
- Use `from __future__ import annotations` in most backend modules for forward references

**Formatting (TypeScript):**
- No Prettier config detected (no `.prettierrc`)
- Indentation: 2 spaces (Vite default)
- Single quotes for strings (consistent throughout frontend)
- Semicolons used at end of type declarations, generally omitted in component files

**Linting (Python):**
- `ruff>=0.0.280` in requirements but no `ruff.toml` or `pyproject.toml` config
- `mypy>=1.5.0` listed but no `mypy.ini` or `pyproject.toml` config
- No pre-commit hooks detected

**Linting (TypeScript):**
- ESLint 9 flat config at `frontend/eslint.config.js`
- Plugins: `@eslint/js`, `typescript-eslint`, `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`
- TypeScript strict mode enabled in `frontend/tsconfig.app.json`
- Strict checks: `noUnusedLocals`, `noUnusedParameters`, `noFallthroughCasesInSwitch`

## Import Organization

**Python:**
1. Standard library (`import os`, `import json`, `from datetime import datetime`)
2. Third-party packages (`import pandas as pd`, `from fastapi import APIRouter`)
3. Internal modules (`from backend.utils.logger import get_logger`, `from backend.db.operations import ...`)
- No `isort` config detected, but imports follow this order consistently
- `from __future__ import annotations` always first when present

**TypeScript:**
1. React/library imports (`import { useState } from 'react'`, `import { useQuery } from '@tanstack/react-query'`)
2. Internal components (`import { Card } from '../components/ui/Card'`)
3. Internal hooks/utils (`import { useAlertFilters } from '../hooks/useAlertFilters'`)
4. Types (using `import type` syntax): `import type { Alert, AlertSummary } from '../types/alert'`
- Path aliases: None configured. All imports use relative paths (`../`, `../../`)

## Error Handling

**Python Backend:**
- FastAPI `HTTPException` for API errors with consistent status codes:
  - 400: Invalid input / state violations (`Cannot ACK alert in {status} state`)
  - 401: Not authenticated (via `require_auth` dependency)
  - 403: Domain restriction (OAuth callback)
  - 404: Resource not found (`Alert not found`, `Backtest not found`)
  - 422: Validation error (Pydantic, alerting rules update)
  - 429: Rate limit exceeded (custom handler in `backend/main.py`)
  - 500: Internal errors (config read/write)
  - 503: Data unavailable (`Hourly data not available`, `Ad requests data not available`)
- Database: `get_db()` context manager auto-commits on success, rollbacks on exception
- Agents: Catch-all `except Exception` patterns with `logger.error()` + graceful degradation
  - LLM failures fall back to statistical analysis
  - Parquet loading failures return `None` (callers handle)
- Scheduler: Each job wrapped in outer try/except to prevent scheduler crash

**TypeScript Frontend:**
- `fetchJSON()` generic wrapper handles all API calls:
  - 401 -> auto-reload page (session expired)
  - Non-ok -> throws `Error` with status message
- `ErrorBoundary` class component wraps entire app at `frontend/src/main.tsx:20`
- TanStack Query handles per-query errors: `retry: 1` default, `retry: false` for auth
- Component-level error rendering: `if (error)` checks display inline error messages

## Logging

**Framework:** Python `logging` module via custom wrapper at `backend/utils/logger.py`

**Format:** `%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s`

**Patterns:**
- Every module uses `logger = get_logger(__name__)` or `get_logger("agent.{name}")`
- Log levels used:
  - `INFO`: Normal operations (pipeline start/complete, data loaded, alert created)
  - `WARNING`: Degradation (LLM fallback, missing data, config fallback)
  - `ERROR`: Failures (pipeline crash, parquet load error, LLM failure)
- Format strings use `%s` style (not f-strings) for lazy evaluation
- Third-party loggers suppressed: `uvicorn.access`, `httpx`, `boto3`, `botocore` set to WARNING
- No structured JSON logging despite `python-json-logger` in requirements
- `exc_info=True` used for traceback in error handlers: `logger.error("...", exc, exc_info=True)`

## Comments

**When to Comment:**
- Module-level docstrings on all agent files explaining purpose, position in pipeline, and algorithm
- Inline `#` comments for non-obvious logic (threshold multipliers, time-of-day adjustments, baseline calculation)
- Section dividers using `# ---` pattern: `# ---------------------------------------------------------------------------`
- SQL DDL includes CHECK constraints documented inline

**Docstrings:**
- Google-style docstrings on public functions with Args/Returns sections
- Agent entry points have brief docstrings explaining role
- Some functions lack docstrings (internal helpers, route handlers)
- No JSDoc in TypeScript frontend code

## Function Design

**Size:**
- Backend route handlers: 10-60 lines typical
- Agent functions: 20-100 lines for main entry, with extracted helpers
- `publisher_routes.py` is the largest file (975 lines) with 5 endpoints and multiple private helpers
- Frontend components: 30-130 lines typical; `PublisherDetailPage.tsx` is largest at 1109 lines

**Parameters (Python):**
- Agent functions take single `AlertState` TypedDict and return `AlertState`
- Route functions use FastAPI `Query()` with validation (`ge`, `le`, `pattern`)
- Optional params typed as `Optional[str]` with `None` default
- Config values injected via `get_config()` singleton, not passed as params

**Parameters (TypeScript):**
- Components use typed props interfaces: `interface AlertsTableProps { data: AlertSummary[] | undefined; ... }`
- Hooks accept config objects: `useAutoRefresh({ intervalMs, enabled, onRefresh })`
- Default values for hook parameters

**Return Values (Python):**
- Agents always return `AlertState` (dict spread pattern: `{**state, "new_key": value}`)
- DB operations return specific types: `Optional[dict]`, `tuple[list, int]`, `int`, `bool`
- Routes return Pydantic response models or plain dicts

## Module Design

**Exports (Python):**
- All `__init__.py` files are empty (no re-exports)
- Each module exposes its public API through direct imports
- Agents export single entry function: `anomaly_detector_agent`, `triage_classifier_agent`, etc.

**Exports (TypeScript):**
- Named exports throughout (no default exports except `App.tsx`)
- Type files export all types/interfaces individually
- `client.ts` exports all API hooks as named functions
- No barrel files (`index.ts` re-exports)

**Component Organization:**
- `frontend/src/components/ui/` - Reusable primitives (Badge, Card, Button, DataTable, Skeleton)
- `frontend/src/components/dashboard/` - Dashboard-specific composed components
- `frontend/src/components/alerts/` - Alert detail sections (Revenue, Triage, Contributors, Geo, Env, Insights)
- `frontend/src/components/charts/` - Recharts wrappers (RevenueTrendChart, GeoBreakdownPieChart)
- `frontend/src/components/layout/` - App shell (Header, Sidebar, PageContainer, AppLayout)
- `frontend/src/pages/` - Route-level page components

---

*Convention analysis: 2026-02-18*

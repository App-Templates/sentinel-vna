# Auditor B — Security & Contract Audit — Phase 10

## Verdict
MINOR ISSUES (no blockers; one notable operational hazard; one persistent data-exposure finding to assess against threat model)

---

## NEW findings (not in MAJOR-01..03 or WR-01..04)

---

### [MEDIUM] — Live production SQLite DB and multiple backup snapshots tracked in git

- **File:line:** `data/vna_alerts.db` (committed initial commit `0b17977`); `data/vna_alerts.db.pre-phase10.bak` (committed `de9e79e`); also present: `data/alerts.db`, `data/vna_alerts.db.bak`, `data/vna_alerts.db.bak.prewave2`, `data/vna_alerts.db.pre-phase08.bak`, `data/vna_alerts.db.pre-phase09.bak` — all tracked per `git ls-files data/`
- **Problem:** `.gitignore` covers `*.db-shm` and `*.db-wal` (WAL sidecars) and `Thumbs.db` but does NOT cover `*.db` or `data/*.db`. The live DB and every phase backup snapshot have been committed to git history from the initial commit onwards. The Phase 10 mitigation commit `de9e79e` explicitly adds a new `.pre-phase10.bak`. Git history retains all prior DB snapshots even if the files are later gitignored — blobs persist in `.git/objects/`.
- **Impact:** The DB contains 438 alerts with real revenue figures, channel group labels, publisher-derived IDs, user IDs (`admin`, `yield_mgr`, `data_eng`, `support`, `ops_team`, `stefano@hej.ia`), and pipeline run metadata. Anyone with repo read access — or if the repo is ever pushed to a public remote — obtains the full operational dataset including alert history, backtest results, pipeline run counts, and any feedback/assignment records that accumulate. The phase backup blobs (`pre-phase08`, `pre-phase09`, `pre-phase10`) are permanent in git history and cannot be removed without a history rewrite (`git filter-repo`).
- **Recommended fix:**
  1. Add `data/*.db` and `data/*.bak` to `.gitignore` immediately.
  2. Remove the DB files from tracking: `git rm --cached data/vna_alerts.db data/*.bak data/alerts.db` and commit.
  3. Rewrite history to expunge the blobs: `git filter-repo --path data/vna_alerts.db --invert-paths` (and same for each bak file). This is destructive — coordinate with all clones.
  4. If the repo is or will be pushed to a remote, rotate any secrets that may exist in committed alert metadata before the rewrite.
  5. Long-term: use an out-of-repo DB path (`VNA_DB_PATH` env var already wired) so the DB is never co-located with the git tree.

---

### [MINOR] — `GET /api/health/alerts-pipeline` is auth-gated in production but designed for unauthenticated external monitors

- **File:line:** `backend/main.py:115` — `app.include_router(router, dependencies=[Depends(require_auth)])`; `backend/api/routes.py:810-833`
- **Problem:** The endpoint's docstring explicitly states it is designed to be consumed by "External monitors (UptimeRobot/synthetic probes)". UptimeRobot and equivalent synthetic probes are unauthenticated HTTP clients — they cannot present a session cookie. The endpoint is reachable only by authenticated sessions (Google OAuth cookie) in production. This creates a design-intent mismatch: the monitoring contract cannot be honoured by external monitors without either exempting the endpoint from auth or providing a bearer token scheme.
  The sibling `/api/health` has the same auth behaviour (consistent policy), so there is no inconsistency between the two health routes — both are auth-gated.
- **Impact:** External uptime monitors will receive 401 on the endpoint they are supposed to probe, defeating MONITOR-01's stated goal of enabling external synthetic probes. The internal watchdog (`silent_failure_watch.py`) calls `get_alerts_pipeline_health()` directly and is unaffected. The operational risk is that the "external probe" layer of the monitoring stack is non-functional silently.
- **Recommended fix:** Decide which model applies:
  - Option A (preferred for internal-only tool): remove the "External monitors" clause from the docstring and acknowledge the endpoint is internal-only. The watchdog covers the detection requirement.
  - Option B (honour the external-probe contract): add an unauthenticated read-only token scheme for `/api/health/alerts-pipeline` (e.g. a static `X-Monitor-Token` header checked against an env var), and explicitly exclude this path from the global `require_auth` dependency.

---

### [MINOR] — `{e!r}` in 503 detail leaks DB path and internal table names to API consumers

- **File:line:** `backend/api/routes.py:831` — `raise HTTPException(status_code=503, detail=f"health_query_failed: {e!r}")`
- **Problem:** When `get_alerts_pipeline_health()` raises (e.g. DB locked, path error, missing table), the raw Python `repr()` of the exception is included verbatim in the HTTP 503 response body. Examples of what leaks:
  - `OperationalError('no such table: alerts')` — reveals table names
  - `OperationalError('unable to open database file')` — with some SQLite bindings the path is embedded
  - `DatabaseError(...)` — any SQLite error string
  Although the endpoint is auth-gated (mitigates public exposure), authenticated operators/scripts still receive internal implementation details that should stay server-side.
- **Impact:** Low in the current auth model. If auth were ever weakened or the endpoint were exempted (see finding above), this becomes a direct info-disclosure vector: attackers learn the DB schema and file layout. Also inconsistent with the sibling `/api/health` handler which swallows all exceptions silently (`except Exception: pass`).
- **Recommended fix:** Replace `{e!r}` with a generic code:
  ```python
  raise HTTPException(status_code=503, detail="health_query_failed")
  ```
  Log the full exception server-side via `logger.exception(...)` (already present at line 827) — that is the correct place for the repr.

---

### [MINOR] — `slack_channel_override` accepts arbitrary URL with no scheme validation — config injection vector

- **File:line:** `backend/utils/config_loader.py:167` — `slack_channel_override: Optional[str] = None`; `backend/monitoring/silent_failure_watch.py:47-51`
- **Problem:** `SilentFailureMonitorConfig.slack_channel_override` is typed as `Optional[str]` with no URL scheme, domain, or pattern validation. If an attacker could write to `config/alerting_rules.yaml` (e.g. via a compromised CI/CD job, a misconfigured file permission, or a future admin UI that edits YAML), they could set `slack_channel_override` to an attacker-controlled URL. The watchdog would POST the P0 meta-alert payload (containing pipeline metrics, last alert timestamps, internal phase references) to that URL on the next firing cycle.
  The payload is low-sensitivity (counts and timestamps, no PII), but the attack channel itself is a SSRF primitive from the application server's network context — the POST goes to an arbitrary URL using the server's identity.
- **Impact:** SSRF via watchdog POST if YAML is writeable. Data exfiltration of pipeline health metadata. The attack requires YAML write access, which raises the bar — but given the DB is already tracked in git (finding above), the YAML boundary is not strong.
- **Recommended fix:** Add a Pydantic `field_validator` or use `pydantic.AnyHttpUrl`:
  ```python
  from pydantic import AnyHttpUrl
  slack_channel_override: Optional[AnyHttpUrl] = None
  ```
  Or add a regex validator restricting to `https://hooks.slack.com/...` domain:
  ```python
  @field_validator("slack_channel_override")
  @classmethod
  def validate_slack_url(cls, v):
      if v and not v.startswith("https://hooks.slack.com/"):
          raise ValueError("slack_channel_override must be a hooks.slack.com URL")
      return v
  ```

---

### [MINOR] — `webhook_url: https://hooks.slack.com/services/TEST123` committed in YAML

- **File:line:** `config/alerting_rules.yaml:154`
- **Problem:** The YAML commit contains a Slack webhook URL in the `slack_notifications.webhook_url` field: `https://hooks.slack.com/services/TEST123`. The path segment `TEST123` appears to be a placeholder but has the exact shape of a real Slack webhook token (`/services/T.../B.../XXXX`). The Phase 10 SUMMARY (10-03-SUMMARY.md:178) notes "The live smoke showed this URL returning 200" — confirming the URL is either functional or once was. A functional webhook URL committed to git is a secret in version history.
- **Impact:** If `TEST123` is a real token (even a test workspace token), any committer with repo history access can post to the Slack workspace. Slack tokens are not revocable by changing the YAML — the token must be explicitly revoked in the Slack app admin UI.
- **Recommended fix:**
  1. If `TEST123` is real: revoke the webhook immediately in Slack App → Incoming Webhooks → Revoke. Then remove from YAML and history.
  2. Replace with an explicit placeholder that cannot be mistaken for a real token: `webhook_url: ""` or `webhook_url: null`.
  3. Document that the real URL is configured via `SLACK_WEBHOOK_URL` env var only, never committed.

---

### [MINOR] — `slowapi` rate-limit is per-IP using `request.client.host` — no `ProxyHeadersMiddleware`, rate-limit is bypassable behind a reverse proxy

- **File:line:** `backend/api/rate_limit.py:6` — `limiter = Limiter(key_func=get_remote_address)`; `backend/main.py` — no `ProxyHeadersMiddleware`
- **Problem:** `get_remote_address` from slowapi resolves to `request.client.host`, which is the TCP peer address as seen by the ASGI server. Starlette does NOT trust `X-Forwarded-For` by default and does NOT populate `request.client.host` from it unless `ProxyHeadersMiddleware` (or Uvicorn's `--proxy-headers` flag with `--forwarded-allow-ips`) is configured. `backend/main.py` adds no such middleware.
  This creates two opposite failure modes depending on deployment:
  1. **Behind a reverse proxy (nginx, Cloudflare, etc.):** `request.client.host` is always the proxy's IP. All clients share one rate-limit bucket. A single automated client burns the bucket for everyone — or the limit effectively never throttles individual clients.
  2. **Direct exposure (dev/test):** `request.client.host` is the real client IP. Rate-limit works correctly per client. Adding a reverse proxy later silently breaks rate-limiting without code changes.
- **Impact:** Rate-limit bypass in the more common production topology (behind a proxy). `/api/health/alerts-pipeline` at 60/minute per proxy IP is effectively unlimited for individual clients.
- **Recommended fix:** Add `ProxyHeadersMiddleware` if behind a trusted proxy, with explicit trusted IP range:
  ```python
  from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
  app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["127.0.0.1", "10.0.0.0/8"])
  ```
  Or configure uvicorn with `--proxy-headers --forwarded-allow-ips=<proxy-ip>`. Document the deployment topology assumption. Audit: verify whether production runs behind nginx/Cloudflare and adjust accordingly.

---

### [LOW] — URLError/OSError exception repr may embed the webhook URL in log output

- **File:line:** `backend/monitoring/silent_failure_watch.py:155-162`
- **Problem:** When `urlopen` raises `URLError` or `OSError`, the exception is logged via `%s` (str representation). For standard Python `urllib` connection errors, `URLError.__str__` returns `"<urlopen error {reason}>"` and does not embed the URL. However, certain OS-level errors (e.g. `ConnectionRefusedError` wrapped in `URLError`) may include the target address in the `reason` field. Additionally, on the "all retries exhausted" path (line 162), `logger.error("send_meta_alert: all retries exhausted: %s", e)` logs `str(e)`. If the exception's `reason` field includes the full URL (possible with some `HTTPError` subclasses that set `url` attribute), the webhook secret embedded in the URL path (`/services/T.../B.../XXXX`) would appear in log files.
  Verified: `HTTPError(url, code, msg, hdrs, fp).__str__()` returns `"HTTP Error {code}: {msg}"` — the URL is NOT in the str output. For plain `URLError`, `str(e) == "<urlopen error {reason}>"` — also does not include the URL. Risk is lower than initial concern but not zero (custom OSError subclasses, future Python changes).
- **Impact:** Low. Secrets in application logs are a concern if logs are shipped to external SIEMs or stored insecurely.
- **Recommended fix:** Mask the webhook URL before logging errors in the retry loop:
  ```python
  masked = webhook_url[:30] + "..." if webhook_url else "(none)"
  logger.error("send_meta_alert: all retries exhausted (webhook=%s): %s", masked, e)
  ```

---

### [LOW] — Slack Block Kit mrkdwn: `last_alert_at` from DB injected unsanitized into mrkdwn field

- **File:line:** `backend/monitoring/silent_failure_watch.py:75,81,94`
- **Problem:** `last_alert_at` is the raw `MAX(created_at)` string from the SQLite `alerts` table, inserted directly into the `mrkdwn`-typed Block Kit section text via:
  ```python
  last_alert_text = metrics.get("last_alert_at") or "(never)"
  body_text = ... f"*Last alert at:* {last_alert_text}\n\n" ...
  ```
  Pydantic's `AlertsPipelineHealth.last_alert_at` field is typed `Optional[str]` with no format constraint. If a malicious or corrupt `created_at` value were inserted into the `alerts` table (e.g. via a SQL injection elsewhere, a compromised migration, or direct DB write), the string would be injected into the Slack message body verbatim.
- **Impact:** Slack mrkdwn injection. Worst case: malformed Block Kit payload (Slack returns 400, watchdog logs a warning, meta-alert is suppressed). Slack mrkdwn does not execute arbitrary code. `mailto:` link preview abuse is possible if the injected string is formatted as `<mailto:attacker@x.com|text>`. Real-world exploitability requires DB write access — raises the bar considerably.
- **Recommended fix:** Sanitize `last_alert_at` before embedding: strip to ISO 8601 characters only:
  ```python
  import re
  safe_last = re.sub(r"[^0-9T:Z.+\-]", "", last_alert_text)[:30] if last_alert_text else "(never)"
  ```
  Or validate the field against an ISO 8601 pattern in `AlertsPipelineHealth` via a Pydantic validator.

---

### [OPERATIONAL] — Watchdog holds DB read connection during APScheduler tick; `busy_timeout=5000ms` is the only guard against blocking a concurrent migration

- **File:line:** `backend/db/database.py:48` — `PRAGMA busy_timeout=5000`; `backend/monitoring/silent_failure_watch.py:175-176` — `get_alerts_pipeline_health()` issues 3 sequential SQLite queries
- **Problem:** SQLite WAL mode allows concurrent readers and one writer. However, `get_alerts_pipeline_health()` issues three separate `SELECT` statements within the same `get_db()` context manager (a thread-local persistent connection). If a long-running DDL statement (e.g. a future `ALTER TABLE` migration) holds a `BEGIN EXCLUSIVE` lock, each of the three watchdog queries will wait up to 5 seconds before raising `OperationalError`. The watchdog's `run_watch_cycle()` catches all exceptions from `check_silent_failure()` (line 210-213) and returns a graceful `watchdog_error` result — it does not block the scheduler. However, the 3 × 5 second wait (15 seconds worst case) can delay other scheduled jobs if APScheduler is configured with a single-threaded executor.
- **Impact:** During `apply_migration_003.py` (which uses `executescript` + exclusive-like semantics), the watchdog could stall the scheduler thread for up to 15 seconds. Not a correctness hazard — the backup/restore is independent — but it is an unexpected coupling between the migration driver and the runtime scheduler.
- **Recommended fix:** Either (a) set a shorter busy timeout for the watchdog queries specifically via a dedicated connection rather than the thread-local connection, or (b) document in the migration driver that the scheduler should be paused before running a migration. The existing `_acquire_apply_lock` + `_check_lsof` does not stop the in-process scheduler from running concurrently.

---

### [LOW] — R-01 scope check: `data/vna_alerts.db` binary mutation committed in Phase 10 scope

- **File:line:** Commit `22abf88` — `data/vna_alerts.db | Bin 3297280 -> 3309568 bytes`
- **Problem:** A binary DB mutation is committed as a Phase 10 feature commit (`feat(10): apply migration 003 to live DB`). This is intentional (migration application is an explicit Phase 10 task: MONITOR-03 Task 4), but it means the commit bundles a non-revertible binary blob change with the source-code change. `git revert 22abf88` would attempt to restore the old DB binary — which only works if no other data has been written since. This is a narrow R-03 (atomic commits + rollback always possible) concern for the DB commit specifically.
- **Impact:** Low. The `.pre-phase10.bak` is present and the rollback script exists. Rollback of the DB commit is handled by the backup, not by `git revert`. The concern is documentation/process: the commit message does not warn that `git revert` is the wrong rollback path for the DB change.
- **Recommended fix:** Add a note to the commit message or migration SUMMARY: "Rollback: restore from `.pre-phase10.bak`, do NOT `git revert` this commit."

---

## Security posture summary

- **Auth:** CONSISTENT and CORRECT at the application level. All three API routers (`router`, `admin_router`, `publisher_router`) are wrapped with `dependencies=[Depends(require_auth)]` at `backend/main.py:115-117`. Both `/api/health` and `/api/health/alerts-pipeline` are auth-gated. In development (`ENVIRONMENT=development`), auth is bypassed to a hardcoded fake user — not a production risk. The design-intent mismatch (endpoint intended for external probes but is auth-gated) is a functional gap, not an auth regression.
- **Rate-limit:** Applied correctly at the decorator level (`@limiter.limit("60/minute")`) on both health endpoints. However, the underlying `key_func=get_remote_address` resolves to `request.client.host` (TCP peer), not `X-Forwarded-For`, because `ProxyHeadersMiddleware` is absent. In a proxied deployment, all clients share one IP bucket — rate-limiting is effectively disabled per-client. This is an operational topology hazard, not a code defect.
- **Secret handling:** The Slack webhook URL is NOT logged on the happy path. Error paths log `str(e)` from `URLError`/`OSError` which does not include the URL in standard CPython. The functional webhook URL `https://hooks.slack.com/services/TEST123` IS committed in `config/alerting_rules.yaml:154` — this is the most concrete secret-handling finding. The env var `SLACK_WEBHOOK_URL` takes precedence correctly and is not logged anywhere.
- **Input validation:** `AlertsPipelineHealth` Pydantic schema validates `alerts_last_24h` and `pipeline_runs_last_24h` with `ge=0` constraints. `last_alert_at` is unvalidated `Optional[str]`. No query params accepted by the health endpoint — SQL injection risk via this endpoint is zero. The `slack_channel_override` config field has no URL validation — see finding above.
- **Error disclosure:** `routes.py:831` emits `{e!r}` (Python repr of exception) in the HTTP 503 detail field. This leaks internal table names, DB paths, and SQLite error strings to authenticated API callers. Not a public exposure given auth gating, but inconsistent with the silent exception handling in the sibling `/api/health` handler and contrary to defense-in-depth.

---

## Contract adherence

- **Phase 09 D-16 filter (deprecated=0 default):** VERIFIED. `get_alerts_pipeline_health()` at `backend/db/operations.py:344,351` scopes both `last_alert_at` and `alerts_last_24h` to `WHERE deprecated = 0`. `pipeline_runs_last_24h` correctly does not filter on deprecated (pipeline runs are not alerts). The health schema contract correctly reflects non-deprecated alert counts only.
- **Phase 09 D-17 API default-hide deprecated:** VERIFIED. Phase 10 adds no new alert list endpoints. The existing `get_alerts()` and `get_alert_by_id()` with `include_deprecated=False` default are untouched by Phase 10 hunks.
- **R-01 commit scope:** CLEAN with one annotation. All Phase 10 commits touch only declared Phase 10 scope files (routes.py, schemas.py, operations.py, config_loader.py, alerting_rules.yaml, scheduler.py, monitoring/, scripts/). The DB binary mutation commit (`22abf88`) and backup commit (`de9e79e`) are intentional Phase 10 tasks (MONITOR-03). No unrelated WIP was swept in. See LOW finding above re: `git revert` limitations on the DB commit.
- **R-14 bridge (x9-forge/contracts):** N/A — confirmed by grep. Sentinel (`value-network-alerting`) contains no imports from `@x9-forge/contracts`. R-14 does not apply to this repo.

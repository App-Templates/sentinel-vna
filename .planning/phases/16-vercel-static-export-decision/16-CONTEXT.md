# Phase 16: Vercel Static Export Decision + v1.3 Deploy — Context

**Gathered:** 2026-05-04
**Status:** Ready for planning
**Source:** Operator directive 2026-05-04 ("vai con deploy") + ROADMAP Phase 16 entry + audit Mondadori-gap synthesis

<scope_extension>
## Scope extension vs ROADMAP entry

ROADMAP Phase 16 originale (line 275-283) prevede 3 SC:
1. Decision in PROJECT.md Key Decisions: ship v1.3.1 with migration plan OR shelve
2. `git status` no longer lists Commit E files as uncommitted on main
3. Deployment docs consistent with chosen model

**Phase 16 ESTESA per questa esecuzione** — scope amplificato per coprire il deploy operativo richiesto da Stefano:

4. **API JSON static export rigenerato** contro backend FastAPI con codice Phase 11-15 attivo (l'attuale snapshot in `frontend/dist/api/` data 2026-04-27 da WIP, pre-Phase-11)
5. **Frontend bundle ricompilato** (`npm run build`) con codice main HEAD `2942775` (Phase 15 ChartErrorBoundary + ScopeBadge + GrossNetToggle + ReferencePeriodFootnote + i18n keys)
6. **Deploy live** su `https://sentinel-vna.vercel.app` via `vercel --prod` o equivalente
7. **Rollback path verificato** via git tag pre-deploy + Vercel deploy URL precedente capturato
8. **Post-deploy UAT** smoke: 5 alert detail (incluso ALT-20260113-225828-P2 dell'email Vito) + 1 dashboard + 1 publishers list + visiva verifica ScopeBadge/GrossNetToggle/ReferencePeriodFootnote/empty-state diagnostico
9. **Network-totals endpoint vivo** verificato via curl produzione: `/api/metrics/network-totals?date=2026-01-12&channel=GOOGLE_ADEX` → 200 + `revenue_gross: 27245.63`

L'estensione è giustificata da:
- Operator directive esplicito 2026-05-04
- Phase 11-15 ferme in main locale a HEAD `2942775`, 246+ commit ahead di origin/main; live Vercel da 2026-04-27 (pre-Phase-11)
- Mail a Vito dipende dal deploy: lui aprendo il link DEVE vedere i fix per credibilità della comunicazione
- Mondadori family fix (Phase 17 CLEAN-02) richiede 3 risposte da Vito → catch-22 senza deploy

</scope_extension>

<domain>
## Phase Boundary

Cosa Phase 16 fa:
- Formalizza decisione Commit E (SHIP — già implicitamente shipped via Phase 12 cherry-pick di backend `7ea4a74` + frontend `94a48cd`)
- Rigenera static API JSON export contro backend Phase 11-15 attivo
- Ricompila frontend bundle con tutti i Phase 11-15 fix
- Deploya su Vercel production (sentinel-vna.vercel.app)
- Verifica live UAT contro 8 punti email Vito + Mondadori-gap audit
- Persiste rollback path (git tag + Vercel deploy URL precedente)

Cosa Phase 16 NON fa:
- NON tocca codice applicativo (zero feat/fix commits)
- NON risolve gap Mondadori family (-22% bacino) — owned by Phase 17 CLEAN-02 dopo risposta Vito
- NON modifica le 3 domande operator (taxonomy / OpenMarket / ad-requests def) — sono per email reply post-deploy
- NON tocca backend Python deploy infrastructure (out of scope — l'API è statica via export, il backend FastAPI gira solo localmente per generare lo snapshot)

</domain>

<decisions>
## Implementation Decisions

### D-16.01 — Commit E: SHIP (formalizza)
- I 5 file architetturali WIP Vercel (vercel.json + scripts/export_api_json.sh + frontend bundling + .vercel/project.json + outputDirectory routing) **sono già in main** (committed pre-2026-04-27).
- Backend WIP `7eaa74` (bacino dedup) cherry-picked Phase 12.
- Frontend WIP `94a48cd` (i18n IT→EN) landed Phase 12.
- Decisione formale: **SHIP v1.3.1 model = current Vercel static** (no migrazione architetturale, l'attuale model ha funzionato e va deployato con i fix Phase 11-15).
- PROJECT.md Key Decisions section va aggiornata.

### D-16.02 — Re-export API JSON pre-deploy: REQUIRED
- L'attuale `frontend/dist/api/*.json` è snapshot del 2026-04-27 da working tree WIP (pre-Phase-11).
- Prima del deploy va re-eseguito `scripts/export_api_json.sh` contro backend uvicorn POST-Phase-15.
- Backend va avviato localmente, lo script estrae 50 alert (top recenti, non deprecated) + dashboard + publisher endpoints + admin endpoints come file JSON statici → `frontend/dist/api/`.
- Il backend NON viene deployato come server live — vive solo come generatore di snapshot.

### D-16.03 — Build frontend: vite production build standard
- `cd frontend && npm run build` → genera `frontend/dist/index.html` + `dist/assets/*.{js,css}`.
- Nessuna modifica al config vite/tsconfig — già funzionante in Phase 15 (build clean 2.13s, 2460 modules).

### D-16.04 — Deploy method: Vercel CLI `--prod`
- `vercel --prod` da repo root con `.vercel/project.json` esistente (`prj_1jMsYWcLI0UULf6RFFUwjXe6gCyw`, team Mondadori `team_RrZxd6aw0swiFDHMdaiSZgxH`).
- Output: nuovo deployment URL + alias `sentinel-vna.vercel.app`.
- Ammette rollback via `vercel rollback <previous-deploy-url>`.

### D-16.05 — Pre-deploy safety: git tag + Vercel current URL capture
- `git tag pre-deploy-v1.3-2026-05-04` su HEAD `2942775` PRIMA di qualsiasi azione.
- Capture current Vercel deploy URL via `vercel ls` o `vercel inspect` per rollback target.
- Snapshot `frontend/dist/api/` precedente in `/tmp/sentinel-vercel-rollback/` (pochi MB).

### D-16.06 — Post-deploy UAT: 7 smoke checks operator-driven
- (1) Apri `sentinel-vna.vercel.app` → login email `stefano@adkaora.com` o equivalente
- (2) Dashboard render: KpiCards con ScopeBadge, RevenueByChannel decoupled, RevenueStatus24h con date selector
- (3) Alert detail `ALT-20260113-225828-P2` (l'alert citato in email Vito): vedi GrossNetToggle, ScopeBadge GOOGLE, ReferencePeriodFootnote
- (4) Alert detail con `revenue_trend: null`: vedi empty-state diagnostico verbatim "No 7-week history. Alert < 7 days old or data not yet aggregated."
- (5) Publishers list `/publishers`: 6-filter URL state hook, sell_type filter dropdown, weighted avgFillRate
- (6) Curl produzione `/api/metrics/network-totals?date=2026-01-12&channel=GOOGLE_ADEX` (via static JSON snapshot) → revenue_gross 27245.63
- (7) Visivamente: empty-state copy verbatim su almeno 1 chart (per UAT email Vito #6 closure live)

Operator firma il UAT post-deploy.

### D-16.07 — Rollback trigger
Se UAT fallisce su >=1 dei 7 check critici:
- `vercel rollback <previous-deploy-url>` per reverse al deploy 2026-04-27
- `git tag` precedente preserva codice
- Surface su STATE.md + nuovo audit per identificare la regressione

### D-16.08 — Email reply Vito: GATED on UAT pass
- Mail a Vito (bozza già scritta in audit synthesis) è preparata MA NON viene inviata da Phase 16
- Phase 16 termina con UAT pass + commit `docs(phase-16): complete deploy v1.3` + `pre-deploy-v1.3-2026-05-04` git tag
- Operator (Stefano) decide quando inviare la mail — out of phase scope

### Claude's Discretion

- Esatto sequencing Wave plans (probabilmente: Wave 1 = pre-deploy safety + decision formalization, Wave 2 = export+build+deploy, Wave 3 = UAT + rollback verification)
- Numero esatto di plans (3-4 stimato)
- Dettagli grep AC per ogni task (planner produce)
- Threat model ASVS L1 deploy-specific (deploy = shared state production)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Vercel deploy infrastructure
- `vercel.json` — config with outputDirectory, routes
- `.vercel/project.json` — project ID + team ID (already linked)
- `scripts/export_api_json.sh` — static API snapshot generator
- `frontend/package.json` — build script (`vite build`)
- `frontend/vite.config.ts` — vite config + proxy (proxy is dev-only)

### Truth source per Vito email closure
- `.planning/STELLA-POLARE.md` — north-star v1.3
- `.planning/intel/sentinel-2026-04-28/EMAIL-VITO-2026-04-22.md` — 8 lamentele verbatim
- `.planning/intel/sentinel-2026-04-28/SYNTHESIS.md` — 5 RC mapping to Phase 11-14
- `.planning/intel/sentinel-2026-05-04-mondadori-gap/SYNTHESIS.md` — Mondadori gap audit (post-Phase-15) — context for Phase 17 follow-up

### Phase 11-15 closure summaries
- `.planning/phases/11-*/11-SUMMARY.md` — network-totals endpoint + sell_type filter + server baseline
- `.planning/phases/12-*/12-*-SUMMARY.md` — bacino dedup + family agg (parziale) + i18n
- `.planning/phases/13-*/13-SUMMARY.md` — date selector + YoY 7w + decoupled charts
- `.planning/phases/14-*/14-SUMMARY.md` — ScopeBadge + GrossNetToggle + ReferencePeriodFootnote + 6-filter URL
- `.planning/phases/15-ui-resilience/15-04-UAT-REPORT.md` — UAT 3/3 PASS signed Stefano 2026-05-04

### Project rules (auto-loaded but worth re-citing)
- `~/.claude/CLAUDE.md` — R-04 chirurgico 10/10 mandatory pre-deploy; R-05 no risky action without OK; R-13 GSD mandatory
- `CLAUDE.md` (repo root) — Sentinel-specific hard constraints (no stash db files, no push origin without OK, etc.)

### Audit history
- `.planning/intel/sentinel-2026-04-28/AUDIT-A-NUMBERS-FORENSICS.md`
- `.planning/intel/sentinel-2026-04-28/AUDIT-B-PHASE-COVERAGE.md`
- `.planning/intel/sentinel-2026-04-28/AUDIT-C-LIVE-VS-EMAIL.md`
- `.planning/intel/sentinel-2026-05-04-mondadori-gap/AGENT-A-data-forensics.md`
- `.planning/intel/sentinel-2026-05-04-mondadori-gap/AGENT-B-contract-scope.md`

</canonical_refs>

<specifics>
## Specific Ideas / Constraints

- **R-04 chirurgico 10/10** mandatory: ogni step deve avere rollback esplicito, snapshot precedente, UAT post-action verify, stop-at-first-doubt protocol.
- **R-05 risky operation OK gate** — `vercel --prod` richiede esplicito OK Stefano dopo che il bundle è pronto e UAT su staging (se possibile) è pass. NO autonomous deploy.
- **R-03 atomic commits** — git tag, formal decision commit (PROJECT.md), deploy log commit, UAT report commit ognuno suo commit.
- **CLAUDE.md (repo)** anti-pattern #5: "Non spawnare deploy o push senza esplicito OK" — Phase 16 ha avuto OK 2026-05-04 per deploy autorizzato, MA singoli step rischiosi (vercel --prod, git push origin se necessario) vanno comunque confermati pre-execution.
- **No `git stash` of `data/vna_alerts.db*`** — runtime mutates them; non touch durante deploy.
- **Vercel team auth** — `.vercel/project.json` mostra team_id Mondadori; CLI deve essere già autenticata. Se non lo è, surface con `vercel login` (richiede operator action).
- **Backend NOT deployed** — solo static frontend + JSON snapshots. Backend FastAPI gira locale solo per generare lo snapshot durante il deploy run.
- **Auth gate** — sentinel-vna.vercel.app ha AuthGuard localStorage-based con domain `@adkaora.com`. UAT post-deploy richiede operator login con email autorizzata.

</specifics>

<deferred>
## Deferred Ideas

- **Phase 17 CLEAN-02 Mondadori family** — fix gap residuo bacino -22% via family aggregation backend + top-50 whitelist. Richiede 3 risposte da Vito (taxonomy / OpenMarket scope / ad-requests def). Mail a Vito è LA azione immediate post-Phase-16 ma è operator-driven (Stefano invia personalmente).
- **Backend deploy** (Phase 18+ potenziale) — attualmente backend è dev-only. Se servono live alert generation, va valutato un deploy serverless o VPS dedicato. Out of v1.3 scope.
- **PBI contract test automation** (Phase 18 HARD-04) — `tests/contracts/test_parquet_db_ui.py` con assertion vs PBI noti. Out of Phase 16 scope.
- **Slack webhook rotation** (Phase 10.2-04 MONITOR-12) — deferred via abort signal, out of Phase 16 scope.

</deferred>

---

*Phase: 16-vercel-static-export-decision*
*Context gathered: 2026-05-04 — operator directive "vai con deploy"*
*Scope extension authorized: Stefano 2026-05-04 18:30 CEST*

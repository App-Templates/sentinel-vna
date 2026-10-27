---
audit_synthesis: true
date: 2026-04-28
sources:
  - EMAIL-VITO-2026-04-22.md
  - AUDIT-A-NUMBERS-FORENSICS.md
  - AUDIT-B-PHASE-COVERAGE.md
  - AUDIT-C-LIVE-VS-EMAIL.md
status: CANONICAL — north-star reference for v1.3 advancement
---

# SENTINEL v1.3 — Sintesi convergente dei 3 audit (2026-04-28)

**Questo documento è la base obbligatoria di comprensione. Ogni step di Sentinel v1.3 deve riferirsi qui.**

## TL;DR (per fretta)

1. L'email di Vito (2026-04-22) lamenta **8 numeri sbagliati** sulla dashboard Sentinel.
2. **Vito ha ragione su tutti gli 8 punti** — confermato indipendentemente da 3 auditor.
3. Le 8 lamentele = **5 root cause** (raggruppamento canonico).
4. **Phase 07-10.2 NON ha cambiato NESSUN numero che Vito cita** — fixava un bug DIVERSO (silent failure CHECK constraint).
5. Le 5 root cause sono indirizzate da **Phase 11+12+13+14** — nessuna ancora implementata.
6. **WIP commit `7ea4a74` (bacino dedup)** è in `wip/pre-10.2-rescue` (mai mergeato in main); il live serve già il suo output (133M); MA non è quello che Vito vuole (366M = aggregazione Mondadori-family).
7. **Path A (refresh JSON + redeploy) NON risolve niente di numerico** dell'email — i bug sono nei calcoli/label, non nella freshness.
8. **ETA realistico** per chiudere l'intera email: 4-6 working days di Phase 11→12→13→14→15.

## Le 8 lamentele dell'email (canoniche)

Vedi `EMAIL-VITO-2026-04-22.md` per l'email verbatim. Decomposizione canonica:

| # | Lamentela | Numeri specifici |
|---|-----------|------------------|
| 1 | Dashboard hourly Revenue AdEx vs PBI Hour Analysis | (delta non quantificato) |
| 2 | Triage AdEx impressions Jan 12 | 14M PBI vs 10M Sentinel |
| 3 | Triage AdEx revenues Jan 12 | €27.2k PBI vs €25.9k Sentinel |
| 4a | Mondadori bacino Feb | 366M PBI vs 133M Sentinel |
| 4b | Mondadori fill rate Feb | 35.2% PBI vs 41.8% Sentinel |
| 4c | Mondadori eCPM Feb | €1.51 PBI vs €2.08 Sentinel |
| 4d | Mondadori RPM Feb | €0.51 PBI vs €0.87 Sentinel |
| 4e | Mondadori revenue Feb | €188k all / €90k Open Market vs €115k Sentinel |
| 5 | Alert UI — current revenue senza periodo di riferimento | (esempio ALT-2026 Jan 13 08:57) |
| 6 | Alert "Google" — timeline mai presente → non verificabile | "No revenue trend data available" |

## Le 5 ROOT CAUSE (mappa canonica)

| RC | Nome | Email # | Fix |
|----|------|---------|-----|
| **(a)** | Top-50 publisher filter senza disclaimer | #1, #2, #3 (parziale) | Channel scope badge (CORR-04) + nota "top-50 only" → Phase 13/14 |
| **(b)** | Mondadori family non aggregati (Mondadori_npa + Adgage_mondocore + Mediamond serviti come pubblicher separati) | #4a → cascata su #4b/c/d | Aggregazione `publisher_family` lato API o UI. **Parziale ipotesi: WIP `7ea4a74` non risolve perché agisce su `n_channels` (math) non su `publisher_family` (grouping).** Phase 12/13 |
| **(c)** | NET vs GROSS revenue senza label | #4e (€115k = €188k × 0.6 rev-share, no bug aritmetico) | Toggle gross/net + label "post rev-share 60%" (CORR-03 D2) → Phase 13 |
| **(d)** | Legacy `GOOGLE` channel naming (107/107 alert legacy `channel_group='GOOGLE'` non `'GOOGLE_ADEX'`) | #6 timeline empty | Migration/filtro retro-compat → Phase 12 |
| **(e)** | Client-side heuristics in `TriageSection.tsx` (`revenueRatio*0.95` + `avgCoverage+0.05` inventati) | #2-#3-#4 indirettamente | Server-side baseline (CORR-01 + API-03) → Phase 11/12 |

**RC (f) extra (timestamp/timezone label):** #5 → CORR-02 + CORR-05 → Phase 14.

## Bug ADDIZIONALI (Auditor C) — Vito non li ha catturati

1. `revenue-status-24h` mostra 23 ore consecutive di `-100%` su giorno parziale incompleto
2. `available_dates`: gap Gen 1 → Dic 23 (2.5 mesi vuoti nel selector dashboard)
3. **CORR-01 heuristics (`*0.95`, `+0.05`)** confermati nel bundle live byte-per-byte (`o=Math.round(r*(l*.95))`)
4. **CORR-08 simple-average fill_rate** confermato nel bundle live (`m.reduce((C,P)=>C+P.fill_rate,0)/m.length`)
5. **200 alert legacy `deprecated=1` nel DB locale ma serviti su Vercel senza il flag** — operatore vede alert vecchi senza saperlo

## Three-way compare (Auditor C, dettagliato in AUDIT-C-LIVE-VS-EMAIL.md §C.2)

| Numero | PBI (verità) | Live Vercel (snapshot Mar 26) | Local backend attuale (main HEAD) | Cambierebbe con deploy refresh? |
|--------|--------------|-------------------------------|------------------------------------|--------------------------------|
| Mondadori bacino | 366M | 133M | 860M (sum naive — main HEAD non ha dedup) | **Sì peggiora**: dal 133M live al 860M se deployasse main raw |
| Mondadori fill_rate | 35.2% | 41.8% | (proporzionale) | Cambia ma non verso PBI |
| AdEx impressions Jan 12 | 14M | 10M | 10M | No |
| Lista alert | (variabile) | 200 legacy | 438 (200 deprecated + 238 backfill) | **Sì migliora**: legacy → fresh |

**Punchline (Auditor C, verbatim):** "None of Phases 07-10.2 changed any number Vito quoted."

## Stato deployment vs sviluppo

| Componente | Local main | Origin/main GitHub | Live Vercel `sentinel-vna.vercel.app` |
|------------|-----------|---------------------|----------------------------------------|
| Frontend i18n + dashboard refactor | ❌ NO (in `wip/pre-10.2-rescue` 94a48cd) | ❌ NO (origin fermo Feb 21) | ✅ DEPLOYATO (deploy non tracciato, da WIP working tree) |
| Backend bacino dedup | ❌ NO (main = `bacino.sum()` naive) | ❌ NO | ✅ DEPLOYATO (output 133M presente in JSON live) |
| Phase 07-10.2 fixes (silent failure) | ✅ TUTTO | ❌ NO (158 commit non pushati) | ❌ NO (JSON Mar 26 = pre-fix) |
| `data/sentinel_db/*.csv` raw | (untracked, locale only, 2 GB) | NO (gitignored) | NO (non deployabile) |

**Sintesi:** ogni layer è in stato disallineato.

## Phase v1.3 — coverage matrix vs email

(Da `AUDIT-B-PHASE-COVERAGE.md` §B.2 — completamente in linea con `ROADMAP.md` § Phase Details.)

| Phase | Stato | Email # indirizzati |
|-------|-------|---------------------|
| 07 DB WIP Investigation | ✓ Done | (none — internal) |
| 08 Schema + ETL | ✓ Done | parziale #4b (SCHEMA-03) ma non visibile finché non deploy |
| 09 Backfill + Legacy Migration | ✓ Done | parziale #6 (alert deprecated/non) |
| 10 Pipeline Monitoring | ✓ Done | (none — internal) |
| 10.1 Hotfix & Hardening | ✓ Done | (none — internal) |
| 999.1 LIVE silence diagnosis | ✓ Done | (none — diagnostic) |
| **10.2 Sec Hardening** | 3/4 done (10.2-04 deferred) | (none — internal) |
| **11** Network Totals + Server-side Baseline | ⏳ NOT STARTED | **#1, #2, #3 (RC-a + RC-e)** |
| **12** WIP Commits + Triage Server-Side | ⏳ NOT STARTED | **#4a/b/c/d (RC-b + RC-d), #6** |
| **13** Dashboard Date Navigation | ⏳ NOT STARTED | **#4e (RC-c), #1 (RC-a)** |
| **14** UI Labeling + Filter Exposure | ⏳ NOT STARTED | **#5 (RC-f), reinforce #1/#4 labels** |
| 15 UI Resilience | ⏳ NOT STARTED | (resilience) |
| 16 Vercel Static Export Decision | ⏳ NOT STARTED | (architectural) |
| 17 Data Cleanup | ⏳ NOT STARTED | (cleanup) |
| 18 Hardening + PBI Contract Tests + Docs | ⏳ NOT STARTED | (regression prevention) |

**Critical path per chiudere l'email:** 11 → 12 → 13 → 14 (15 utile, 16-18 non bloccanti per Vito).

## Decision card — 3 path mutuamente esclusivi

| Path | Cosa fa | Tempo | Cosa risolve | Rischio |
|------|---------|-------|--------------|---------|
| **1 — Email reply onesta** | Rispondi a Vito: "8 bug confermati, 5 root cause, ETA ~5gg, nel frattempo Mondadori/AdEx non attendibili" | 30 min | Niente tecnico, compra tempo, niente blast radius | LOW |
| **2 — Phase 11 start** | `/gsd-discuss-phase 11` → /plan → /execute (Network Totals API + ETL refresh + server-side baseline) | 1-2 sessioni | RC (a) parzialmente + (e) | MEDIUM (R-13: deve essere top-tier) |
| **3 — Quick-win 2gg** | (a) deploy main su Vercel + (b) prototipo CORR-04 channel scope badge | 1-2 sessioni | (d) trend vuoto + lista alert + visivo immediato | HIGH (Path A non sposta numeri; prototipo singolo viola R-13) |

**Raccomandazione audit-driven:** Path 1 + Path 2. Path 3 è teatro.

## Cosa SOLO STEFANO può decidere

1. **Email reply** — vuoi rispondere a Vito ora, prima di Phase 11? Quale tono/contenuto?
2. **Phase 11 vs 12 ordering** — Phase 11 è server-side baseline (RC-e); Phase 12 è WIP commits + triage server-side (RC-b/d). Quale prima?
3. **Mondadori family aggregation** — dobbiamo decidere come definire `publisher_family`: hardcoded (Mondadori = M + M_npa + Adgage_mondocore + Mediamond) oppure regex/config? Vito può chiarire definizione PBI.
4. **Sell type filter scope** — PBI distingue `Open Market` vs `all sell types`; Sentinel non espone `sell_type` ovunque. Esponiamo come filter o come fixed-context-with-badge?
5. **Vercel deploy strategy** — main locale è 158 commit ahead di origin. Pushiamo origin/main per allineare GitHub? Cambiamo Vercel project link a `value-network-alerting` o `frontend` (ora deploy.sh punta a `sentinel-vna` che non corrisponde a nessuno dei 2 .vercel/ link)?

## Riferimenti

- `EMAIL-VITO-2026-04-22.md` — verbatim email + decomposizione 8 punti
- `AUDIT-A-NUMBERS-FORENSICS.md` — code-path tracing per ogni numero
- `AUDIT-B-PHASE-COVERAGE.md` — phase ledger + critical path
- `AUDIT-C-LIVE-VS-EMAIL.md` — live forensics + 1-page operator briefing
- `.planning/PROJECT.md` — milestone definition + key decisions
- `.planning/ROADMAP.md` § Phase Details — phase 11-18 specs
- `.planning/REQUIREMENTS.md` — CORR-01..11, SCHEMA-01..04, MONITOR-01..14, API-01..03

## Anti-pattern da NON ripetere (lessons learned di questa sessione)

1. **Non assumere "email" come dato accertato finché non si legge il testo verbatim.** Speculare basandosi su una menzione singola produce path inutili.
2. **Non confondere "fix shipped to local main" con "fix visible in dashboard".** Il deploy gap (158 commit non pushati) significa che ogni `[x]` in REQUIREMENTS.md è funzionalmente `[~]` finché non si chiude il deploy.
3. **Non proporre Path A (refresh JSON) come fix a bug di calcolo.** I numeri sbagliati restano sbagliati con qualunque freshness.
4. **Non fidarsi di `git stash` con DB binari modificati.** I file `data/vna_alerts.db*` sono mutati dal runtime continuamente; pop dopo deploy lungo conflitta.
5. **Non confondere "WIP commit C bacino fix" con "fix di RC-b"**. La dedup matematica `n_channels`-divide è un FIX DIVERSO dall'aggregazione `publisher_family`. Il primo non risolve la lamentela `366M vs 133M`.

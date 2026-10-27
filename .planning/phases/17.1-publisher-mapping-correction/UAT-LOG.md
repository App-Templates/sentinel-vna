# Phase 17.1 UAT Log

**Deploy date (W-03):** 2026-05-19 (`.deploy-date`; rollback tag `pre-17.1-deploy-2026-05-19`)
**Initial deploy timestamp:** 2026-05-20T13:19:01 GMT+0200 (deployment `dpl_GAkE3GYXWrc7TDnoQaaMd4Y5VbUQ`)
**Gap-closure deploy timestamp:** 2026-05-20T15:09:37 GMT+0200 (deployment `dpl_APXL5nUScNqT9khMZwtcqNYQZxEr`)
**Production canonical alias:** `https://sentinel-vna-stefano-hejais-projects.vercel.app`
**Gap-closure per-deploy URL:** `https://sentinel-1obzbccu2-stefano-hejais-projects.vercel.app`
**Operator:** Stefano Argiolas
**UAT executed:** 2026-05-20 (Checks 1-6 confirmed via browser of `/publishers`; Check 7 Mondadori drilldown; Check 8 Prensa Ibérica drilldown post gap-closure)

---

## 8-Check Results

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | Top Publishers page loads (200 OK + Top 35 visible) | **PASS** | Operator browser screenshot of `/publishers` rendering Top 35 table populated. CDN GET `/api/publishers/top` returned HTTP 200 with `.publishers \| length == 35` (DEPLOY-LOG §"W-05 CDN smoke"). |
| 2 | No `_family` suffix in publisher names | **PASS** | DEPLOY-LOG anti-presence check on CDN response: `_family: PASS (0 found)`. Browser table inspection by operator confirmed zero rows ending in `_family`. |
| 3 | Mondadori revenue numerically within ±5% of €1.125k (B-03 NUMERIC) | **PASS** | Actual value on CDN top-N: **€1,125,425** (rounded from €1,125,424.54). Band [€1,068,750, €1,181,250]. Delta from €1.125M target ≈ €425 — well inside ±€56,250 (5%) tolerance. Compare Phase 17 wrong over-aggregation €1,458,298.74 (Mondadori_family) — corrected to Mondadori-only after Marco audit. |
| 4 | Mediamond / Mondocore distinct from Mondadori (Marco audit RC-(b) fix) | **PASS** | Mediamond present as own row in Top-N with revenue **€332,874.19**, separate from Mondadori. (Mediamond appears in the standalone publisher list; data-distinct fix verified.) Mondocore absent from top-35 — €0 revenue in 2025 parquet (documented Wave 2a SUMMARY D-17.1-02a-D; reverse-mapping wires it correctly when data lands). |
| 5 | No `AdGage_` raw prefix in publisher names; clean PBI names visible | **PASS** | DEPLOY-LOG: `AdGage_: PASS (0 found)`. CDN top-N exhibits PBI-normalized names (Vocento €1,157,530.03; Prensa Ibérica €1,010,699.63; El Español €509,558.27; Unidad Editorial €419,957.76; Grupo Godó €353,701.07). Operator browser confirms. |
| 6 | No `OLD` and no `test` cluster publisher names in table | **PASS** | DEPLOY-LOG: `OLD: PASS (0 found)`, `test: PASS (0 found)`. CDN response anti-presence verified at deploy time; operator browser scan confirms. |
| 7 | Click on a clean publisher row navigates to drilldown (Mondadori) | **PASS** | Operator clicked Mondadori row → `/publishers/Mondadori` drilldown loaded. Weekly KPIs rendered: **revenue €1,107,330** (ISO-year 2025 — the ~€18k delta vs Top Publishers €1,125,425 calendar-year is the 4 late-Dec 2025 days whose ISO week belongs to 2026; expected per Wave 2b SUMMARY D-17.1-02b-D). **eCPM 1.23€**, **Impressions 903.3M** rendered. B-01 5/5 endpoints reachable (no 500 on feedback-history or interventions tabs). |
| 8 | Click on a publisher with accents (Prensa Ibérica) routes correctly | **PASS (after gap-closure)** | Initial deploy (`dpl_GAkE3GYXWrc7TDnoQaaMd4Y5VbUQ` 2026-05-20T13:19): operator click on `Prensa Ibérica` row returned "Impossibile caricare i dettagli" — see Gap-Closure section below for root cause + fix. Gap-closure deploy (`dpl_APXL5nUScNqT9khMZwtcqNYQZxEr` 2026-05-20T15:09): operator re-clicked Prensa Ibérica row → drilldown loaded. CDN smoke evidence: `GET /api/publishers/Prensa%20Ib%C3%A9rica/weekly-kpis` returned HTTP 200 + `application/json`, byte-identical to local `frontend/dist/api/publishers/Prensa Ibérica_weekly-kpis.json`. Grupo Godó cross-check also PASS (HTTP 200 + byte-identical). All 5 sub-endpoints HTTP 200 for Prensa Ibérica. |

---

## Summary

- **Total checks:** 8
- **PASSED:** 8/8
- **FAILED:** 0
- **PENDING:** 0
- **Outstanding issues:** 0 (gap closure fully resolved)

**Mondadori revenue recorded:** €1,125,424.54
**B-03 ±5% band [€1,068,750, €1,181,250]:** within ✓ (delta from €1.125M target ≈ €425)
**Rollback path executed:** no (UAT PASSED end-to-end)

---

## Gap-Closure Note (Check 8 trajectory)

Check 8 (multi-word publisher drilldown) initially failed on the first production deploy (`dpl_GAkE3GYXWrc7TDnoQaaMd4Y5VbUQ`, 2026-05-20T13:19). Root cause identified during operator bisect: `scripts/export_api_json.sh:50` used `for pid in $PUB_IDS` which word-split on whitespace, producing single-token filenames (`Prensa_weekly-kpis.json` + orphan `Ibérica_weekly-kpis.json`) for the 19 multi-word publisher_ids in `/api/publishers/top`. The Vercel route regex `([^/]+)` URL-decoded `Prensa%20Ib%C3%A9rica` → `Prensa Ibérica` (literal space) and looked for `publishers/Prensa Ibérica_weekly-kpis.json` → not found → fell through SPA `index.html` → frontend showed "Impossibile caricare i dettagli".

**Affected surface:** 19 multi-word publishers × 5 endpoints = 95 broken paths. Single-word publishers (Mondadori, Vocento, Mediamond, Dorvan, etc.) were unaffected — that's why Checks 1-7 (Mondadori-based) all passed at the first deploy while only Check 8 (multi-word) failed.

**Fix (commits `98d1ddc` + `190636c` + `b626f20`, 2026-05-20T~14:54-15:14Z):**
1. `scripts/export_api_json.sh`: `for pid in $PUB_IDS` → `while IFS= read -r pid; ... <<< "$PUB_IDS"` (preserves whitespace); dropped `SAFE_PID=$(tr ' ' '_')` underscore transform; added `urlencode()` python3 helper for path segments; added `rm -rf` at top of script to prevent stale entity files persisting between exports.
2. Snapshot re-exported with fix applied → 1004 JSON files. All 19 multi-word × 5 endpoints = 95 new files present with literal-space filenames. Single-word publishers unchanged (byte-identical vs prior deploy for Mondadori control).
3. Gap-closure deploy via `vercel --prod --yes` (operator OK "procedi su tutto" 2026-05-20T~14:54Z covers the redeploy). Deploy `dpl_APXL5nUScNqT9khMZwtcqNYQZxEr`, build 18s, Ready 26s, exit 0.
4. W-05 CDN byte-diff smoke + sub-endpoint smoke: all 95 multi-word paths HTTP 200 + byte-identical vs local on first attempt. Operator re-tested Prensa Ibérica click → drilldown loaded successfully.

This is a post-deploy bug fixed within the same phase via the same R-04 chirurgico discipline (rollback tag still valid, R-05 explicit operator OK preserved). Tracked end-to-end in DEPLOY-LOG.md §"Gap-closure deploy".

---

## Evidence Pointers

- **CDN smoke evidence (per-check anti-presence + numeric):** `DEPLOY-LOG.md` §"Smoke evidence (captured 2026-05-20T13:20Z)" + §"W-05 CDN smoke (post-deploy, before operator UAT)" (gap-closure run)
- **Rollback artifacts:** Tag `pre-17.1-deploy-2026-05-19` (still valid), Vercel rollback target `sentinel-6euuq78x2-stefano-hejais-projects.vercel.app` (pre-Phase-17.1)
- **Gap-closure commit chain:** `98d1ddc` (script fix) → `190636c` (DEPLOY-LOG snapshot marker) → `b626f20` (CDN smoke metadata)
- **Initial deploy commit chain:** `ac04c70` (snapshot regen) → `9830259` (CDN smoke metadata)
- **Plan-checker iter-1 fixes baked in & verified live:** B-01 (5/5 endpoints — Prensa Ibérica feedback-history + interventions both HTTP 200), B-03 (Mondadori €1,125,425 within ±5% band), W-01 (Mediamond present + OLD/test absent), W-05 (CDN byte-diff PASS on both deploys)

---

*Phase: 17.1-publisher-mapping-correction*
*UAT: 8/8 PASSED*
*Operator sign-off: Stefano Argiolas, 2026-05-20*

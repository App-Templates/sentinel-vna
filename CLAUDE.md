# Sentinel — Claude Session Directives

**Codename:** SENTINEL = `value-network-alerting` (NON sentinel-spot, that's a different repo).

**Operator:** Stefano Argiolas (CSIO Mondadori Digital, X9+Forge architect on other projects).

---

## 🌟 MANDATORY READ before any action

**Read these in this order — they are the truth source for v1.3:**

1. `.planning/STELLA-POLARE.md` — north-star (~5 min)
2. `.planning/intel/sentinel-2026-04-28/EMAIL-VITO-2026-04-22.md` — the email of record (~5 min)
3. `.planning/intel/sentinel-2026-04-28/SYNTHESIS.md` — convergent audit findings (~10 min)
4. `.planning/PROJECT.md` — milestone definition (~5 min)
5. `.planning/STATE.md` — current execution position (~2 min)

**Total: ~30 min to be operational.** Skip and you'll burn 1+ hour proposing wrong paths (documented anti-pattern in SYNTHESIS.md "Lessons learned").

---

## Hard constraints (project-specific, on top of global ~/.claude/CLAUDE.md)

- **R-13 architectural quality:** v1.3 is "production-grade 10/10" by mandate. No quick-and-dirty.
- **R-05 no risky action without OK:** any `git push`, `vercel --prod`, `git reset --hard`, `vercel rollback`, or DB-mutating script requires explicit operator OK.
- **R-04 chirurgico 10/10 for any deploy:** snapshot + tag + rollback plan + verify post-action mandatory.
- **R-03 atomic commits:** each logical change = one commit. Never bundle.
- **No `git stash` of `data/vna_alerts.db*`** — runtime mutates them continuously, pop fails on binary conflict.
- **`data/sentinel_db/*` is .gitignored**, ~2 GB raw CSVs, do NOT push to origin.

---

## Anti-pattern PROIBITI (apprese in sessione 2026-04-27/28)

1. ❌ Non assumere il contenuto dell'email Vito senza leggerla verbatim
2. ❌ Non proporre "Path A" (refresh JSON + redeploy) come fix ai numeri sbagliati — documentato non risolve
3. ❌ Non confondere `[x]` in REQUIREMENTS.md con "live in produzione"
4. ❌ Non confondere WIP `7ea4a74` bacino dedup con fix di RC-b (Mondadori family)
5. ❌ Non spawnare deploy o push senza esplicito OK
6. ❌ Non scrivere documenti di sintesi senza prima aver LETTO i 4 file in `.planning/intel/sentinel-2026-04-28/`

---

## Stato repo (snapshot 2026-04-28)

- Branch corrente: variabile per sessione, ma `main` è il source of truth
- Local main = 158 commit ahead di `origin/main` (origin fermo a Feb 21)
- Branch `wip/pre-10.2-rescue` = 2 commit (frontend i18n + backend bacino WIP) parcheggiati
- Tag `pre-10.2-wip-snapshot` = safety tag su HEAD pre-Phase-10.2-execution
- Phase 07-10.2 (3/4) shipped su local main, MAI pushato
- Live Vercel `https://sentinel-vna.vercel.app` = deploy 2026-04-27 12:45 GMT non tracciato (da WIP)

---

## Stack

- Backend: Python (FastAPI + uvicorn + SQLite WAL + APScheduler)
- ETL: pyarrow + pandas, sentinel_db CSVs → parquet
- Frontend: TS/React + Vite + Tailwind, i18n it/en (LanguageProvider)
- Deploy: Vercel static + JSON snapshot pre-export via `scripts/export_api_json.sh`
- Workflow: GSD (Get Shit Done) per fasi, atomic commits, multi-agent audit

---

*Last updated: 2026-04-28 — file creato per persistere truth source post audit triplo.*

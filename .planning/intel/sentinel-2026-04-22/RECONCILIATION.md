# SENTINEL — Stato reale e piano Stabilization v1.3

**Data intel:** 2026-04-22
**Autore:** sessione Claude multi-agent (4 prior analysts + 3 orthogonal auditors)
**Contesto:** crash laptop durante analyst run (OOM pandas su 1.3 GB CSV); ripartenza + re-audit con vincoli memoria

---

## Revisione critica: l'analisi di stamattina era INCOMPLETA

L'analista "parquet consistency" della sessione crashata ha auditato il **file sbagliato**: `daily_channel_aggregated.parquet` (v1.0, stale 2026-01-22) invece di `daily_aggregated.parquet` (v1.2, fresh 2026-03-23). Conclusione errata che v1.2 non fosse shippato.

**Rettifica (confermata da 3 agenti indipendenti oggi):** v1.2 è live e funzionante nel runtime.

## Stato reale confermato

### v1.2 — SHIPPED e wired
- `data/baseline/daily_aggregated.parquet`: 5M righe, **7 canali** (GOOGLE_ADEX, DEAL, DIRECT, HEADER_BIDDING_MAGNITE, HEADER_BIDDING_PUBMATIC, TAM, OPEN_BIDDING), 50 publishers, 18 campi, max date **2026-03-23**
- `data/baseline/hourly_aggregated.parquet`: GOOGLE_ADEX only (limite sorgente `hour_kpi.csv`, non del codice)
- A8 gross-margin alert: `backend/agents/anomaly_detector.py:586-639`, enabled in YAML
- Leading indicators CTR/viewability: `anomaly_detector.py:641-707`, P2-WATCH
- Cross-channel detection: attivo
- Runtime read paths corretti: `data_fetcher_real.py:25-28`, `routes.py:79-80`, `publisher_routes.py:20-21`

### 🔴 Root cause della staleness percepita: CHECK constraint stale
**`vna_alerts.db` schema**:
```sql
CHECK (channel_group IN ('GOOGLE', 'OPEN_BIDDING'))  -- v1.0
```
Ma v1.2 pipeline scrive canali `GOOGLE_ADEX, DEAL, DIRECT, ...`.

**Effetto osservato**:
- Ultimo alert persistito: **2026-01-22 14:39:40**
- Alert dopo quel timestamp: **0**
- `pipeline_runs` tra 22-gen e 22-apr: **2590 esecuzioni** → pipeline gira, INSERT falliscono silenziosamente sulla CHECK
- **2 mesi di silent failure** perché nessun monitoring su "pipeline run but 0 alerts written"

### 🟡 WIP 56 file uncommitted (2 mesi di drift)

Classificati in 5 commit logici (vedi `wip-56-file-audit.md`):

| Commit | File | Tema | Rischio |
|---|---|---|---|
| A | 10 | Design system + i18n infra | Basso |
| B | 10 | Traduzione IT→EN docs | Basso |
| C | 2 | Backend correctness (YoY rolling 7w, bacino dedup) | Basso, migliora correttezza |
| D | 8 | Dashboard date picker + nuovo API contract | Medio, dipende da C |
| E | 5 | Vercel static export architectural shift | **Alto**, shelve |

**🚩 Red flag**: `data/vna_alerts.db*` binary diff senza migration script tracciato → qualcuno ha toccato il DB localmente senza storia.

## Piano Stabilization v1.3 (raccomandato 10/10)

### Phase 01 — Intel Freeze (immediata, read-only)
Salva i report degli agenti in `.planning/intel/sentinel-2026-04-22/` (questo file + 4 altri). Aggiorna `STATE.md` con realtà. Zero codice toccato.

### Phase 02 — DB WIP Investigation (1h, read-only)
- Dump schema `vna_alerts.db` WIP vs `git show HEAD:data/vna_alerts.db`
- Diff vs `backend/db/models.py`
- Gate: se WIP contiene lavoro utile → preservare. Spazzatura → reset pulito. Ambiguo → ask Stefano.

### Phase 03 — Safe WIP Commits (mezza giornata, parallel waves)
- Commit A (design system + i18n infra) — atomic
- Commit B (traduzione) — atomic
- Commit C (backend correctness) — atomic con regression test

Indipendenti tra loro, parallelizzabili.

### Phase 04 — 🔴 P0-A Schema Migration (2-3h, atomic)
- Nuovo file: `scripts/migrations/001_expand_channel_groups.sql` (tracked in git)
- CHECK espanso ai 7 canali v1.2
- Aggiorna `backend/db/models.py`
- Backup DB pre-migrazione (rollback garantito, R-04)
- Test: INSERT alert per ciascuno dei 7 canali → PASS
- Atomic commit con rollback plan documentato

### Phase 05 — 🔴 P0-B Alert Backfill (1-2h)
Re-run pipeline `scripts/regenerate_alerts.py` per 2026-01-23 → 2026-04-22. Expected: decine/centinaia di alert recuperati. UI torna viva.

### Phase 06 — 🔴 P0-C Silent-Failure Monitoring (2h, NON-NEGOZIABILE pre-prod)
- Campo `alerts_written_count` in `pipeline_runs`
- Health endpoint `/health/alerts-pipeline`
- Meta-alert interno: `pipeline_runs_last_24h > 0 AND alerts_last_24h == 0` → P0 critical
- Test: simulare constraint violation → verificare che meta-alert scatta

### Phase 07 — Commit D + Contract Test (3h)
Dashboard date picker + nuovo API contract. Depends on C già in main.

### Phase 08 — 🟡 P0-D Triage Server-Side (mezza giornata)
Rimuove `revenueRatio * 0.95` heuristic dal frontend. Aggiunge `baseline_bacino`, `baseline_coverage` al model. Calcolo server-side vero.

### Phase 09 — Decisione Commit E Vercel Static Export
Discussion + plan dedicato. Non blocker per prod — v1.3.1 successiva.

### Phase 10 — Hardening
- Contract test parquet ↔ DB ↔ UI
- Data lineage doc (aggiornamento `DATA_INTEGRATION.md`)
- CI gate per CHECK constraint mismatch future
- Aggiornamento `docs/` operational + technical

## Dimensioni 10/10

| Dimensione | Come il piano lo centra |
|---|---|
| Blast radius minimo (R-04) | Phase 01-02 read-only, backup in 04, rollback ad ogni step |
| Atomic commits (R-03) | 5 commit WIP + 1 migration + 1 backfill + 1 monitoring + 1 triage. Ognuno revertibile |
| Fix-the-code-first (R-10) | Root cause identificato (CHECK constraint), fix mirato. Zero prompt engineering |
| No cascade patches (R-11) | P0-A testato PRIMA di P0-B. Monitoring PRIMA di considerare risolto |
| Persistence (R-08, R-09) | Intel freeze = survives /clear. STATE.md aggiornato |
| Architectural quality (R-13) | Migration scripts tracciati (mai più drift silent). Contract test. Monitoring strutturale |
| Production safety (R-05, R-16) | Deploy è phase separata con snapshot VPS. Zero live actions senza OK |

## Tempo stimato
- Path critico (Phase 01 → 06): **1 giornata piena** → produzione sblocca alert freschi + monitoring
- Path completo (Phase 01 → 10): **3-4 giornate** → ship v1.3 stabilization

## Dipendenze tra phase
```
01 (intel) ─┐
02 (DB inv) ─┼→ 03a/b/c (parallel) ──→ 04 (schema) ──→ 05 (backfill) ──→ 06 (monitor)
                                                                              │
                                                            07 (commit D) ←───┤
                                                            08 (triage)  ←────┤
                                                            09 (E decision)   │
                                                            10 (hardening) ←──┘
```

## Requirement derivati
- **STAB-01**: Schema `vna_alerts.channel_group` accetta 7 canali v1.2
- **STAB-02**: 90 giorni di alert storici backfilled in DB
- **STAB-03**: Pipeline silent-failure monitoring live e testato
- **STAB-04**: WIP 56 file committato in 4 commit atomici tracciati
- **STAB-05**: DB WIP binary diff investigato e reconciled
- **STAB-06**: Triage baseline calcolato server-side (no client-side heuristic)
- **STAB-07**: Contract test parquet ↔ DB ↔ UI (regressione futura impossibile)
- **STAB-08**: Data lineage doc aggiornata a v1.2
- **STAB-09**: CI gate previene future CHECK constraint drift

## Prossimo step
`/gsd-new-milestone` per aprire **v1.3 Stabilization** con queste 9 requirements.

---
canonical: true
mandatory_read: true
last_updated: 2026-04-28
purpose: north-star reference — read FIRST before any action on Sentinel v1.3
---

# 🌟 STELLA POLARE — Sentinel v1.3

> **Ogni Claude session che entra in questo progetto DEVE leggere questo file prima di proporre QUALSIASI azione.** Non è un suggerimento. È un vincolo del milestone v1.3 stesso.

## Da dove parte tutto

**Email Vito Sena (head TAM&Yield) → Stefano, 2026-04-22**: 8 numeri sulla dashboard Sentinel non tornano vs Power BI. È la verità centrale di v1.3. Senza questa, qualunque ragionamento è speculazione.

📄 **Email verbatim** → `.planning/intel/sentinel-2026-04-28/EMAIL-VITO-2026-04-22.md`

## Cosa abbiamo scoperto (audit triplo 2026-04-28)

3 auditor indipendenti hanno verificato l'email contro parquet, DB, live Vercel, e codice:

| Trovato | Conseguenza |
|---------|-------------|
| Vito ha ragione su tutti gli 8 punti | Verificato indipendentemente, 3/3 audit |
| Le 8 lamentele = **5 root cause** (a/b/c/d/e + label f) | Vedi `SYNTHESIS.md` §"Le 5 ROOT CAUSE" |
| **Phase 07-10.2 NON cambia nessun numero email** | Hanno fixato un bug DIVERSO (silent failure 2-month CHECK constraint) |
| Le RC indirizzate da Phase 11+12+13+14 | Nessuna ancora implementata |
| Live Vercel = deploy non-tracciato da WIP working tree | Mar 26 JSON snapshot, frontend i18n WIP, niente di Phase 07-10.2 |
| Path A (refresh JSON) NON risolve | I numeri sbagliati sono di calcolo, non di freshness |

📄 **Sintesi** → `.planning/intel/sentinel-2026-04-28/SYNTHESIS.md` (LEGGI QUESTO se hai tempo per UN solo file)

## Le 5 root cause canoniche

```
(a) Top-50 publisher filter senza disclaimer    → Phase 13/14 (CORR-04)
(b) Mondadori family non aggregati              → Phase 12/13 (NEW: publisher_family)
(c) NET vs GROSS senza label (€115k=€188k×0.6)  → Phase 13 (CORR-03 D2)
(d) Legacy 'GOOGLE' channel naming              → Phase 12 (migration/filter)
(e) Client-side heuristics in TriageSection     → Phase 11/12 (CORR-01 + API-03)
(f) Timestamp/timezone label mancante           → Phase 14 (CORR-02 + CORR-05)
```

## Stato coverage live (al 2026-04-28)

```
Componente                Local-main  Origin/main  Vercel-Live
i18n + dashboard refactor   ❌          ❌            ✅ (deploy non tracciato)
Backend bacino dedup        ❌          ❌            ✅ (output 133M)
Phase 07-10.2 silent-fix    ✅          ❌ (158 ahead) ❌
Phase 11+ (email fix)       ❌          ❌            ❌
```

**Origin/main fermo a Feb 21.** Local main 158 commit ahead non pushati.

## Anti-pattern PROIBITI (no più speculazione)

1. ❌ **Non assumere il contenuto dell'email senza leggerla verbatim.** Va ricontrollata in `EMAIL-VITO-2026-04-22.md`.
2. ❌ **Non proporre Path A (refresh JSON + redeploy)** come fix all'email. Documentato non risolve.
3. ❌ **Non confondere `[x]` in REQUIREMENTS.md con "live"**. Il gap deploy è enorme.
4. ❌ **Non confondere WIP `7ea4a74` bacino dedup con fix RC-b**. Sono due cose diverse: dedup matematica ≠ aggregazione publisher_family.
5. ❌ **Non fare `git stash` con `data/vna_alerts.db*` modificato**. Conflitti su binario garantiti.
6. ❌ **Non fare deploy senza esplicito OK Stefano**. Ogni deploy = R-04 + R-05.

## Riferimenti obbligatori (in ordine)

```
.planning/intel/sentinel-2026-04-28/
├── EMAIL-VITO-2026-04-22.md       ← TRUTH SOURCE
├── SYNTHESIS.md                    ← se leggi 1 file, leggi questo
├── README.md                       ← indice
├── AUDIT-A-NUMBERS-FORENSICS.md    ← code-path tracing
├── AUDIT-B-PHASE-COVERAGE.md       ← critical path
└── AUDIT-C-LIVE-VS-EMAIL.md        ← three-way live forensics + briefing pronto
```

Plus:
- `.planning/PROJECT.md` — milestone v1.3 goal
- `.planning/ROADMAP.md` — phase details 07-18
- `.planning/REQUIREMENTS.md` — CORR/SCHEMA/MONITOR/API/HARD requirements
- `.planning/STATE.md` — current execution position
- `.planning/intel/sentinel-2026-04-22/` — analisi originale che ha aperto v1.3

## Decisioni operatore aperte (al 2026-04-28)

1. Email reply a Vito: prima di Phase 11 o dopo?
2. Phase 11 vs 12 ordering
3. `publisher_family` definition (Mondadori = M + M_npa + Adgage_mondocore + Mediamond?)
4. Sell type filter scope (filter o badge)
5. Vercel deploy strategy (push origin/main? Vercel project naming?)

Vedi `SYNTHESIS.md` §"Cosa SOLO STEFANO può decidere" per dettaglio.

## Storia recente

| Data | Evento |
|------|--------|
| 2026-04-22 | Email Vito ricevuta. Milestone v1.3 aperto. Intel `sentinel-2026-04-22/` (silent failure root-cause) |
| 2026-04-23 → 2026-04-25 | Phase 07-10.1 + 999.1 implementate (silent failure fixed) |
| 2026-04-27 | Phase 10.2 (3/4 plans). 10.2-04 webhook deferred via abort |
| 2026-04-27 (12:45 GMT) | Deploy Vercel non tracciato (da WIP working tree) — frontend i18n + bacino dedup live, JSON Mar 26 snapshot |
| 2026-04-28 | Audit triplo + sintesi: scoperto Phase 07-10.2 ≠ email fix. Pivot a Phase 11+. |

---

*Questo file evolve solo a milestone transitions o quando emerge nuova evidenza canonica. Modifiche minori (status, decisioni chiuse) accettabili. Modifiche maggiori (riscrittura root cause) richiedono nuovo audit.*

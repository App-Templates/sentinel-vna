---
intel_index: true
date: 2026-04-28
status: CANONICAL — read this first when entering Sentinel v1.3 work
---

# Intel 2026-04-28 — Indice

**Truth source:** Email Vito 2026-04-22 + audit triplo del 2026-04-28.

## Ordine di lettura obbligatorio

1. **`EMAIL-VITO-2026-04-22.md`** — l'email originale verbatim + decomposizione canonica delle 8 lamentele in 6 categorie
2. **`SYNTHESIS.md`** — sintesi convergente dei 3 audit, 5 root cause, decision card. **Se hai tempo per UN solo file, leggi questo.**
3. **`AUDIT-A-NUMBERS-FORENSICS.md`** — per ogni numero email → endpoint backend → file:line → formula bug. Include simulazione WIP commit C contro parquet reale.
4. **`AUDIT-B-PHASE-COVERAGE.md`** — phase ledger 07-18 + critical path + 2-day quick-win analysis
5. **`AUDIT-C-LIVE-VS-EMAIL.md`** — live forensics three-way (PBI / Vercel / Local) + 1-page operator briefing pronto da inviare a Vito

## Convergenza audit (sommario)

Tutti e 3 confermano:
- Vito ha ragione su tutti gli 8 punti
- 5 root cause (a)/(b)/(c)/(d)/(e) + 1 RC label (f)
- Phase 07-10.2 NON ha cambiato nessun numero che Vito cita
- Path A (refresh JSON) NON risolve i bug di calcolo
- WIP `7ea4a74` bacino dedup non è la soluzione di RC-b (Mondadori family aggregation)
- Live Vercel deploy è di provenienza non-tracciata (deploy fatto da WIP working tree, non da main HEAD)

## Caveat per Claude future sessions

- **Non riproporre Path A** (deploy refresh) come soluzione all'email. Documentato anti-pattern in SYNTHESIS.md "Lessons learned".
- **Non confondere "main fix" con "live fix".** Il gap deploy è la metà del problema.
- **Non assumere il contenuto dell'email** se non verbatim. Citato verbatim in EMAIL-VITO-2026-04-22.md.
- **Riferirsi a questa cartella** come fonte di verità prima di proporre azioni su Sentinel v1.3.

## Storia

- 2026-04-22: email Vito ricevuta da Stefano. Apre milestone v1.3 Stabilization.
- 2026-04-22: 6 intel files originali in `.planning/intel/sentinel-2026-04-22/` (analisi pre-fase, root-cause silent failure).
- 2026-04-22 → 2026-04-27: Phase 07-10.2 implementate (silent failure fix).
- **2026-04-28: scoperto che le phase fatte NON indirizzano l'email. Audit triplo + sintesi qui presente. Pivot esplicito verso Phase 11+.**

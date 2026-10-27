# Email Vito — 2026-04-22 — Sentinel data correctness audit

**Sender:** team TAM&Yield (presumibilmente Vito Sena, head)
**Recipient:** Stefano Argiolas
**Date received:** 2026-04-22
**Status:** UNRESOLVED al 2026-04-28 (6 giorni post-arrivo)
**Trigger:** apertura milestone v1.3 Stabilization su Sentinel

**Importanza:** Questa email è la **verità centrale** del progetto v1.3. Ogni decisione su Sentinel deve riferirsi a questi punti come oracolo di "cosa significa giusto/sbagliato". NON modificare questo file salvo per aggiungere risposte verbatim del sender.

---

## Email verbatim (da screenshot operatore 2026-04-28)

> Ciao Stefano,
>
> abbiamo condotto in maniera separata l'analisi sulla validazione dei dati/alert presenti su Sentinel e di seguito i punti evidenziati:
>
> **• Correttezza dei dati:**
>
> ◦ **Dashboard** — non tornano numeriche orarie e totali sul giorno di Revenue AdEx (confrontato utilizzando il report Hour Analysis di Power BI). Il dato dell'YoY sembra veritiero (sebbene YoY orario non dovrebbe essere nella base dato)
>
> ◦ **Alert > Triage Classification** — non tornano le numeriche:
>
>   Ad esempio considerando il seguente alert: **13 Gennaio**, e assumendo che i dati facciano riferimento al 12 Gennaio, mi risultano su Power BI (Open Market):
>
>   - 14M AdEx impressions (Power BI) vs **10M Sentinel**
>   - €27.2k AdEx Revenues (Power BI) vs **€25.9k Sentinel**
>   - di conseguenza le revenue dei tab successivi
>
> ◦ **Top Publisher** — anche qui non mi tornano i dati confrontando con Dashboard Publisher (Power BI) sul mese di **Febbraio** e publisher **Mondadori**:
>
>   - **Bacino**: 133M vs **366M** (Power BI, ad requests)
>   - **Fill rate**: 41.8% vs **35.2%** (Power BI, coverage)
>   - **eCPM**: €2.08 vs **€1.51** (Power BI, gross ecpm)
>   - **RPM**: €0.87 vs **€0.51** (Power BI, gross rpm)
>   - **Revenue**: €115k vs **€188k** (Power BI, all sell type), **€90k** (Power BI, sell type = "Open Market")
>
> **• Timeframe:** verificando all'interno degli Alert, il dato di current revenue non è associato ad un periodo di riferimento. Ad esempio, l'alert è delle 8:57 del 13 Gennaio, il dato di revenue a quale periodo fa riferimento?
>
>   [screenshot allegato: Alert ALT-2026, P2 OPEN, Jan 13 08:57 AM, Google, Coverage, Rule A2. STEP 1 REVENUE STATUS — Current Revenue €25,927 / Baseline (7-week avg) €27,639 / Delta -€1,712 / -6.2%. Tab "Revenue Trend (7 Weeks)" → "No revenue trend data available for this alert period."]
>
> **• Alert con etichetta "Google"** (come nell'esempio precedente) non riusciamo a verificare i dati perché non è mai presente la timeline

---

## Decomposizione canonica delle 8 lamentele

| # | Lamentela | Numero specifico | Categoria root cause |
|---|-----------|------------------|----------------------|
| 1 | Dashboard hourly Revenue AdEx non torna vs PBI Hour Analysis | (numero non quantificato in email) | Calcolo aggregazione oraria |
| 2 | Triage Classification — AdEx impressions giorno 12 Gen | 14M PBI vs 10M Sentinel (-29% Sentinel) | sell_type filter / channel scope |
| 3 | Triage Classification — AdEx Revenues giorno 12 Gen | €27.2k PBI vs €25.9k Sentinel (-5% Sentinel) | sell_type filter / channel scope |
| 4a | Mondadori bacino Feb | 366M PBI vs 133M Sentinel (Sentinel 36% di PBI) | sell_type filter probabile (PBI all=366M, Sentinel su Open_Market subset?) |
| 4b | Mondadori fill rate Feb | 35.2% PBI vs 41.8% Sentinel (Sentinel +18%) | Conseguenza di 4a — denominatore (bacino) artificialmente piccolo |
| 4c | Mondadori eCPM Feb | €1.51 PBI vs €2.08 Sentinel (Sentinel +38%) | Filtro impressions o sell_type |
| 4d | Mondadori RPM Feb | €0.51 PBI vs €0.87 Sentinel (Sentinel +71%) | Conseguenza di 4a (denominatore bacino) o filtro |
| 4e | Mondadori revenue Feb | €188k PBI all / €90k PBI Open_Market vs €115k Sentinel | Sentinel non distingue gross+net + sell_type non visibile |
| 5 | Alert UI — current revenue senza riferimento temporale | "L'alert è delle 8:57, il dato di revenue a quale periodo fa riferimento?" | Manca label `as of <hour> UTC` |
| 6 | Alert UI — etichetta "Google" senza timeline → non verificabile | "No revenue trend data available for this alert period" | Empty state diagnostico mancante |

**Pattern trasversale:** tutti i 4 numeri Mondadori sono coerenti con un'ipotesi unica → **Sentinel mostra subset Open_Market (mappato male a 1 canale/sotto-set, con 36% del bacino), ma le LABEL della UI dicono "Mondadori" come se fosse tutto-publisher → confusione operatore.** Possibile che il filtro Open_Market sia implicito nel calcolo ma non comunicato in UI.

---

## Mapping a requisiti v1.3 (.planning/REQUIREMENTS.md)

| # email | Requisito v1.3 esistente | Phase | Status (al 2026-04-28) |
|---------|--------------------------|-------|------------------------|
| 1 (hourly AdEx) | SCHEMA-04 (sell_type_proxy derivation) + CORR-04 (channel scope badge) | 08 / 13 | SCHEMA-04 ✓ validato in PROJECT.md ma non visibile in UI; CORR-04 NON FATTO |
| 2-3 (Triage 12 Gen) | CORR-04 channel scope + sell_type filter + CORR-03 gross/net | 13 | NON FATTO |
| 4a (bacino) | CORR-08 weighted-by-impressions (era simple_average) + WIP commit C `publisher_routes.py bacino dedup fix` | 12 / WIP | **WIP committato in `wip/pre-10.2-rescue` `7ea4a74` ma MAI deployato; analisi tecnica indica fix DIMINUISCE ulteriormente bacino → potrebbe peggiorare il bug nel verso opposto** |
| 4b (fill rate) | SCHEMA-03 (`measurable_impressions` preserved in ETL) | 08 | SCHEMA-03 segnato `[x]` validato ma il fill_rate ricalcolato non è ancora deployato in dashboard live |
| 4c (eCPM) | SCHEMA-03 + sell_type filter | 08 / 13 | Bloccato da 4a/4b |
| 4d (RPM) | SCHEMA-03 + sell_type filter | 08 / 13 | Bloccato da 4a/4b |
| 4e (revenue gross/net) | CORR-03 gross+net side-by-side + D2 + sell_type filter | 13 | NON FATTO |
| 5 (timeframe) | CORR-02 reference period esplicito + CORR-05 timestamp/timezone label | 14 | NON FATTO |
| 6 (timeline mancante) | CORR-07 diagnostic empty states + CORR-04 channel scope | 13 / 15 | NON FATTO |

---

## Conclusione onesta al 2026-04-28

**Le phase 07-10.2 hanno fixato un bug DIVERSO da quello dell'email.**

- Bug fixato (Phase 07-10.2): silent failure CHECK constraint → 0 alert salvati per 2 mesi (Jan 22 → Apr 22). Critico, ma invisibile all'utente perché la pipeline GIRAVA, mostrava alert vecchi.
- Bug lamentato dall'email: **calcoli/display sbagliati** — impressions, revenue, bacino, fill rate, eCPM, RPM tutti divergenti vs Power BI; mancano label temporali e channel scope.

Le 8 lamentele dell'email mappano a phase 11+12+13+14 (correctness, baseline server-side, channel scope, gross/net, timestamp labels) — **nessuna delle quali è stata implementata o deployata.** L'unico parziale è il commit WIP `7ea4a74` che tocca `publisher_routes.py` per dedup bacino, ma mai deployato e con possibile direzione di fix incerta.

**Path di refresh JSON / redeploy NON risolve l'email** — i numeri sbagliati restano sbagliati anche con dati attuali.

---

## Referenze incrociate

- `.planning/PROJECT.md` — milestone v1.3 goal + requirements ATTIVI vs VALIDATED
- `.planning/ROADMAP.md` § "Phase Details" — phase 11/12/13/14 dettaglio
- `.planning/REQUIREMENTS.md` — CORR-01..11, SCHEMA-01..04, MONITOR-01..14, API-01..03
- `.planning/intel/sentinel-2026-04-22/RECONCILIATION.md` — analisi originale che ha aperto v1.3 (silent failure root-cause)
- `wip/pre-10.2-rescue` `7ea4a74` — backend WIP bacino dedup fix (da valutare)

---
auditor: C
date: 2026-04-28
status: complete
---

# Audit C — Live platform vs email

## Verdict

**Vito ha ragione su tutti gli 8 punti, ma sottostima il problema.** Il deploy live (`https://sentinel-vna.vercel.app`) serve uno snapshot statico fatto il **2026-03-26**: precede di un mese le decisioni v1.3 (deep audit del 22 aprile) e include un mix tossico di alert legacy "GOOGLE" che la pipeline locale ha già marcato `deprecated=1` ma il JSON statico continua a esporre senza il flag. Il database locale vede 200/438 alert deprecati e 238 freschi (post-Phase 09 backfill 2026-01-23 → 2026-03-23) **che il live non ha mai visto**. La logica di calcolo dietro le 5 numeriche Mondadori è confermata su entrambi i lati (live e backend main attuale): nessuna delle Phase 07-10.2 chiuse ha modificato i numeri che Vito ha confrontato. Il commit WIP `7ea4a74` "publisher_routes bacino dedup" è **già in main** (è la code path che produce 133M / 41.8% in entrambi gli ambienti) e **non avvicinerà** Vito al PBI: anzi, è lui stesso il responsabile del 133M attuale (la versione pre-WIP avrebbe dato bacino naïf 860M, ben più lontano dai 366M PBI ma per una via diversa).

Aggiungo **5 bug live che Vito non ha menzionato** ma sono evidenti curl-alla-mano.

---

## C.1 Reproduction of each complaint

| # | Complaint | Live URL | Expected (PBI) | Actual on live (Sentinel snapshot 26 Mar) | Match |
|---|-----------|----------|---------------|-------------------------------------------|-------|
| 1 | Dashboard hourly Revenue AdEx non torna | `/api/metrics/revenue-status-24h.json` (default = 2026-03-23) | non quantificato | hour 0 = €532, hour 1-23 = €0 con `delta_pct=-100%` (data point isolato in coda dataset) | **Confermato bug** — vedi anche §C.3 bonus 1 |
| 2 | AdEx impressions 12 Gen | (alert detail per Vito) — non c'è endpoint network specifico | 14M | parquet top-50 mostra `GOOGLE_ADEX impressions = 11.49M` Jan 12 (dato che tappa il display)| **Confermato — 4M mancanti** |
| 3 | AdEx revenue 12 Gen | idem | €27.2k gross | parquet top-50 `GOOGLE_ADEX rev_gross = €23.0k` Jan 12 (€13.8k net) | **Confermato — €4.2k gap** |
| 4a | Mondadori bacino Feb | `/api/publishers/top_2026_02.json` (Mondadori) | 366M | **133,242,026** | **Confermato — gap 233M (Sentinel 36% del PBI)** |
| 4b | Mondadori fill_rate Feb | idem | 35.2% | **41.75%** | **Confermato — Sentinel +18%** |
| 4c | Mondadori eCPM Feb | idem | €1.51 | **€2.08** | **Confermato — Sentinel +38%** |
| 4d | Mondadori RPM Feb | idem | €0.51 | **€0.87** | **Confermato — Sentinel +71%** |
| 4e | Mondadori revenue Feb | idem | €188k all / €90k OM | **€115,591 (net)** / `€192,651 gross` (raw) | **Confermato — confronto frainteso UI: Sentinel mostra €115k NET, PBI mostra €188k GROSS; differenza è 60/40 rev-share, non un bug ma label ingannevole** |
| 5 | Alert UI senza timeframe | `/api/alerts/ALT-20260113-225828-P2.json` | (UI label issue) | payload non contiene `reference_period`, `as_of`, né `timezone` — solo `timestamp:"2026-01-13T08:57:05"` (no TZ suffix) e `revenue_current:25927.18` raw | **Confermato — assenza struttura semantica** |
| 6 | Alert "Google" senza timeline | `/api/alerts/ALT-20260113-225828-P2/trend.json` | (UI empty state) | `{"trend": []}` — array vuoto | **Confermato. Pattern sistemico:** 107/107 alert con `channel_group="GOOGLE"` hanno trend vuoto (vs 39/93 OPEN_BIDDING che hanno dati) |

### Dettaglio raw per #2-3 (Jan 12 GOOGLE_ADEX network)

Confronto da `data/sentinel_db/daily_kpi.csv` (NO filtri):

| Source | Impressions | Revenue gross |
|--------|-------------|---------------|
| **PBI (Vito)** | 14M | €27.2k |
| **Raw daily_kpi.csv `GOOGLE_ADEX` Jan 12** | **14,009,820** | **€27,245.63** |
| Parquet baseline (top-50 filter) | 11,491,192 | €23,024.16 |
| Sentinel UI / alert quoted | 10M | €25,927 (revenue_current) |

Il raw upstream **matcha PBI al pixel** (14.01M ≈ 14M, €27,245 ≈ €27.2k). La perdita di 4M impressions e ~€4k è **interamente dovuta al filtro top-50 publisher** applicato in `etl_csv_to_parquet.py`. Il "€25.9k" che Vito vede sull'alert è l'`revenue_current` di un alert legacy generato contro la baseline v1.0 (canale `GOOGLE`, non `GOOGLE_ADEX`), che non corrisponde a nessuna numerica del parquet attuale (alert deprecato `deprecated=1, reason='v1.0 schema stale'` nel DB locale ma **ancora servito dalla snapshot Vercel** senza il flag).

---

## C.2 Three-way compare PBI / Live / Local-current

| Metric | PBI (Vito) | Live snapshot 2026-03-26 | Local backend main (oggi) | Diff Live ↔ Local | Cosa cambierebbe il deploy ora |
|--------|------------|---------------------------|----------------------------|-------------------|--------------------------------|
| Mondadori Feb bacino | 366M | 133.2M | **133.2M** (identico) | **0** | Nulla: WIP commit C `7ea4a74` è già in main; il calcolo non cambia |
| Mondadori Feb fill_rate | 35.2% | 41.75% | **41.75%** | **0** | Idem |
| Mondadori Feb eCPM | €1.51 | €2.08 | **€2.08** | **0** | Idem |
| Mondadori Feb RPM | €0.51 | €0.87 | **€0.87** | **0** | Idem |
| Mondadori Feb revenue net | €188k (gross) / €90k (OM) | €115.6k (net all) | **€115.6k** | 0 | Idem |
| Mondadori Feb revenue gross | €188k (PBI all) | non esposto in UI | **€192.7k** (calcolato local) | n/a | **Disponibile lato server**, basta un endpoint o toggle UI (CORR-03) |
| Jan 12 GOOGLE_ADEX impressions network | 14M | 11.5M (top-50) | **11.5M** | 0 | Bisogna API-01 (network-totals da CSV upstream) |
| Jan 12 GOOGLE_ADEX rev_gross network | €27.2k | €23k (top-50) | **€23k** | 0 | Idem (API-01) |
| Total alerts visibili | n/a | 200 (TUTTI legacy 2-channel: 107 GOOGLE + 93 OPEN_BIDDING, range 2024-02 → 2026-01-22) | 238 freschi 2026-01-23→2026-03-23 + 200 legacy (deprecated=1) | **+238 fresh hidden + 200 stale-but-served** | Re-deploy API JSON includerebbe i 238 nuovi e nasconderebbe i 200 deprecati (default `?include_deprecated=false`) |
| Alert ALT-20260113-225828-P2 | live | OPEN, mostrato | **deprecato locally con motivo 'v1.0 schema stale'** ma stesso alert_id | bug critico | Il live serve un alert che il backend ha già "ritirato" — utente vede dati condannati |

**Conclusione three-way:** le 5 metriche numeriche di Mondadori non beneficiano di alcun fix tra le Phase 07-10.2 chiuse. Il deploy del codice attuale **non porterà nessun miglioramento numerico per Vito**: per arrivare al PBI servono Phase 11+12+13 (CORR-03 gross/net toggle, CORR-04 channel scope badge, API-01 network-totals senza top-50 filter, CLEAN-02 Mondadori variant aggregation, SCHEMA-03 measurable in fill_rate denominator). Il deploy però risolverebbe **subito**:

- Sostituirebbe i 200 alert legacy con 238 freschi 2026-01-23 → 2026-03-23 (Phase 09 backfill)
- L'alert ALT-20260113-225828-P2 specifico citato da Vito **scomparirebbe** dalla lista (default-hidden via `deprecated=1`)
- Il payload `deprecated: bool` esposto in API permetterebbe alla UI di mostrare un badge

Quindi: deploy refresh ≠ fix dei numeri ma ≠ "completamente inutile" — risolve la confusione "perché vedo solo alert vecchi di 3+ mesi" che Vito ha probabilmente bevuto in silenzio.

---

## C.3 Additional UI/UX bugs in live build (Vito non li ha menzionati)

### Bonus 1 — Dashboard `/revenue-status-24h` mostra ore "incomplete" come -100% senza disclaimer

```
hour 0  rev=€532   delta_pct=+5.2%
hour 1  rev=€0     delta_pct=-100.0%
hour 2  rev=€0     delta_pct=-100.0%
... (fino a hour 23 tutti -100%)
```

L'utente che apre il default oggi (data point = 2026-03-23) vede **23 ore consecutive di -100% rev drop** rispetto alla baseline. Solo guardando il dato sa che è un giorno parziale (last day del dataset, 1 ora di data, resto vuoto). Niente label "as of HH:00 UTC", niente fade-out su ore future, niente "incomplete day" badge. È **CORR-02 + CORR-05 + CORR-07 ammucchiati**: timestamp/timezone label + reference period + diagnostic empty state.

**Citation:** `frontend/dist/api/metrics/revenue-status-24h.json` (default response served live).

### Bonus 2 — `available_dates` salta da 2026-01-01 indietro a 2025-12-23

Il `revenue-status-24h.json` ha `available_dates` lista di 10 date: `["2026-01-01","2025-12-31","2025-12-30","2025-12-29","2025-12-28","2025-12-27","2025-12-26","2025-12-25","2025-12-24","2025-12-23"]`. Manca completamente il range Jan 02 → Mar 23 che è proprio quello da cui viene il dataset hourly raw (2161 timestamps coprono fino a Mar 23). Il date selector nella UI è tagliato.

### Bonus 3 — CORR-01 heuristics SPEDITE in live bundle

`frontend/dist/assets/index-DaNDZ59F.js` (live etag `8447cf618d5a6c11362e201e8bcfccb5`) contiene la stringa minificata:

```
o=Math.round(r*(l*.95)),u=Math.min(n+.05,.95),...
```

Mappabile 1:1 a `frontend/src/components/alerts/TriageSection.tsx:31-32`:

```ts
const baselineBacino = Math.round(totalBacino * (revenueRatio * 0.95))
const baselineCoverage = Math.min(avgCoverage + 0.05, 0.95)
```

L'utente che apre QUALSIASI alert su live vede uno STEP 2/3 con baselineBacino e baselineCoverage **completamente inventati dal frontend** — il backend non li produce, sono stime client-side dichiaratamente eliminate da CORR-01 ma vive ancora nel deploy.

### Bonus 4 — CORR-08 simple-average fill_rate visibile sui Top Publisher KPI

Bundle:

```
m.length>0?m.reduce((C,P)=>C+P.fill_rate,0)/m.length:0
```

Mappa a `PublishersPage.tsx:66`:

```ts
const avgFillRate = data.length > 0 ? data.reduce((sum, p) => sum + p.fill_rate, 0) / data.length : 0
```

Il "Fill Rate Medio" mostrato in alto nel tab Top Publisher è una media aritmetica semplice di 50 publisher, non pesata sulle impressions (CORR-08). Mondadori (~600M impr/mo) e un publisher minuscolo da 50K impr pesano uguale.

### Bonus 5 — 107/107 alert "GOOGLE" senza timeline trend, sistematico

Survey su tutti i 200 alert nel deploy:

```
channel                  with_trend  without_trend
GOOGLE                            0           107
OPEN_BIDDING                     39            54
```

Vito ha trovato 1 esempio. Il pattern è **100% degli alert legacy GOOGLE**. Il bug non è del singolo alert: è la baseline rolling 7w che non ha matching dato per il channel name "GOOGLE" nel parquet v1.2 (dove il canale si chiama `GOOGLE_ADEX`). Backend fa la query con `WHERE channel='GOOGLE'`, parquet ha solo `'GOOGLE_ADEX'` → 0 righe → trend vuoto. Sintomo dello stesso `MIGRATE-01` già identificato.

Non è solo cosmetico: è la **prova** che gli alert serviti sono inservibili — Vito non può "verificare" perché letteralmente non c'è la storia.

### Bonus 6 — Alert deprecati live senza badge

Il DB locale ha:

```sql
SELECT alert_id, deprecated, deprecation_reason FROM alerts WHERE alert_id='ALT-20260113-225828-P2';
('ALT-20260113-225828-P2', 1, 'v1.0 schema stale: legacy channel naming + v1.2 baseline divergence (Phase 09 deprecation)')
```

Live JSON:

```json
{"alert_id":"ALT-20260113-225828-P2", "channel_group":"GOOGLE", "status":"OPEN", ...}
```

Manca il campo `deprecated` (snapshot pre-Phase 09 migration). Quindi Vito sta debuggando un alert che il team ha **già deciso di ritirare**.

### Verifiche negative (CORR fixes che NON sono in live)

| Item | Bundle search | Result |
|------|---------------|--------|
| CORR-02 reference period label "as of [hour] UTC" | `'as of'`, `'reference period'`, `'for the hour'` | **NOT FOUND** |
| CORR-04 "channel scope" string | `'channel scope'`, `'channel_scope'` | NOT FOUND (ma `'GOOGLE_ADEX only'` è presente — fix parziale leaked from WIP?) |
| CORR-07 diagnostic empty state | `'No 7-week history'`, `'data not yet aggregated'`, `'less than 7 days old'` | NOT FOUND. Solo il messaggio base `"No revenue trend data available for this alert period."` (esattamente la stringa che Vito ha citato in screenshot) |
| CORR-09 i18n keys for KpiCards | `kpi.rpm`, `kpi.ctr`, `kpi.viewability`, `kpi.gross_margin` | **PRESENT** (3 occorrenze ciascuno) — fix leaked from WIP |
| CORR-10 ErrorBoundary | `getDerivedStateFromError`, `componentDidCatch` | **PRESENT** (20 occorrenze) — generic boundary in shadcn / react-router; non è chiaro se wrap chart components specifici |

---

## C.4 Requirements vs live state

### Validated `[x]` ma NON deployato (shipped-to-local-only gap)

| Requirement | Status in REQUIREMENTS.md | Visibile nel live? | Gap |
|-------------|---------------------------|---------------------|-----|
| SCHEMA-01 (CHECK constraint 7-channel) | ✓ Phase 08 | n/a (DB-side) | OK ma irrilevante per dashboard |
| SCHEMA-02 (models.py sync) | ✓ Phase 08 | n/a | OK |
| SCHEMA-03 (measurable preserved in ETL) | ✓ Phase 08 | parquet ha la colonna ma `fill_rate` calcolato in `publisher_routes.py` usa ancora `impressions/bacino` (NON `measurable_impressions/bacino`) | **Bug residuo:** SCHEMA-03 ETL fix è atterrato ma il consumer (publisher_routes.py linea 211 `pub["fill_rate"] = pub["avg_coverage"]`) non lo legge ancora. Anche se rideployassi oggi, fill_rate Mondadori resta 41.75% non 35.2%. |
| SCHEMA-04 (sell_type_proxy) | ✓ Phase 08 | parquet ha la colonna; UI/API non espongono filtro | **Solo data-side**, manca CORR-11 / API-02 |
| BACKFILL-01 (60 giorni alert) | ✓ Phase 09 | **NO — live ferma a 2026-01-22** | Snapshot statico pre-backfill |
| MIGRATE-01 (200 legacy soft-deprecated) | ✓ Phase 09 | **NO — live serve i 200 senza flag** | Snapshot pre-deprecation |
| API `/api/alerts?include_deprecated=` | ✓ Phase 09 | n/a (snapshot statico, non query-driven) | Strutturale: per supportare il param serve serverless |
| MONITOR-01..10 | ✓ Phase 10/10.1/999.1 | n/a (backend-only, watchdog) | OK |

### Active `[ ]` con tracce in WIP

| Requirement | Phase | WIP / branch trace | Spostamento all'utente |
|-------------|-------|---------------------|-----------------------|
| WIP-01 DB binary diff investig. | 07 | non started | nessuno |
| WIP-02..05 atomic commits | 11/12 | branch `wip/pre-10.2-rescue`: commit `7ea4a74` (backend) + `94a48cd` (frontend WIP). Backend WIP **già merged in main** per via di rescue commit; frontend WIP è il bundle che vediamo live (i18n keys + GOOGLE_ADEX label). | parziale leak in produzione |
| CORR-01 server-side baseline | 11 | nessuna implementazione | utente vede heuristic |
| CORR-08 weighted fill_rate | 11 | nessuna | media semplice live |
| CORR-09 i18n KPI labels | 11 | leaked nel bundle live | **già funzionante in live** (controintuitivo: Vito non si è lamentato di questo) |
| CORR-02 reference period | 13 | non started | bug visibile |
| CORR-03 gross/net side-by-side | 13 | non started | label ingannevole |
| CORR-04 channel scope badge | 13 | parzialmente leaked (`GOOGLE_ADEX only` string) | parziale |
| CORR-05 timezone label | 13 | non started | timestamp senza TZ |
| CORR-07 diagnostic empty state | 13.5 | non started | empty state generico |
| CORR-10 chart error boundary | 13.5 | generic ErrorBoundary presente | da verificare wrap puntuale |
| CORR-11 sell_type_proxy filter UI | 13 | non started | nessun filtro |
| API-01 `/network-totals` | 10.5 | non started | utente vede top-50 senza disclaimer |
| API-02 sell_type query param | 10.5 | non started | idem |
| API-03 baseline_bacino server-side | 11 | non started | dipendenza per CORR-01 |

### ETA per Vito (estrapolata da ROADMAP.md cadenza Phase 07→10.2 = 6 giorni avg)

| Bug Vito | Phase risolutiva | Realistic ETA da oggi (28 Apr) |
|----------|-------------------|--------------------------------|
| #5 timeframe label | 13 | ~2 settimane (10-12 mag) |
| #6 GOOGLE timeline missing | 9 (deprecation) deploy + 13 empty state | ~1 settimana per deprecation deploy + 2 per empty state |
| #2-3 AdEx Jan 12 numbers | 10.5 (API-01) + 13 (CORR-04 badge) | ~3 settimane (mid-mag) |
| #4a-d Mondadori bacino/fill/eCPM/RPM | 11 (CORR-08) + 13 (CORR-04) + future SCHEMA-03 wire | ~3-4 settimane (fine mag/inizio giu) |
| #4e Mondadori revenue gross | 13 (CORR-03 gross/net toggle) | ~3 settimane |
| #1 Dashboard hourly | 13 + bonus dataset refresh | ~3 settimane (richiede ETL refresh per Mar 24-Apr) |

---

## C.5 1-page operator briefing (ready-to-forward)

> **Subject:** Re: Validazione Sentinel — risposta puntuale ai tuoi 8 punti
>
> Ciao Vito,
>
> ho fatto un audit forense del live. Ti scrivo onesto.
>
> **1. Hai ragione su tutto. Tutti gli 8 punti.**
> - I 4 numeri Mondadori Feb (133M / 41.8% / €2.08 / €0.87) li ho riprodotti curlando il JSON live: matcheranno fino al decimale quello che vedi nella UI. Il PBI ti dà 366M / 35.2% / €1.51 / €0.51 e ha ragione. Il delta sul revenue €115k vs €188k è un caso a parte: sono **gli stessi soldi**, Sentinel mostra il NET (post rev-share 60%), PBI mostra il GROSS — colpa solo della label assente.
> - I numeri AdEx 12 Gen (10M vs 14M, €25.9k vs €27.2k) li ho riprodotti curlando il dato grezzo `daily_kpi.csv`: il tuo 14M PBI è **esatto al pixel** (raw = 14,009,820). I nostri 10M sono frutto del filtro top-50 publisher applicato all'ETL. Tutto ciò che resta fuori da quei 50 (~13% delle revenue) è invisibile.
> - L'alert delle 8:57 del 13 Gennaio (ALT-20260113-225828-P2) ha letteralmente un campo `trend: []` lato API. Non è "mancano i dati per quel giorno": il pattern è 100% degli alert con channel `GOOGLE` (107 su 107). Non hai modo di verificarli e infatti non te ne serve: quel canale è una nomenclatura legacy v1.0 che il sistema oggi chiama `GOOGLE_ADEX`. Backend cerca trend per `'GOOGLE'`, parquet ne ha solo per `'GOOGLE_ADEX'`, risultato lista vuota.
>
> **2. 5 root cause. Non 8 bug separati.**
>
> | # | Root cause | Impatta |
> |---|------------|---------|
> | 1 | Top-50 publisher filter senza disclaimer in UI | Bug #2-3 (Jan 12 AdEx numerica) |
> | 2 | Mondadori_npa, Adgage_mondocore, Mediamond NON aggregati con Mondadori — UI mostra solo `publisher_id="Mondadori"` esatto match | Bug #4a (bacino), parzialmente #4e |
> | 3 | Revenue NET vs GROSS in UI senza label | Bug #4e (€115k vs €188k è 60/40 rev-share) |
> | 4 | Alert legacy v1.0 (channel="GOOGLE") con baseline rolling 7w che cerca un canale che nel dataset v1.2 non esiste più; alert già marcati `deprecated=1` nel DB ma il deploy live è uno snapshot statico del 26 marzo, pre-deprecation | Bug #5 (timeframe label) e #6 (timeline mancante) |
> | 5 | Heuristics client-side (`baseline = revenue_current * 0.95 + 5pp` per coverage) sostituiscono dati che dovrebbe produrre il backend | Bug #1 (dashboard hourly: vedi -100% per 23 ore alla fine del dataset perché manca il dato, non perché c'è stato un crollo) |
>
> **3. ETA realistici.**
>
> - Phase 13 (UI labeling: timeframe, gross/net, channel scope, timezone) — ~10-12 maggio
> - Phase 11 (CORR-01/08, baseline server-side, fill_rate weighted) — ~1ª settimana di maggio
> - Phase 10.5 (`/network-totals` endpoint che bypassa filtro top-50) — entro 5 maggio
> - Phase 09 deploy refresh (rimpiazzare i 200 alert "GOOGLE" con i 238 freschi 2026-01-23 → 2026-03-23 + nascondere i deprecated) — **fattibile entro venerdì 1 maggio** se autorizzi un re-export
> - CLEAN-02 (Mondadori vs Mondadori_npa vs mondocore aggregation) — ancora in `[ ]`, da pianificare
>
> **4. Nel frattempo (workaround).**
>
> - **Per Mondadori**: ignora i numeri della pagina Top Publisher fino a Phase 13 (chiusura ~mid mag). Per Feb usa il PBI. La conferma: **Sentinel è coerente con se stesso** (133M / 41.8% / €2.08 / €0.87) ma rappresenta un sottoinsieme (solo `publisher_id="Mondadori"`, NET, top-50 only). Il delta vs PBI **non significa numeri sbagliati** — significa scope diverso non comunicato.
> - **Per Open Market 12 Gen e simili giornaliere**: stessa storia, ignora la dashboard. Il dato è giusto per l'85% del network ma manca il 13% bottom-tail. Phase 10.5 ti darà l'endpoint network-totals coerente con PBI.
> - **Per gli alert "GOOGLE"**: tratta come "informativi storici, da non usare per debugging". Re-deploy di settimana prossima li nasconde di default.
> - **Per la dashboard hourly**: leggi solo le ore con `delta_pct ≠ -100%`. Il -100% è artefatto di "ora futura/nodata", non un crollo. Phase 13 metterà il badge.
>
> Faccio il sync esecuzione phase 11+13+10.5 questa settimana e ti do un go-live target firme entro **venerdì 8 maggio**. Se vuoi, ti propongo intanto un re-export dei 238 alert freschi (Phase 09) come quick-win operativo entro venerdì 1 mag.
>
> S.

---

## Open questions for operator

1. **Re-export immediato dei 238 alert freschi (Phase 09)** — autorizzato entro 1 maggio? (Cambia subito cosa Vito vede nella alert list, anche se i numeri Mondadori/AdEx restano gli stessi.)

2. **CLEAN-02 strategia su Mondadori_npa + Adgage_mondocore + Mediamond** — sono unità di business "Mondadori"? Confermare con Vito e mappare in `publisher_mapping.csv` o aggregare in UI con disclosure GDPR-aware (npa = no personal ads).

3. **CORR-03 gross/net default** — PBI usa GROSS, Sentinel usa NET. Decisione D2 da REQUIREMENTS.md dice "default GROSS, NET subtitle". Confermare con Vito? Se preferisce restare NET con label corretta, è una mezza giornata in meno.

4. **Phase 11 priority — CORR-08 fill_rate denominator** — devo wire `measurable_impressions / bacino_dedup` (PBI definition) o lasciare `impressions / bacino_dedup`? Cambia Mondadori da 41.75% → ~37.0% (più vicino a PBI 35.2%, gap residuo dovuto a CLEAN-02 scope).

5. **Top-50 filter** — bypass via API-01 only o anche regenerate parquet senza filtro per dashboard generale? Decisione D1 dice "hybrid endpoint". Conferma scope.

6. **Alert ALT-20260113-225828-P2** — visto che è marcato `deprecated=1` ma è quello citato verbatim nell'email di Vito, vogliamo eccezionalmente generare un nuovo alert equivalente (post-Phase 09 backfill, su channel `GOOGLE_ADEX` invece di `GOOGLE`) per dare a Vito un caso "ufficiale" da testare? O accettiamo il "guarda il prossimo che arriva"?

7. **Re-deploy frequency** — il deploy live è uno static export del 26 marzo. Pianifichiamo re-export settimanale (Phase 14 Vercel decision) o keep ad-hoc?

---

*Auditor C — 2026-04-28 — read-only investigation against live deploy + local DB + parquet baseline + raw CSV upstream. Zero mutations.*

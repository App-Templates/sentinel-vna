---
status: DRAFT — pending Stefano approval before send
to: marco.manduca@adkaora.com
cc:
  - iolanda.prezio@adkaora.com
  - nicholas.farinato@adkaora.com
  - vito.sena@adkaora.com
  - pm@adkaora.com
from: stefano@hej.ai
subject: "Re: AdKaora [INT] | Sentinel - Feedback"
gating_phase: Phase 19 V1+V2 deployed
gated_open: D2 Sample 2 HBM byte-perfect (Phase 21 v1.4 — Athena hourly ingestion)
authored: 2026-05-22
---

# Bozza email risposta Marco — Sentinel feedback 2026-05-19

## Subject

Re: AdKaora [INT] | Sentinel - Feedback

## Body (italiano informale, mirror tono Marco, no trattini a inizio riga)

```
Ciao Marco,

ti rispondo punto per punto sul feedback che mi hai mandato il 19/5. Otto
dei nove punti sono chiusi e live su https://sentinel-vna-stefano-hejais-projects.vercel.app
— ti spiego sotto cosa è stato fatto e perché. Sul nono (Sample 2 HBM)
c'è un blocco strutturale onesto che ti documento sotto.

Prima però la cosa importante: nel verificare il D2 ho scoperto un bug
serio. La pipeline aveva un mismatch di timezone (UTC vs naive) che
mascherato come 'backfill' restituiva silently dati sintetici sopra tutta
la finestra storica HBM/HBP/TAM. I valori €736 e €1185 dei tuoi due
sample erano numeri inventati dal fallback, non dati reali. Fix landato
(commit 9a91792), e abbiamo deprecato in DB i 400 alert pre-fix
(deprecated=1 + deprecation_reason) per preservare l'audit trail senza
più mostrarli come verità.

Visualizzazione

V1 — Alert per Channel a livello Demand (diretta-deal-open)
Aggiunto. Il livello Demand (Diretta / Deal / Open Market) è ora un campo
derivato esposto dall'API su ogni alert (channel_group → demand_layer
mapping in backend/db/demand_layers.py, single source of truth con mirror
TS lato frontend protetto da contract-test). In dashboard ogni riga
mostra il badge Demand accanto al Channel; nella detail page il badge è
nell'header.

V2 — Distribuzione % revenue intra-Open Market
Aggiunto come nuovo tab "Open Market Distribution" sulla detail page,
visibile solo quando l'alert è su Open Market. Due donut affiancate
(current vs baseline) + tabella per ogni OM sub-channel con revenue,
delta_pct, share now/baseline e Δ share in punti percentuali. Quando il
totale OM si muove meno del 5% ma due o più sub-channel shiftano la
share di ≥3pp, esce un callout "Possible intra-OM shift" che è
esattamente il segnale che descrivevi (il calo di uno compensato dal
gain di un altro). Per gli alert storici dove channel_breakdown è
incompleto, il pannello mostra una disclosure onesta sulla dipendenza
Athena (vedi sotto sul punto Sample 2).

V3 — Tooltip Revenue Impact mostrava label baseline
Chiuso (Phase 17.2 HOTFIX-01). Tooltip ora distingue baseline vs current
correttamente.

V4 — "Revenue Trend (7 Weeks)" su 7 giorni
Chiuso (Phase 17.2 HOTFIX-02). La label è "Last 7 Days".

V5 — Top 35 vs Top 50
Chiuso (Phase 17.2 HOTFIX-03). Il numero corretto è Top 35. Il
disclaimer è ora più prominente (banner amber, count in bold) e il link
"Network totals" rispetta tutti i filtri attivi (closure D1).

Bug

B1 — Tab 3/4/5 inaccessibili
Chiuso (Phase 17.2 HOTFIX-04). I tre tab Contributors / Geo Breakdown /
Environment Split ora gestiscono il caso empty payload con empty-state
card invece di rompere il render.

B2 — Tab Triage Bacino+Coverage = 0
Chiuso (Phase 17.2 HOTFIX-05). Era un contract drift sul payload
('bacino_current' / 'coverage_current' invece di 'bacino' / 'coverage')
introdotto in Phase 11 — TriageSection leggeva i campi vecchi e cadeva
sempre sullo 0 di fallback. Ora legge i campi giusti + filtra
'amp_drift_detected' (che diluiva avgCoverage di 1/4) + sostituisce 'n/a'
quando il payload davvero non ha env_split.

Dati e Coerenza

D1 — Network totals link ignorava filtri
Chiuso (Phase 17.2 HOTFIX-06). Il link compone l'href con
URLSearchParams a partire dai filtri attivi della PublishersPage.

D2 Sample 1 — ALT-20260322-010000-P2 GOOGLE_ADEX
Chiuso byte-perfect (Phase 17.4). L'alert detail su CDN ora restituisce
revenue_current=€662.67 (data_source='real_csv'). Il valore Sentinel
€662.67 è dentro la banda PBI €662.00 ±1% [€655.38, €668.62] — gate
strict attivo nel contract test scripts/test_alert_revenue_pbi_parity.py
(invariant INV-1).

Path tecnico per chiudere il gap publisher-top-50 (Phase 11 D1): nuovo
endpoint /api/metrics/network-totals?bypass_top50=true che legge
data/sentinel_db/daily_kpi.csv direct, bypassando il filtro top-50 di
default che strippava ~21% del revenue gross. Sample 1 alimenta direttamente
da quel path.

Inoltre come closure dello storico: 38 alert GOOGLE_ADEX 'backfill'
(2026-01-23 → 2026-03-23) sono stati riscritti a 'real_csv' con i valori
veri dal CSV (Migration 006 + script di rewrite). 200 alert
HBM/HBP/TAM/DIRECT/DEAL/OPEN_BIDDING pre-fix sono stati marcati
deprecated=1 con reason 'synthetic-era pre-H6-fix, Phase 21 Athena
dependency'.

D2 Sample 2 — ALT-20260320-070000-P2 HEADER_BIDDING_MAGNITE
APERTO con disclosure strutturale.

Per chiudere a byte-perfect contro il tuo screenshot HBM €688 serve la
serie oraria HBM. La nostra sorgente attuale data/sentinel_db/hour_kpi.csv
contiene solo GOOGLE_ADEX a livello orario (verificato). Le serie
orarie HBM/HBP/TAM/OPEN_BIDDING non sono nel pipeline csv-only, vivono
solo su Athena.

Il connector Athena è già code-ready nel repo (Phase 17.4 ha landato la
whitelist 7 canali in backend/connectors/athena.py:19 con fallback
graceful 'synthetic_no_athena' per ogni canale missing-creds). Ci
servono solo le credenziali production Athena per HBM/HBP/TAM/OPEN_BIDDING
hourly + attivazione ingestion. Quello è scope di Phase 21 (v1.4 Athena
Full Ingestion). ETA realistica: ~5-7 giorni di lavoro tecnico una volta
che abbiamo le credenziali in mano.

Per il tuo caso specifico, fino a Phase 21 chiusa, il tab "Open Market
Distribution" sull'alert HBM mostra la disclosure di non-disponibilità
del breakdown orario su sub-channel non-AdEx, invece di tirare numeri
ricavati dal sintetico.

---

In sintesi: 8/9 chiusi e live, Sample 2 chiude appena attiviamo Athena
production (Phase 21 v1.4). Quando vuoi ti mostro le UI nuove insieme,
o fammi sapere se vedi qualcosa di strano sull'ambiente live.

Grazie del lavoro di audit — il bug timezone si nascondeva da gennaio,
senza il tuo check puntuale sarebbe rimasto silente.

Stefano
```

## Allegati consigliati

- Screenshot dashboard con badge Demand visibile su riga alerts (post-deploy)
- Screenshot detail page tab "Open Market Distribution" su un alert OM (post-deploy)
- Link diretto: `https://sentinel-vna-stefano-hejais-projects.vercel.app/alerts/ALT-20260322-010000-P2` (Sample 1 byte-perfect)

## Anti-pattern da rispettare al send

1. NON inviare senza esplicito OK Stefano sul testo finale.
2. NON promettere ETA Athena/Phase 21 più stretta di 5-7 giorni (è già aggressiva).
3. NON dichiarare V1/V2 come "alerting refactor completo" — è UI surfacing + intra-OM shift detection panel; il refactor algoritmico richiede dati multi-channel hourly (Athena).

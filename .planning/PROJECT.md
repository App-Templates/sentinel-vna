# SENTINEL — Value Network Alerting Platform

## What This Is

Piattaforma di monitoraggio e alerting per la rete pubblicitaria Adkaora. SENTINEL analizza le revenue orarie dei publisher, rileva anomalie (cali improvvisi, drift graduali, near-zero, data gap), classifica le cause e notifica il team operativo. Destinata al team TAM&Yield (5-10 persone) per il monitoraggio di 50-100 publisher attivi.

## Core Value

**Trovare gli alert in tempo quasi reale comunicando tempestivamente solo ciò che è davvero importante** — eliminando i falsi positivi e rendendo visibili i cali graduali che oggi nessuno nota finché il danno non è fatto.

## Requirements

### Validated

<!-- Funzionalità esistenti e funzionanti nella piattaforma corrente -->

- ✓ Pipeline LangGraph 11 agenti (orchestrator → notifier) — v1.0
- ✓ Alert A1 revenue drop con severity P0/P1/P2 — v1.0
- ✓ Alert A2 drift 7 giorni — v1.0 (da migliorare)
- ✓ Alert A3 near-zero revenue/coverage — v1.0
- ✓ Alert A0 data gap detection — v1.0
- ✓ Triage classification (TRAFFIC/COVERAGE/MIXED/REVENUE_ONLY) — v1.0
- ✓ Contributor analysis per-publisher — v1.0
- ✓ Geo breakdown (ITA/ES/OTHER) — v1.0
- ✓ Environment split (WEB/AMP/APP) — v1.0
- ✓ Insight generation (template-based) — v1.0
- ✓ Dashboard alert list con filtri — v1.0
- ✓ Alert detail 7-step view — v1.0
- ✓ Top 35 publisher per revenue con country — v1.0
- ✓ Publisher weekly KPI charts con annotazioni stagionali — v1.0
- ✓ eCPM optimization windows — v1.0
- ✓ Backtest storico — v1.0
- ✓ Health page — v1.0
- ✓ Admin page datasource config — v1.0
- ✓ Google OAuth (dominio @adkaora.com) — v1.0
- ✓ Rate limiting API — v1.0
- ✓ Deduplicazione alert LIVE mode — v1.0.1
- ✓ Graph singleton (compile-once) — v1.0.1
- ✓ Real data fetcher (parquet, non sintetico) — v1.0.1

### Active

<!-- Requisiti v1.1 — da costruire -->

**Alerting Evoluto:**
- [ ] Drift detection avanzato per cali graduali (2%/giorno, regressione lineare su 14-30gg)
- [ ] Alert su margine % sotto soglia configurabile
- [ ] Alert coverage=zero con triage dedicato (policy Google/MCM/ads.txt)
- [ ] Alert correlato coverage↓ + CPM↑↑ (pricing rule errata)
- [ ] Confronto revenue vs giorno precedente (stesse ore) con soglia 30%
- [ ] Confronto revenue vs media 14 giorni
- [ ] Alert attivi weekend/festivi (scheduling ridotto)
- [ ] Calibrazione soglie (30% operativo vs 5-15% attenzione)

**Operator Workflow:**
- [ ] Feedback su alert (conferma/falso positivo/commento/assegna)
- [ ] Categorie falso positivo predefinite
- [ ] Tracking interventi manuali (form rapido < 1 min)
- [ ] Collegamento alert ↔ intervento manuale
- [ ] Storico feedback per publisher/pattern

**Notifiche:**
- [ ] Slack canale dedicato
- [ ] Template configurabile per severity
- [ ] P0 = immediata, P1/P2 = riepilogo giornaliero

**Dati e Multi-canale:**
- [ ] Connessione Athena (refresh orario)
- [ ] Multi-canale (diretta, HB&TAM, preferred deal, deal guaranteed)
- [ ] Granularità per formato (interstitial, display)
- [ ] Monitoraggio CTR/Viewability AdEx come leading indicator

**Intelligence:**
- [ ] Soglie dinamiche per stagionalità storica
- [ ] Auto-suggerimento "possibile falso positivo"
- [ ] Suggerimenti d'azione basati su pattern storici
- [ ] Publisher tiering (top 20 + onboarding con monitoring intensivo)

### Out of Scope

- Esecuzione diretta azioni su GAM dalla piattaforma — troppo rischioso per v1.1, serve validazione umana
- Integrazione GAM change history via API — complessità alta, form manuale sufficiente per ora
- Benchmark competitor/mercato — dati non disponibili
- App mobile — dashboard web responsive sufficiente
- Dati traffico page views/sessioni — dipendenza da Analytics, da valutare in v1.2
- Adattamento soglie automatico per publisher basato su feedback ML — v1.2, serve massa critica di feedback prima

## Context

**Team:** TAM&Yield guidato da Vito Sena (Head). 5-10 operatori tra account manager e yield specialists.

**Workflow attuale:** Check manuale ogni 3-4 ore durante il giorno, 2x/giorno weekend. Confronto visivo su GAM tra revenue orarie vs ieri e vs media 14gg. Diagnosi manuale per formato, company, environment.

**Pain point principale:** I cali graduali (es. 2%/giorno) non vengono notati finché il danno cumulativo non è significativo. Nessuno controlla trend multi-giorno sistematicamente.

**Interventi manuali:** Quotidiani su pricing rules, floor CPM, demand partners. Tracciati su GAM (change history) ma non usati proattivamente. Il team è disposto a loggarli su SENTINEL se il form è rapido (< 1 min) e solo per interventi significativi.

**Falsi positivi:** Campagne dirette publisher (sottraggono traffico all'Open Market), interventi pianificati, stagionalità, problemi tecnici noti. Generano rumore negli alert.

**KPI prioritari:** 1. RPM, 2. Coverage, 3. eCPM, 4. CTR

**Dati Athena:** Parzialmente pronti (tabelle esistono, schema da verificare). Dati aggiuntivi richiesti: fill rate, viewability, CTR, floor CPM storici.

**Publisher critici:** Top 20 per revenue + nuovi in onboarding (prime settimane di collaborazione richiedono monitoring intensivo).

## Constraints

- **Infrastruttura:** SQLite single-writer (accettabile per 5-10 utenti), Athena schema da verificare
- **Team:** 5-10 utenti, nessun accesso differenziato richiesto (tutti vedono tutto)
- **Dati:** Parquet come fallback, Athena come source primaria (quando pronto)
- **Operativo:** Form interventi < 1 minuto, notifiche solo per ciò che è importante
- **Budget:** Nessun vincolo esplicito, LLM optional (fallback statistico sempre attivo)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Drift detection con regressione lineare 14-30gg | 2%/giorno non rilevato da A2 attuale (7gg, -8%) | — Pending |
| Form interventi manuali (non integrazione GAM API) | GAM API complessa, form < 1min accettato dal team | — Pending |
| Soglie doppie (30% operativo + 5-15% attenzione) | Allineare con pratica ops senza perdere granularità | — Pending |
| Slack come canale primario notifiche | Team già su Slack, canale dedicato da creare | — Pending |
| RPM come KPI primario (non solo revenue) | Il team ragiona in RPM, non revenue assoluta | — Pending |
| CTR/Viewability come leading indicator | Quando calano su AdEx, revenue Open Market cala dopo | — Pending |

---
*Last updated: 2026-02-19 after stakeholder questionnaire analysis*

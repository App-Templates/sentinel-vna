# Requirements: SENTINEL v1.1

**Defined:** 2026-02-19
**Core Value:** Trovare gli alert in tempo quasi reale comunicando solo ciò che è davvero importante — rendendo visibili i cali graduali che oggi nessuno nota.

## v1 Requirements

### Drift & Gradual Decline

- [ ] **DRIFT-01**: Il sistema rileva cali graduali di revenue (es. 2%/giorno) usando regressione lineare su finestra 14-30 giorni e genera alert quando il trend cumulativo supera soglia configurabile
- [ ] **DRIFT-02**: Il sistema confronta revenue orarie vs stesse ore del giorno precedente e genera alert con soglia 30% (allineata con pratica operativa)
- [ ] **DRIFT-03**: Il sistema confronta revenue vs media ultimi 14 giorni e genera alert quando le curve divergono significativamente

### Alert Nuovi Tipi

- [x] **ALRT-01**: Il sistema genera alert quando il margine % scende sotto soglia configurabile per publisher/gruppo
- [x] **ALRT-02**: Il sistema rileva coverage=zero e classifica con triage dedicato (policy Google, MCM, ads.txt)
- [x] **ALRT-03**: Il sistema rileva correlazione coverage↓ + CPM↑↑ come indicatore di pricing rule errata
- [ ] **ALRT-04**: Il sistema esegue alerting attivo anche nel weekend e festivi con scheduling ridotto (2x/giorno)
- [ ] **ALRT-05**: Il sistema supporta soglie doppie: alert operativo (30% deviazione) e alert di attenzione (5-15% deviazione)

### Operator Feedback

- [ ] **FEED-01**: L'operatore può confermare un alert come reale o segnalarlo come falso positivo scegliendo tra categorie predefinite (intervento manuale, stagionalità, tecnico, campagna publisher, rumore mercato)
- [ ] **FEED-02**: L'operatore può aggiungere un commento testuale con contesto a qualsiasi alert
- [ ] **FEED-03**: L'operatore può assegnare un alert a un collega del team
- [ ] **FEED-04**: Il sistema mostra lo storico dei feedback sullo stesso publisher/pattern quando si visualizza un alert

### Interventi Manuali

- [ ] **INTV-01**: L'operatore può registrare un intervento manuale tramite form rapido (< 1 minuto): data, publisher, tipo intervento, valore prima/dopo, motivo
- [ ] **INTV-02**: L'operatore può collegare un alert a un intervento manuale registrato
- [ ] **INTV-03**: Il sistema esclude/annota automaticamente i periodi con interventi manuali nella baseline degli alert

### Notifiche

- [ ] **NOTF-01**: Il sistema invia notifiche su canale Slack dedicato SENTINEL
- [ ] **NOTF-02**: Il livello di dettaglio della notifica è configurabile per severity (P0=report completo con contributors e azioni, P2=una riga con link alla dashboard)
- [ ] **NOTF-03**: Alert P0 genera notifica Slack immediata; P1/P2 vengono raggruppati in riepilogo giornaliero

### Dati e Connettività

- [ ] **DATA-01**: Il sistema si connette ad Athena con refresh orario dei dati
- [ ] **DATA-02**: Il sistema monitora revenue per tutti i canali: Open Market, diretta, HB&TAM, preferred deal, deal guaranteed
- [ ] **DATA-03**: Il sistema monitora CTR e Viewability AdEx come leading indicator (calo CTR/View → calo revenue Open Market nelle ore successive)

## v2 Requirements

### Intelligence (v1.2)

- **INTL-01**: Soglie dinamiche che si adattano automaticamente alla stagionalità storica
- **INTL-02**: Auto-suggerimento "possibile falso positivo" basato su feedback passati simili
- **INTL-03**: Suggerimenti d'azione basati su pattern storici (es. "in periodi simili, alzare floor del 10% ha funzionato")
- **INTL-04**: Monitoraggio intensificato per publisher in fase di onboarding (prime settimane)
- **INTL-05**: Publisher tiering automatico (top 20 con soglie più strette)

### Granularità (v1.2)

- **GRAN-01**: Analisi per formato (interstitial, display, video)
- **GRAN-02**: Dati fill rate per ad-unit
- **GRAN-03**: Floor CPM storici per correlazione con revenue

## Out of Scope

| Feature | Reason |
|---------|--------|
| Esecuzione azioni su GAM dalla piattaforma | Troppo rischioso senza validazione umana, premature per v1.1 |
| Integrazione GAM change history API | Complessità alta, form manuale < 1 min accettato dal team |
| Benchmark competitor/mercato | Dati non disponibili |
| App mobile nativa | Dashboard web responsive sufficiente per 5-10 utenti |
| ML per adattamento soglie automatico | Serve massa critica di feedback prima (v1.2+) |
| Dati traffico (page views/sessioni) | Dipendenza da Analytics, non prioritario per alerting |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DRIFT-01 | Phase 1 | Pending |
| DRIFT-02 | Phase 1 | Pending |
| DRIFT-03 | Phase 1 | Pending |
| ALRT-01 | Phase 2 | Complete |
| ALRT-02 | Phase 2 | Complete |
| ALRT-03 | Phase 2 | Complete |
| ALRT-04 | Phase 1 | Pending |
| ALRT-05 | Phase 1 | Pending |
| FEED-01 | Phase 3 | Pending |
| FEED-02 | Phase 3 | Pending |
| FEED-03 | Phase 3 | Pending |
| FEED-04 | Phase 3 | Pending |
| INTV-01 | Phase 3 | Pending |
| INTV-02 | Phase 3 | Pending |
| INTV-03 | Phase 3 | Pending |
| NOTF-01 | Phase 4 | Pending |
| NOTF-02 | Phase 4 | Pending |
| NOTF-03 | Phase 4 | Pending |
| DATA-01 | Phase 5 | Pending |
| DATA-02 | Phase 5 | Pending |
| DATA-03 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 21 total
- Mapped to phases: 21
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-19*
*Last updated: 2026-02-19 after stakeholder analysis*

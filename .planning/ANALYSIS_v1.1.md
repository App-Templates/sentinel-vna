# SENTINEL v1.1 — Analisi Stakeholder e Piano d'Azione

**Data:** 2026-02-19
**Fonti:** Questionario Stakeholder (Vito Sena, Head of TAM&YIELD) + Procedura Check Revenue Orari
**Obiettivo:** Sintetizzare le risultanze e definire un piano d'azione per l'evoluzione della piattaforma

---

## 1. Risultanze Chiave dal Questionario

### 1.1 Profilo Operativo
- **Compilato da:** Vito Sena, Head of TAM&YIELD
- **Team:** TAM + Yield, 5-10 persone
- **Utilizzo:** Prima mattina (check notturno) + quando arrivano notifiche
- **Publisher attivi:** 50-100, segmentati per revenue/geo/verticale/traffico
- **Publisher critici:** Nuovi onboarding (prime settimane) + Top 20 per revenue

### 1.2 Interventi Manuali — Stato Attuale
**Scoperta fondamentale:** Gli interventi SONO tracciati su GAM (change history, pricing rule history) ma NON vengono gestiti proattivamente. Vengono usati solo retroattivamente per ricostruire cause di problemi.

- Frequenza: **quotidiana**
- Esecutori: Team TAM + Team Yield (più operatori)
- Tipi: floor CPM, pricing rules, demand partners, Open Bidding rules, A/B test su pricing rules
- Disponibilità a loggarli su SENTINEL: **sì, se rapido e solo per interventi significativi**
- Info minime: data + publisher + tipo + valore prima/dopo + motivo

**Implicazione per SENTINEL:** Non serve ricostruire tutto il tracking da zero — si può integrare con la change history di GAM via API, oppure creare un form minimale per interventi significativi.

### 1.3 Feedback Operatore — Tutti i Canali Aperti
Vito ha selezionato TUTTE le opzioni:
- Confermare alert come reale
- Segnalare falso positivo con motivo
- Aggiungere commento con contesto
- Assegnare alert a collega
- Collegare alert a intervento manuale

**Falsi positivi comuni:** TUTTI i tipi (intervento pianificato, stagionalità, problemi tecnici noti, variazioni publisher, rumore di mercato) + **campagne publisher** (es. "Ford in questi giorni, non vi passiamo traffico").

**Feedback nel tempo:** Vito vuole TUTTO — storico, auto-suggerimenti, adattamento soglie. Ma anche "tutti gli operatori del team" devono poter dare feedback.

### 1.4 Data Quality
- Soglie: **automatiche basate su stagionalità storica** (non fisse)
- Dati: "puliti a monte in base alle esigenze" — non è un problema di data quality grezza
- Evento esterno critico: **campagne dirette dei publisher** che sottraggono traffico all'Open Market

### 1.5 Notifiche
- **Canale Slack dedicato** (da creare)
- Dettaglio: **configurabile per severity** (P0 = completo, P2 = minimo)
- Urgenza: **P0 = immediata, P1/P2 = riepilogo giornaliero**
- Nessun accesso differenziato necessario (tutti vedono tutto)

### 1.6 Dati Live e Athena
- Frequenza ideale: **oraria**
- Athena: **parzialmente pronto** (tabelle esistono, schema da verificare)
- Dati aggiuntivi richiesti: fill rate, viewability, traffico, floor CPM storici, benchmark competitor

### 1.7 Business Rules e KPI
**KPI per priorità:**
1. **RPM** (priorità #1)
2. **Coverage** (priorità #2)
3. **eCPM** (priorità #3)
4. **CTR** (menzionato come "Altro")

**Regole floor CPM — quando si interviene:**
- CPM netto editore sotto il concordato
- Margine troppo basso
- Mesi poveri (gennaio, agosto) → si abbassano le rule
- Mesi ricchi (novembre, dicembre) → si alzano le rule
- Ottimizzazione RPM opportunistica

**SENTINEL dovrebbe:** suggerire azioni basate su pattern storici (non solo segnalare!)

### 1.8 Pain Points e Desideri
- **Frustrazione #1:** Cali graduali di revenue difficili da individuare
- **Frustrazione #2:** Nessun alert nel weekend/festivi
- **Frustrazione #3:** Nessun alert sui margini (quando margine % scende sotto soglia)
- **Desiderio:** Alert quasi real-time che comunicano SOLO ciò che è davvero importante

---

## 2. Risultanze dalla Procedura Operativa

### 2.1 Workflow Attuale (Manuale)
La procedura descrive il check che Vito/team fanno **ogni 3-4 ore** durante la giornata lavorativa e **2 volte al giorno** nel weekend (da cellulare).

Questo è esattamente ciò che SENTINEL deve automatizzare.

### 2.2 Step 1 — Check Revenue Orario
**Cosa fanno:**
- Monitorano revenue orarie **Open Market**
- Confrontano con **stesse ore del giorno precedente**
- Alert se deviazione **>30%**
- Verificano anche: **diretta, HB&TAM, preferred deal, deal guaranteed**
- Motivo: un CPM errato (65€ invece di 6.5€) fa schizzare le dirette e sottrae Open Market

**Viste necessarie:**
1. Revenue tutti i canali vs ieri (confronto orario)
2. Revenue tutti i canali vs media ultimi 14 giorni (curve devono somigliarsi)

**Scope:** Per formato (interstitial, display), company, environment (web, AMP, webview)

### 2.3 Step 2 — Diagnosi Cause

**Caso A: Calo Ad Request**
- 90% dei casi: errori nei codici (adk-init mancante)
- Azione: verifica in pagina presenza adk-init, check console errori

**Caso B: Calo Coverage (Ad Request OK)**

| Scenario | Sintomo | Causa | Azione |
|----------|---------|-------|--------|
| B.1 Coverage = Zero | Coverage azzerata | Policy Google, MCM, ads.txt | Escalation immediata |
| B.2 Coverage ↓ + CPM ↑↑ | Coverage giù, AdEx CPM schizza (2€→5€) | Pricing rule troppo alta su network | Controllare pricing rules + display CPM |
| B.3 Coverage ↓ + KPI bassi | Coverage giù, CPM normali | CTR o Viewability in calo | Monitorare AdEx CTR/Viewability |

**Nota critica su AdEx:** Si valutano SOLO CTR e Viewability di AdEx (60-70% delle revenue). HB&TAM non sono tracciabili in GAM (KPI = 0) e alterano i dati complessivi.

---

## 3. Gap Analysis: SENTINEL Attuale vs Realtà Operativa

### 3.1 Gap Critici (la piattaforma non fa queste cose)

| # | Gap | Impatto | Complessità |
|---|-----|---------|-------------|
| G1 | **Solo 2 canali (GOOGLE, OPEN_BIDDING)** — ops monitora anche diretta, HB&TAM, preferred, guaranteed | Non rileva quando un CPM errato sulle dirette sottrae Open Market | Alta |
| G2 | **Nessun alert su margine** | Il team non sa quando il margine % scende sotto soglia concordata | Media |
| G3 | **Confronto solo 7-week baseline** — ops usa ieri + media 14gg | Il confronto attuale è troppo "smooth", non cattura anomalie vs ieri | Media |
| G4 | **Nessun monitoraggio CTR/Viewability** | Leading indicator: se CTR/View scendono, Open Market cala nelle ore successive | Media |
| G5 | **Nessuna granularità per formato** (interstitial vs display) | Un CPM alto su display può bloccarla completamente, non visibile a livello aggregato | Alta |
| G6 | **Nessun handling coverage=zero** | Caso critico (policy Google, MCM, ads.txt) non ha triage dedicato | Bassa |
| G7 | **Nessuna correlazione coverage↓ + CPM↑** | Pattern classico di pricing rule errata, non rilevato | Media |
| G8 | **Nessun alert weekend/festivi** | 2x/giorno manuale dal cellulare — SENTINEL potrebbe automatizzare | Bassa |

### 3.2 Gap Importanti (miglioramenti necessari)

| # | Gap | Impatto | Complessità |
|---|-----|---------|-------------|
| G9 | **Nessun tracking interventi manuali** | Non si distingue variazione reale da rumore di intervento | Media |
| G10 | **Nessun feedback loop operatore** | Il sistema non impara dai falsi positivi | Media |
| G11 | **Soglie fisse** — ops vuole soglie automatiche per stagionalità | Troppe alert in periodi bassi, poche in periodi alti | Alta |
| G12 | **Nessun suggerimento d'azione** | Ops deve interpretare ogni alert da zero | Alta |
| G13 | **Nessuna notifica Slack** | Operatori devono check manuale della dashboard | Bassa |
| G14 | **30% threshold ops vs 5-15% SENTINEL** | Disallineamento soglie con pratica reale | Config |
| G15 | **No monitoraggio publisher in onboarding** | Prime settimane richiedono attenzione speciale | Media |

### 3.3 Gap Dati

| # | Gap | Fonte Dati | Disponibilità |
|---|-----|-----------|---------------|
| D1 | Fill rate per ad-unit | Athena/GAM | Da verificare |
| D2 | Viewability AdEx | Athena/GAM | Da verificare |
| D3 | CTR AdEx | Athena/GAM | Da verificare |
| D4 | Floor CPM storici | GAM pricing rules | Da verificare |
| D5 | Revenue per canale (diretta, HB, TAM, PD, DG) | Athena | Da verificare schema |
| D6 | Revenue per formato (interstitial, display) | Athena | Da verificare schema |
| D7 | Dati traffico (page views, sessioni) | Analytics/Athena | Da verificare |

---

## 4. Requisiti Emersi per v1.1

### 4.1 Must-Have (senza questi SENTINEL non risolve i problemi reali)

**Alerting Core:**
- **ALERT-01:** Alert su revenue Open Market vs giorno precedente (stesse ore) con soglia 30%
- **ALERT-02:** Alert su revenue vs media 14 giorni (curve devono somigliarsi)
- **ALERT-03:** Alert su margine quando margine % scende sotto soglia configurabile
- **ALERT-04:** Alert coverage=zero con triage dedicato (policy/MCM/ads.txt)
- **ALERT-05:** Alert correlato coverage↓ + CPM↑↑ (pricing rule errata)
- **ALERT-06:** Alert weekend/festivi (scheduling ridotto ma attivo)
- **ALERT-07:** Cali graduali di revenue (drift detection migliorato)

**Operator Workflow:**
- **FLOW-01:** Feedback su alert: conferma/falso positivo/commento/assegna
- **FLOW-02:** Categorie falso positivo predefinite (intervento manuale, stagionalità, tecnico, campagna publisher, rumore)
- **FLOW-03:** Storico feedback per publisher/pattern
- **FLOW-04:** Tracking interventi manuali (form rapido: data, publisher, tipo, prima/dopo, motivo)
- **FLOW-05:** Collegamento alert ↔ intervento manuale

**Notifiche:**
- **NOTIF-01:** Canale Slack dedicato SENTINEL
- **NOTIF-02:** Dettaglio configurabile per severity (P0=completo, P2=minimo)
- **NOTIF-03:** P0 = notifica immediata, P1/P2 = riepilogo giornaliero

### 4.2 Should-Have (migliorano significativamente la piattaforma)

**Dati e Analisi:**
- **DATA-01:** Connessione Athena con refresh orario
- **DATA-02:** Multi-canale: diretta, HB&TAM, preferred deal, deal guaranteed (oltre a Open Market)
- **DATA-03:** Granularità per formato (interstitial, display)
- **DATA-04:** Monitoraggio CTR e Viewability AdEx come leading indicator
- **DATA-05:** Publisher tiering (top 20 con soglie più strette)

**Intelligence:**
- **INTEL-01:** Soglie dinamiche basate su stagionalità storica
- **INTEL-02:** Auto-suggerimento "possibile falso positivo" basato su feedback passati
- **INTEL-03:** Suggerimenti d'azione basati su pattern storici
- **INTEL-04:** Monitoraggio intensificato per publisher in onboarding

### 4.3 Nice-to-Have (v1.2+)

- Adattamento soglie automatico per publisher basato su feedback cumulativo
- Integrazione diretta con GAM change history per tracking interventi
- Benchmark competitor/mercato
- Esecuzione azioni dalla piattaforma (modifica pricing rules)
- Dati traffico (page views, sessioni)

---

## 5. Piano d'Azione Proposto

### Fase 1: Foundation Fix (1-2 settimane)
**Obiettivo:** Rendere SENTINEL affidabile per uso quotidiano

- [x] ~~Fix data_fetcher sintetico → reale~~ (FATTO)
- [x] ~~Fix graph compilation singleton~~ (FATTO)
- [x] ~~Fix deduplicazione alert~~ (FATTO)
- [ ] Alert weekend/festivi (scheduling attivo, frequenza ridotta)
- [ ] Soglia 30% per alert iniziale (allineare con pratica ops)
- [ ] Confronto vs giorno precedente (non solo 7-week baseline)

### Fase 2: Operator Workflow (2-3 settimane)
**Obiettivo:** Gli operatori possono interagire con gli alert

- [ ] Feedback su alert (conferma, falso positivo con categoria, commento)
- [ ] Tracking interventi manuali (form rapido)
- [ ] Collegamento alert ↔ intervento
- [ ] Storico feedback per publisher

### Fase 3: Notifiche e Comunicazione (1 settimana)
**Obiettivo:** Alert arrivano dove servono

- [ ] Integrazione Slack reale (canale dedicato)
- [ ] Template notifica configurabile per severity
- [ ] Riepilogo giornaliero P1/P2
- [ ] Notifica immediata P0

### Fase 4: Nuovi Alert e Diagnosi (2-3 settimane)
**Obiettivo:** Coprire i casi operativi reali

- [ ] Alert margine (quando margine % scende sotto soglia)
- [ ] Alert coverage=zero con triage dedicato
- [ ] Alert correlato coverage↓ + CPM↑ (pricing rule errata)
- [ ] Confronto vs media 14 giorni
- [ ] Cali graduali migliorati (drift)

### Fase 5: Dati Live e Multi-canale (3-4 settimane)
**Obiettivo:** Dati reali, multi-canale, granulari

- [ ] Connessione Athena (verifica schema, credenziali)
- [ ] Multi-canale (diretta, HB&TAM, preferred, guaranteed)
- [ ] Granularità per formato
- [ ] CTR e Viewability come leading indicator

### Fase 6: Intelligence (2-3 settimane)
**Obiettivo:** SENTINEL diventa proattivo

- [ ] Soglie dinamiche per stagionalità
- [ ] Auto-suggerimento falso positivo
- [ ] Suggerimenti d'azione basati su pattern
- [ ] Publisher tiering (top 20 + onboarding)

---

## 6. Osservazioni Strategiche

### 6.1 Il Disallineamento delle Soglie
SENTINEL attuale usa P0=-15%, P1=-10%, P2=-5%. La pratica operativa usa **30%** come prima soglia. Questo va calibrato: la soglia del 30% è per il check rapido "tutto ok?", mentre le soglie più basse di SENTINEL servono per il monitoraggio continuo. Probabilmente servono DUE livelli: alert operativo (30%) e alert di attenzione (5-15%).

### 6.2 Il Vero Competitor non è un Tool, è Excel+GAM
Il team oggi fa tutto manualmente con GAM + check visivi. SENTINEL deve essere MENO faticoso di questo workflow, non di più. Il form degli interventi deve essere < 1 minuto. Le notifiche devono essere precise (zero rumore). Se SENTINEL genera troppi falsi positivi, il team tornerà al check manuale.

### 6.3 RPM come KPI Primario
Il team pensa in termini di RPM (revenue per mille page views), non solo revenue assoluta. Questo cambia la logica degli alert: un calo di revenue con page views stabili è diverso da un calo di revenue con calo di traffico. SENTINEL deve distinguere.

### 6.4 Il Ruolo delle Campagne Dirette
Un tema emerso forte: le campagne dirette dei publisher possono "rubare" traffico all'Open Market. Questo genera falsi alert su Open Market quando in realtà è un comportamento atteso. SENTINEL deve poter tracciare/annotare questi periodi.

### 6.5 Leading Indicator: CTR e Viewability
Scoperta operativa importante: quando CTR e Viewability AdEx calano, le revenue Open Market calano nelle ore successive. Questo è un leading indicator che SENTINEL potrebbe usare per alert PREDITTIVI, non solo reattivi.

### 6.6 La Sezione 9 (Priorità) Non è Stata Compilata
La sezione 9 era contrassegnata "Stefano Argiolas" — le priorità di sviluppo vanno definite internamente, non dallo stakeholder ops. Questo ha senso: Vito dice COSA serve, Stefano decide IN CHE ORDINE.

---

*Analisi completata: 2026-02-19*
*Prossimo step: Creare PROJECT.md, REQUIREMENTS.md e ROADMAP.md basati su questa analisi*

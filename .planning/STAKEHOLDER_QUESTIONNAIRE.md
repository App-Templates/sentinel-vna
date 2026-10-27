# SENTINEL — Questionario Stakeholder

**Obiettivo:** Raccogliere le informazioni necessarie per definire i requisiti della v1.1 della piattaforma di alerting SENTINEL. Le risposte guideranno le priorità di sviluppo.

**Come compilare:** Per ogni domanda, seleziona l'opzione più vicina oppure scrivi una risposta libera. Se non sei sicuro, scrivi "da definire". Se la domanda non ti riguarda, scrivi "N/A".

**Compilato da:** ____________________
**Ruolo:** ____________________
**Data:** ____________________

---

## 1. Interventi Manuali e Tracking

Oggi gli operatori fanno interventi sulle properties (floor CPM, ottimizzazione RPM, modifiche ad-unit, ecc.) che impattano i dati di revenue. SENTINEL ha bisogno di sapere QUANDO avvengono questi interventi per distinguere variazioni reali da rumore.

### 1.1 Come vengono tracciati oggi gli interventi manuali?
- [ ] Non vengono tracciati da nessuna parte
- [ ] Fogli Excel/Google Sheets (non collegati alla piattaforma)
- [ ] Annotazioni su GAM/piattaforma di ad serving
- [ ] Altro: ____________________

### 1.2 Chi esegue gli interventi manuali sulle properties?
- [ ] Un solo operatore dedicato
- [ ] Più operatori (quanti? _____)
- [ ] Team esterno / publisher stessi
- [ ] Misto: ____________________

### 1.3 Che tipo di interventi vengono fatti? (seleziona tutti quelli applicabili)
- [ ] Modifica floor CPM
- [ ] Ottimizzazione RPM per publisher
- [ ] Cambio configurazione ad-unit
- [ ] Attivazione/disattivazione partner di demand
- [ ] Modifica regole di Open Bidding
- [ ] A/B test su layout/posizionamenti
- [ ] Altro: ____________________

### 1.4 Con che frequenza avvengono questi interventi?
- [ ] Quotidianamente
- [ ] Alcune volte a settimana
- [ ] Settimanalmente
- [ ] Solo quando necessario (ad-hoc)
- [ ] Altro: ____________________

### 1.5 Sareste disposti a registrare gli interventi su SENTINEL?
Immaginate un form semplice: data, publisher, tipo di intervento, note.
- [ ] Sì, se è rapido (< 1 minuto per intervento)
- [ ] Sì, ma solo per interventi significativi
- [ ] Difficile — troppo overhead operativo
- [ ] Altro: ____________________

### 1.6 Quali informazioni minime servono per ogni intervento?
- [ ] Data + publisher + tipo intervento è sufficiente
- [ ] Serve anche il valore "prima" e "dopo" (es. floor da 0.50 a 0.80)
- [ ] Servono anche le note sul motivo dell'intervento
- [ ] Altro: ____________________

---

## 2. Feedback Operatore sugli Alert

SENTINEL deve imparare dagli operatori: capire quali alert sono utili, quali sono falsi positivi, e come gestire situazioni specifiche.

### 2.1 Quando un operatore vede un alert, cosa dovrebbe poter fare?
(seleziona tutti quelli applicabili)
- [ ] Confermare l'alert come reale ("sì, c'è un problema")
- [ ] Segnalare come falso positivo con motivo
- [ ] Aggiungere un commento con contesto ("è successo perché...")
- [ ] Assegnare l'alert a un collega
- [ ] Collegare l'alert a un intervento manuale precedente
- [ ] Altro: ____________________

### 2.2 Quali categorie di "falso positivo" sono comuni?
(seleziona tutti quelli applicabili)
- [ ] Intervento manuale pianificato (floor change, A/B test)
- [ ] Stagionalità nota (festività, back-to-school, Black Friday)
- [ ] Problema tecnico temporaneo già noto (GAM outage, CDN issue)
- [ ] Publisher ha comunicato variazione prevista
- [ ] Variazione fisiologica (rumore normale del mercato)
- [ ] Altro: ____________________

### 2.3 Come dovrebbe il sistema utilizzare il feedback nel tempo?
- [ ] Mostrare storico dei feedback sullo stesso publisher/pattern
- [ ] Suggerire automaticamente "questo potrebbe essere un falso positivo" basandosi su feedback passati
- [ ] Adattare le soglie per publisher specifici basandosi sui feedback
- [ ] Solo storico, nessuna automazione (troppo rischioso)
- [ ] Altro: ____________________

### 2.4 Chi dovrebbe poter dare feedback sugli alert?
- [ ] Tutti gli operatori del team
- [ ] Solo operatori senior / responsabili
- [ ] Chiunque, ma con livelli diversi (operatore vs. admin)
- [ ] Altro: ____________________

---

## 3. Data Quality e Rumore

I dati contengono rumore che può generare alert non significativi. Dobbiamo capire quali sono le fonti di rumore note.

### 3.1 Quali eventi esterni impattano i dati ma non sono "problemi reali"?
(seleziona tutti quelli applicabili)
- [ ] Festività e periodi speciali (Natale, Pasqua, Ferragosto, ecc.)
- [ ] Campagne pubblicitarie specifiche (inizio/fine)
- [ ] Periodi di budget trimestrale (inizio/fine trimestre)
- [ ] Weekend vs. feriali (pattern diversi)
- [ ] Traffico bot/invalido
- [ ] Problemi lato publisher (sito down, redesign)
- [ ] Altro: ____________________

### 3.2 Ci sono publisher con comportamenti particolari che generano falsi alert?
(rispondi liberamente)

____________________
____________________
____________________

### 3.3 Ci sono periodi dell'anno in cui le soglie di alert dovrebbero essere diverse?
- [ ] Sì — periodi specifici: ____________________
- [ ] Sì — le soglie dovrebbero essere automatiche (basate su stagionalità storica)
- [ ] No — soglie fisse vanno bene
- [ ] Non so, da valutare

### 3.4 Come gestite oggi i "dati sporchi"?
- [ ] Li ignoriamo e lavoriamo con quello che c'è
- [ ] Puliamo manualmente caso per caso
- [ ] Abbiamo regole di esclusione (quali? _____)
- [ ] Altro: ____________________

---

## 4. Publisher e Segmentazione

### 4.1 Quanti publisher gestite attivamente?
- [ ] Meno di 20
- [ ] 20-50
- [ ] 50-100
- [ ] Più di 100

### 4.2 I publisher hanno tutti le stesse regole di alerting o servono soglie personalizzate?
- [ ] Stesse regole per tutti
- [ ] 2-3 gruppi con regole diverse (es. top tier, mid tier, long tail)
- [ ] Ogni publisher è diverso e serve personalizzazione individuale
- [ ] Altro: ____________________

### 4.3 Come sono segmentati i publisher oggi?
(seleziona tutti quelli applicabili)
- [ ] Per revenue (top, medium, small)
- [ ] Per paese/geo (Italia, Spagna, LATAM, altro)
- [ ] Per verticale/settore (news, sport, entertainment, ecc.)
- [ ] Per tipo di traffico (web, AMP, app)
- [ ] Non sono segmentati formalmente
- [ ] Altro: ____________________

### 4.4 Ci sono publisher "critici" che richiedono attenzione speciale?
(rispondi liberamente — es. publisher che generano più revenue, più problematici, ecc.)

____________________
____________________
____________________

---

## 5. Utenti e Ruoli

### 5.1 Chi userà SENTINEL quotidianamente?
(seleziona tutti quelli applicabili)
- [ ] Account manager (gestione publisher)
- [ ] Operatori yield/ad-ops (ottimizzazione)
- [ ] Team tecnico (monitoring infrastruttura)
- [ ] Management (overview KPI)
- [ ] Altro: ____________________

### 5.2 Quante persone useranno la piattaforma?
- [ ] 1-5 persone
- [ ] 5-10 persone
- [ ] 10-20 persone
- [ ] Più di 20

### 5.3 Servono livelli di accesso diversi?
- [ ] No — tutti vedono tutto
- [ ] Sì — operatori vedono solo i loro publisher
- [ ] Sì — admin può modificare regole, operatori solo leggono e danno feedback
- [ ] Sì — configurazione: ____________________

### 5.4 In quale momento della giornata la piattaforma viene consultata maggiormente?
- [ ] Prima mattina (check notturno)
- [ ] Durante tutto l'orario lavorativo
- [ ] Fine giornata (riepilogo)
- [ ] Solo quando arriva una notifica
- [ ] Altro: ____________________

---

## 6. Notifiche e Comunicazione

### 6.1 Dove volete ricevere le notifiche degli alert?
(seleziona tutti quelli applicabili)
- [ ] Canale Slack dedicato
- [ ] DM Slack alla persona responsabile del publisher
- [ ] Email
- [ ] Solo sulla dashboard (nessuna notifica push)
- [ ] Altro: ____________________

### 6.2 Che livello di dettaglio nelle notifiche?
- [ ] Minimo: "Alert P0 su publisher X — revenue -18%" con link alla dashboard
- [ ] Medio: alert + triage + top contributor + azione suggerita
- [ ] Completo: report completo nella notifica stessa
- [ ] Configurabile per severity (P0 = completo, P2 = minimo)

### 6.3 Quali alert giustificano una notifica immediata vs. un riepilogo?
- [ ] P0 = immediata, P1/P2 = riepilogo giornaliero
- [ ] Tutti immediati
- [ ] Solo P0 immediata, il resto solo dashboard
- [ ] Configurabile per operatore/publisher
- [ ] Altro: ____________________

### 6.4 Esiste già un canale Slack dedicato al team ad-ops?
- [ ] Sì — nome canale: ____________________
- [ ] No — va creato
- [ ] Usiamo altro (Teams, Telegram, ecc.): ____________________

---

## 7. Dati Live e Athena

### 7.1 Qual è la frequenza ideale di aggiornamento dati?
- [ ] Real-time (< 5 minuti)
- [ ] Oraria
- [ ] Ogni 2-3 ore (allineata con i cicli di alert)
- [ ] Giornaliera è sufficiente per ora
- [ ] Altro: ____________________

### 7.2 I dati su Athena sono già disponibili e pronti?
- [ ] Sì — tabelle pronte, credenziali disponibili
- [ ] Parzialmente — tabelle esistono ma schema da verificare
- [ ] No — serve setup infrastrutturale
- [ ] Non so / da verificare con il team tecnico

### 7.3 Quali dati aggiuntivi sarebbero utili rispetto a quelli attuali?
(seleziona tutti quelli applicabili)
- [ ] Dati di fill rate per ad-unit
- [ ] Dati di viewability
- [ ] Dati di traffico (page views, sessioni)
- [ ] Dati floor CPM storici (per correlare con revenue)
- [ ] Dati competitor/benchmark di mercato
- [ ] Altro: ____________________

---

## 8. Ottimizzazione e Business Rules

### 8.1 Esistono regole di ottimizzazione standard o ogni publisher è un caso a sé?
- [ ] Regole standard che valgono per tutti
- [ ] Regole di base con eccezioni per publisher specifici
- [ ] Ogni publisher ha la sua strategia
- [ ] Altro: ____________________

### 8.2 Come viene deciso quando intervenire su un floor CPM?
(rispondi liberamente)

____________________
____________________
____________________

### 8.3 SENTINEL dovrebbe suggerire azioni di ottimizzazione o solo segnalare anomalie?
- [ ] Solo segnalare — le decisioni le prendiamo noi
- [ ] Suggerire azioni basate su pattern storici (es. "in periodi simili, aumentare il floor del 10% ha funzionato")
- [ ] Suggerire E permettere di eseguire azioni dalla piattaforma
- [ ] Altro: ____________________

### 8.4 Quali KPI sono più importanti per valutare la salute di un publisher?
Ordina per priorità (1 = più importante):
- [ ] Revenue totale — priorità: ___
- [ ] eCPM — priorità: ___
- [ ] RPM — priorità: ___
- [ ] Fill rate — priorità: ___
- [ ] Bacino (ad requests) — priorità: ___
- [ ] Coverage — priorità: ___
- [ ] Viewability — priorità: ___
- [ ] Altro: ____________________

---

## 9. Priorità di Sviluppo

### 9.1 Ordina queste aree per urgenza (1 = più urgente):
- [ ] Fix bug critici (data fetcher, deduplicazione alert) — priorità: ___
- [ ] Tracking interventi manuali — priorità: ___
- [ ] Feedback operatore sugli alert — priorità: ___
- [ ] Notifiche Slack/email — priorità: ___
- [ ] Connessione Athena (dati live) — priorità: ___
- [ ] Test automatici — priorità: ___
- [ ] Soglie personalizzate per publisher — priorità: ___
- [ ] Suggerimenti di ottimizzazione — priorità: ___

### 9.2 C'è una deadline o milestone specifica?
- [ ] No — evoluzione continua
- [ ] Sì — data target: ____________________
- [ ] Sì — evento/milestone: ____________________

### 9.3 Ci sono vincoli tecnici o organizzativi da considerare?
(rispondi liberamente — es. accesso AWS limitato, team piccolo, budget, ecc.)

____________________
____________________
____________________

---

## 10. Domande Aperte

### 10.1 Cosa ti frustra di più nel workflow attuale (senza SENTINEL)?

____________________
____________________
____________________

### 10.2 Se SENTINEL potesse fare UNA cosa perfettamente, quale sarebbe?

____________________
____________________
____________________

### 10.3 C'è qualcosa che non ho chiesto ma che ritieni importante?

____________________
____________________
____________________

---

*Questionario generato il 2026-02-18*
*Progetto: SENTINEL — Value Network Alerting Platform*
*Ritornare compilato a: [inserire contatto]*

---
source: PDF allegato sessione 2026-05-20
sender: Marco Manduca <marco.manduca@adkaora.com>
recipient: Stefano Argiolas <stefano@hej.ai>
cc:
  - Iolanda Prezio <iolanda.prezio@adkaora.com>
  - Nicholas Farinato <nicholas.farinato@adkaora.com>
  - Vito Sena <vito.sena@adkaora.com>
  - Team - PM <pm@adkaora.com>
date: 2026-05-19T17:59:00+02:00
subject: AdKaora [INT] | Sentinel - Feedback
canonical: true
purpose: truth source per Phase 17.2 (UI hotfix) + Phase 17.3 (revenue calc audit)
---

# Email Marco — Sentinel Feedback 2026-05-19

## Testo verbatim

> Ciao Stefano,
>
> come promesso, ti riporto anche qui i feedback che abbiamo sulla nuova versione di Sentinel (puoi trovarli anche sul solito file condiviso):
>
> **Visualizzazione:**
>
> - Alert > Alert per Channel --> potrebbe aver senso solo a livello di Demand (diretta-deal-open). All'interno dell'open ci può essere uno shift di revnue tra Channel (oggi Equative compra su AdEx, domani tramite Demand Manager) quindi il calo di una può essere compensato da altro. Questi shift sono frequenti ciò significa numero alert elevati e falsi alert
> - Alert > Alert per Channel --> seguendo la logica del punto precedente sarebbe meglio studiare la distribuzione % della revenue nel caso di problemi su Open Market
> - Alert > Tab 1. Revenue Impact facendo mouseover sul grafico, mostra sempre la label baseline al posto di current revenue
> - Alert: Sempre sul grafico, c'è scritto Revenue Trend (7 Weeks), ma vengono mostrati solamente gli ultimi 7 giorni
> - Top Publishers: nel disclaimer in testa alla pagina scrivi Top 35 publisher, nella precedente mail facevi riferimento alla Top 50. Quale dei due è corretto?
>
> **Bug:**
>
> - Alert > Non è più possibile accedere ai tab 3. Top Contributors, 4. Geo Breakdown, 5. Environment Split.
> - Alert > Tab 2. Triage Classification mostra sempre Bacino (Impressions) e Coverage a 0 su tutti gli alert.
>
> **Dati e Coerenza:**
>
> - Top Publisher > il link Network totals riporta sempre agli stessi dati (giorno 23/03/2026, Google — direi l'ultimo dato disponibile sulla base dato, a prescindere da eventuali filtri che vengono applicati) e le revenue non mi tornano.
> - Alerts > abbiamo provato a fare un check puntuale su alcuni alert e vedere se i dati fossero coerenti con i nostri. Ti lascio di seguito un paio di esempio con relativi ss.
>
>   1. **ALT-20260322-010000-P2**
>      Se ho compreso bene, l'alert sarebbe dovuto arrivare il 22 Marzo alle 02:00 sui dati dello stesso giorno alle ore 01:00. Nel caso specifico, Sentinel segnala un totale di €736 Current Revenue (gross), ma a me risultano €1.166 alle 00:00 e €662 alle 01:00 (come da ss in allegato)
>
>      | timestamp | channel_group | revenue_gross |
>      |-----------|---------------|---------------|
>      | 2026-03-22 00:00:00.000 | GOOGLE_ADEX | 1166.216532 |
>      | 2026-03-22 01:00:00.000 | GOOGLE_ADEX | 662.6686729999999 |
>      | 2026-03-22 02:00:00.000 | GOOGLE_ADEX | 440.7493519999999 |
>      | 2026-03-22 03:00:00.000 | GOOGLE_ADEX | 350.601728 |
>      | 2026-03-22 04:00:00.000 | GOOGLE_ADEX | 368.1737260000001 |
>      | 2026-03-22 05:00:00.000 | GOOGLE_ADEX | 454.0776219999999 |
>      | 2026-03-22 06:00:00.000 | GOOGLE_ADEX | 938.3802559999999 |
>      | 2026-03-22 07:00:00.000 | GOOGLE_ADEX | 1917.4076909999999 |
>      | 2026-03-22 08:00:00.000 | GOOGLE_ADEX | 2511.876044 |
>      | 2026-03-22 09:00:00.000 | GOOGLE_ADEX | 2484.6488780000004 |
>
>   2. **ALT-20260320-070000-P2**
>      In questo caso, l'alert è arrivato il 20 Marzo alle 08:00 sui dati delle ore 07:00. Sentinel segnala €1.185 Current Revenue (gross), ma a me risultano €688 alle 07:00 e €495 alle 06:00 (come da ss in allegato)
>
>      | timestamp | channel_group | revenue_gross |
>      |-----------|---------------|---------------|
>      | 2026-03-20 00:00:00.000 | HEADER_BIDDING_MAGNITE | 221.49809999999997 |
>      | 2026-03-20 01:00:00.000 | HEADER_BIDDING_MAGNITE | 137.8615 |
>      | 2026-03-20 02:00:00.000 | HEADER_BIDDING_MAGNITE | 111.34759999999997 |
>      | 2026-03-20 03:00:00.000 | HEADER_BIDDING_MAGNITE | 100.67920000000001 |
>      | 2026-03-20 04:00:00.000 | HEADER_BIDDING_MAGNITE | 119.90369999999997 |
>      | 2026-03-20 05:00:00.000 | HEADER_BIDDING_MAGNITE | 236.81500000000005 |
>      | 2026-03-20 06:00:00.000 | HEADER_BIDDING_MAGNITE | 495.67909999999995 |
>      | 2026-03-20 07:00:00.000 | HEADER_BIDDING_MAGNITE | 688.7145 |
>      | 2026-03-20 08:00:00.000 | HEADER_BIDDING_MAGNITE | 707.1276 |
>      | 2026-03-20 09:00:00.000 | HEADER_BIDDING_MAGNITE | 719.5611999999998 |
>      | 2026-03-20 10:00:00.000 | HEADER_BIDDING_MAGNITE | 642.0332000000001 |
>      | 2026-03-20 11:00:00.000 | HEADER_BIDDING_MAGNITE | 571.1683999999999 |
>      | 2026-03-20 12:00:00.000 | HEADER_BIDDING_MAGNITE | 610.4526999999999 |
>
> Ne approfitto per augurarti una buona giornata,
> Marco

## Mappa feedback → Phase

| ID | Feedback | Tipo | Destinazione |
|---|---|---|---|
| V1 | Alert per Channel a livello Demand | Refactor | Backlog v1.4 |
| V2 | Studio distribuzione % revenue Open Market | Feature | Backlog v1.4 |
| V3 | Tooltip Revenue Impact mostra "baseline" | Bug UI | Phase 17.2 |
| V4 | "Revenue Trend (7 Weeks)" → 7 giorni | Bug label | Phase 17.2 |
| V5 | Top 35 vs Top 50 disclaimer | Q + UX | Phase 17.2 (disclaimer prominence; valore Top 35 confermato) |
| B1 | Tab 3/4/5 inaccessibili | Bug | Phase 17.2 |
| B2 | Tab 2 Triage Bacino+Coverage = 0 | Bug | Phase 17.2 |
| D1 | Network totals link ignora filtri | Bug | Phase 17.2 |
| D2 | 2 alert revenue gross discrepant | Bug calc | Phase 17.3 (audit dedicato) |

## Note operative

- L'email arriva DOPO l'integrazione del publisher mapping (mail Marco 2026-05-18, Phase 17.1 SHIPPED 2026-05-20). Nessun feedback di questa mail tocca il mapping.
- D2 non è una semplice off-by-one: i sample mostrano che Sentinel restituisce valori NON corrispondenti a nessuna singola riga oraria. Possibili ipotesi:
  - Aggregazione su finestra multi-ora (es. 4-5 ore dall'inizio della giornata UTC)
  - Channel filter applicato in modo diverso (multi-channel sum vs single-channel)
  - Reference timestamp wrap (UTC vs Europe/Rome) che sposta i bucket orari
- Marco ha promesso ulteriori feedback via "file condiviso" (probabilmente Google Sheet con Iolanda).

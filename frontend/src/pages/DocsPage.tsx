import { useState } from 'react'
import {
  ChevronDown, ChevronRight, AlertTriangle, TrendingDown, Activity,
  Layers, Globe, Monitor, Users, Cpu, HelpCircle, Database,
  Network, Shield, Settings, Clock, FolderTree, Code, Container,
  BarChart3, Eye, Zap, ShieldAlert, BookOpen, Target,
} from 'lucide-react'
import { cn } from '../lib/utils'

// ---------------------------------------------------------------------------
// Shared Components
// ---------------------------------------------------------------------------

function Section({
  id, icon: Icon, title, children, open, onToggle,
}: {
  id: string; icon: React.ElementType; title: string; children: React.ReactNode; open: boolean; onToggle: (id: string) => void
}) {
  return (
    <div className="border-b border-gray-200 last:border-b-0">
      <button onClick={() => onToggle(id)} className="flex w-full items-center gap-3 px-4 py-4 text-left transition-colors hover:bg-gray-50">
        <Icon size={20} className="shrink-0 text-blue-600" />
        <span className="flex-1 text-base font-semibold text-gray-900">{title}</span>
        {open ? <ChevronDown size={18} className="text-gray-400" /> : <ChevronRight size={18} className="text-gray-400" />}
      </button>
      {open && <div className="px-4 pb-6 pt-0 pl-11 text-sm leading-relaxed text-gray-700">{children}</div>}
    </div>
  )
}

function Th({ children }: { children: React.ReactNode }) {
  return <th className="border border-gray-200 bg-gray-50 px-3 py-2 text-left text-xs font-semibold uppercase text-gray-600">{children}</th>
}

function Td({ children, className, ...rest }: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return <td className={cn('border border-gray-200 px-3 py-2 text-sm', className)} {...rest}>{children}</td>
}

function Badge({ color, children }: { color: 'red' | 'orange' | 'yellow' | 'blue' | 'green' | 'gray' | 'purple'; children: React.ReactNode }) {
  const colors = {
    red: 'bg-red-100 text-red-800', orange: 'bg-orange-100 text-orange-800',
    yellow: 'bg-yellow-100 text-yellow-800', blue: 'bg-blue-100 text-blue-800',
    green: 'bg-green-100 text-green-800', gray: 'bg-gray-100 text-gray-700',
    purple: 'bg-purple-100 text-purple-800',
  }
  return <span className={cn('inline-block rounded-full px-2 py-0.5 text-xs font-medium', colors[color])}>{children}</span>
}

function CodeBlock({ children }: { children: string }) {
  return <pre className="my-3 overflow-x-auto rounded-lg bg-gray-900 p-4 text-xs leading-relaxed text-gray-200">{children}</pre>
}

// ---------------------------------------------------------------------------
// Operational Tab
// ---------------------------------------------------------------------------

const OP_SECTIONS = ['alert-rules', 'severity', 'triage', 'metrics', 'pipeline', 'contributors', 'geo', 'env', 'multi-metric', 'opt-windows', 'ecpm-patterns', 'hidden-patterns', 'danger-zones', 'driver-guide', 'faq']

function OperationalDocs({ openSections, toggle }: { openSections: Set<string>; toggle: (id: string) => void }) {
  return (
    <>
      {/* ALERT RULES */}
      <Section id="alert-rules" icon={AlertTriangle} title="Regole di Alert (A0, A1, A2, A3)" open={openSections.has('alert-rules')} onToggle={toggle}>
        <p className="mb-4">
          Sentinel monitora i ricavi della rete pubblicitaria Adkaora confrontando le metriche correnti con una
          <strong> baseline storica</strong> (stessa ora, stesso giorno della settimana, media delle <strong>7 settimane</strong> precedenti).
          Quando rileva un'anomalia, genera un alert secondo una di quattro regole:
        </p>
        <table className="mb-4 w-full border-collapse">
          <thead><tr><Th>Regola</Th><Th>Nome</Th><Th>Cosa rileva</Th><Th>Quando scatta</Th></tr></thead>
          <tbody>
            <tr>
              <Td><Badge color="red">A1</Badge></Td><Td className="font-medium">Revenue Drop</Td>
              <Td>Calo improvviso dei ricavi rispetto alla baseline oraria/giornaliera</Td>
              <Td>Quando il delta % ricavi supera le soglie P0/P1/P2. Z-score check + soppressione off-peak (22-06).</Td>
            </tr>
            <tr>
              <Td><Badge color="orange">A2</Badge></Td><Td className="font-medium">7-Day Drift</Td>
              <Td>Trend negativo graduale su 7 giorni consecutivi</Td>
              <Td>Media mobile a 7 giorni scesa di <strong>&ge; 8%</strong>. Rileva erosioni lente.</Td>
            </tr>
            <tr>
              <Td><Badge color="yellow">A3</Badge></Td><Td className="font-medium">Near-Zero</Td>
              <Td>Ricavi o coverage vicini a zero</Td>
              <Td>Revenue &lt; <strong>100 EUR</strong> o coverage &lt; <strong>5%</strong> per <strong>3 periodi</strong> consecutivi.</Td>
            </tr>
            <tr>
              <Td><Badge color="purple">A0</Badge></Td><Td className="font-medium">Data Gap</Td>
              <Td>Dati mancanti oltre la soglia configurata</Td>
              <Td>Gap &gt; <strong>4 ore</strong> senza dati. Alert tecnico immediato, bypassa triage e analisi.</Td>
            </tr>
          </tbody>
        </table>
        <div className="rounded-lg bg-blue-50 p-3">
          <p className="text-sm text-blue-800">
            <strong>Perche' quattro regole?</strong> A0 cattura i problemi tecnici (dati mancanti). A1 cattura i cali improvvisi. A2 le erosioni lente (-2%/giorno = -14%/settimana). A3 le morti silenziose (publisher che smettono di generare revenue).
          </p>
        </div>
      </Section>

      {/* SEVERITY */}
      <Section id="severity" icon={TrendingDown} title="Livelli di Severity (P0, P1, P2)" open={openSections.has('severity')} onToggle={toggle}>
        <p className="mb-4">La severity determina priorita' e tempi di risposta. Assegnata dall'Anomaly Detector in base al delta % e al contesto temporale.</p>
        <table className="mb-4 w-full border-collapse">
          <thead><tr><Th>Severity</Th><Th>Soglia</Th><Th>Finestra</Th><Th>Significato</Th><Th>Azione</Th></tr></thead>
          <tbody>
            <tr><Td><Badge color="red">P0</Badge></Td><Td className="font-mono">&ge; -15%</Td><Td>2h consecutive</Td><Td>Calo grave, impatto significativo sui ricavi giornalieri</Td><Td>Investigare entro 30 min</Td></tr>
            <tr><Td><Badge color="orange">P1</Badge></Td><Td className="font-mono">&ge; -10%</Td><Td>2h consecutive</Td><Td>Calo importante, impatto rilevante se persiste</Td><Td>Investigare entro 2 ore</Td></tr>
            <tr><Td><Badge color="yellow">P2</Badge></Td><Td className="font-mono">&ge; -5%</Td><Td>4h consecutive</Td><Td>Calo moderato, possibilmente fisiologico</Td><Td>Monitorare, investigare se persiste</Td></tr>
          </tbody>
        </table>
        <div className="space-y-2">
          <p><strong>Aggiustamenti contestuali:</strong></p>
          <ul className="list-disc space-y-1 pl-5">
            <li><strong>Off-peak (22-06):</strong> soglie rilassate 1.5x. Un -15% notturno diventa P1.</li>
            <li><strong>Weekend:</strong> soglie rilassate 1.2x.</li>
            <li><strong>Z-score &lt; 1.5 + off-peak:</strong> alert soppresso (probabile falso positivo).</li>
          </ul>
        </div>
      </Section>

      {/* TRIAGE */}
      <Section id="triage" icon={Activity} title="Classificazione Triage" open={openSections.has('triage')} onToggle={toggle}>
        <p className="mb-4">Il triage classifica la <strong>causa primaria</strong> confrontando variazioni di bacino e coverage.</p>
        <table className="mb-4 w-full border-collapse">
          <thead><tr><Th>Classificazione</Th><Th>Condizione</Th><Th>Significato</Th><Th>Dove investigare</Th></tr></thead>
          <tbody>
            <tr><Td><Badge color="blue">TRAFFIC_DRIVEN</Badge></Td><Td className="font-mono">bacino &le; -10%<br/>coverage &gt; -10%</Td><Td>Traffico calato, fill rate stabile</Td><Td>Publisher, sorgenti traffico, tag</Td></tr>
            <tr><Td><Badge color="green">COVERAGE_DRIVEN</Badge></Td><Td className="font-mono">coverage &le; -10%<br/>bacino &gt; -10%</Td><Td>Traffico stabile, meno impressioni monetizzate</Td><Td>Demand partner, floor price, bid</Td></tr>
            <tr><Td><Badge color="orange">MIXED</Badge></Td><Td className="font-mono">entrambi &le; -10%</Td><Td>Calo sia traffico che copertura</Td><Td>Piattaforma, ad server, mercato</Td></tr>
            <tr><Td><Badge color="gray">REVENUE_ONLY</Badge></Td><Td className="font-mono">entrambi &gt; -10%</Td><Td>Revenue cala senza driver visibili</Td><Td>CPM, eCPM, mix inventory, demand</Td></tr>
          </tbody>
        </table>
        <div className="rounded-lg bg-blue-50 p-3">
          <p className="text-sm text-blue-800"><strong>Soglia -10%:</strong> sotto il 10% il segnale e' indistinguibile dal rumore. Simmetrica per evitare bias.</p>
        </div>
      </Section>

      {/* METRICS */}
      <Section id="metrics" icon={Layers} title="Metriche chiave: Bacino, Coverage, eCPM" open={openSections.has('metrics')} onToggle={toggle}>
        <div className="space-y-4">
          <div>
            <h4 className="font-semibold text-gray-900">Bacino (Ad Requests)</h4>
            <p>Impressioni disponibili. Se cala: meno pagine viste o tag non caricati. <code className="rounded bg-gray-100 px-1 text-xs">SUM(ad_requests)</code></p>
          </div>
          <div>
            <h4 className="font-semibold text-gray-900">Coverage (Fill Rate)</h4>
            <p>% di ad requests con annuncio servito. <code className="rounded bg-gray-100 px-1 text-xs">impressions_filled / ad_requests</code>. Se cala: demand in difficolta'.</p>
          </div>
          <div>
            <h4 className="font-semibold text-gray-900">eCPM</h4>
            <p>Ricavo medio per 1000 impressioni. <code className="rounded bg-gray-100 px-1 text-xs">(revenue / impressions) * 1000</code>. Indicatore di qualita' monetizzazione.</p>
          </div>
          <div>
            <h4 className="font-semibold text-gray-900">Revenue</h4>
            <p>Prodotto: <code className="rounded bg-gray-100 px-1 text-xs">revenue = bacino x coverage x eCPM / 1000</code>. Ecco perche' il triage decompone nelle componenti.</p>
          </div>
        </div>
      </Section>

      {/* PIPELINE */}
      <Section id="pipeline" icon={Cpu} title="Pipeline di Analisi (11 Agenti)" open={openSections.has('pipeline')} onToggle={toggle}>
        <p className="mb-4">Pipeline di 11 agenti specializzati che analizzano l'anomalia da diverse angolazioni:</p>
        <div className="space-y-3">
          {[
            { n: 1, name: 'Orchestrator', d: 'Prepara contesto: canale, timestamp, trigger type.' },
            { n: 2, name: 'Data Fetcher', d: 'Recupera dati (Athena → GAM → Parquet fallback chain), calcola baseline 7 settimane e delta. Cache con TTL.' },
            { n: 3, name: 'Data Validator', d: 'Verifica qualita\' dati: completezza, coerenza, outlier. Se dati mancanti > 4h, genera alert A0.' },
            { n: 4, name: 'Anomaly Detector', d: 'Applica regole A1/A2/A3 con check ore consecutive, Z-scores (sample std N-1), assegna severity. A0 bypassa questo step. Optional: Claude Haiku.' },
            { n: 5, name: 'Triage Classifier', d: 'Classifica causa: TRAFFIC/COVERAGE/MIXED/REVENUE_ONLY.' },
            { n: '6a', name: 'Contributor Analyzer', d: 'Top publisher per quota di calo. Optional: Claude Haiku per normalizzazione nomi.' },
            { n: '6b', name: 'Geo Analyzer', d: 'Scompone per geo cluster (ITA/ES/OTHER).' },
            { n: '6c', name: 'Environment Splitter', d: 'Scompone per WEB/AMP/APP. Rileva AMP drift.' },
            { n: 7, name: 'Insight Generator', d: 'Correla risultati, genera findings ordinati. Optional: Claude Sonnet.' },
            { n: 8, name: 'Report Builder', d: 'Compone report strutturato finale.' },
            { n: 9, name: 'Notifier', d: 'Slack/email asincroni via ThreadPoolExecutor (solo LIVE, non backtest). Retry con exponential backoff.' },
          ].map((a) => (
            <div key={a.n} className="flex gap-3">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700">{a.n}</div>
              <div><span className="font-semibold text-gray-900">{a.name}</span><span className="text-gray-400"> — </span>{a.d}</div>
            </div>
          ))}
        </div>
        <div className="mt-4 rounded-lg bg-gray-50 p-3 text-xs text-gray-600">
          6a/6b/6c girano in parallelo (state keys diverse, nessuna dipendenza). Riduce latenza pipeline. Nota: alert A0 (data gap) bypassano triage e analisi, saltano direttamente a report_builder.
        </div>
      </Section>

      {/* CONTRIBUTORS */}
      <Section id="contributors" icon={Users} title="Analisi Contributors" open={openSections.has('contributors')} onToggle={toggle}>
        <div className="space-y-3">
          <div><h4 className="font-semibold text-gray-900">Quota of Drop</h4><p><code className="rounded bg-gray-100 px-1 text-xs">(delta_publisher / delta_totale) x 100</code>. Calo -10K EUR, publisher -3K = quota 30%.</p></div>
          <div><h4 className="font-semibold text-gray-900">Filtri</h4><p>Max <strong>15 publisher</strong>, quota minima <strong>1%</strong>.</p></div>
          <div><h4 className="font-semibold text-gray-900">Concentrazione</h4><p>Top 3 &gt; 60%: problema <strong>concentrato</strong> (intervento mirato). Distribuito: <strong>sistemico</strong>.</p></div>
        </div>
      </Section>

      {/* GEO */}
      <Section id="geo" icon={Globe} title="Analisi Geografica" open={openSections.has('geo')} onToggle={toggle}>
        <table className="mb-4 w-full border-collapse">
          <thead><tr><Th>Cluster</Th><Th>Paesi</Th><Th>Note</Th></tr></thead>
          <tbody>
            <tr><Td><Badge color="green">ITA</Badge></Td><Td>Italia</Td><Td>Mercato principale</Td></tr>
            <tr><Td><Badge color="orange">ES</Badge></Td><Td>Spagna</Td><Td>Secondo mercato (Vocento, Prensa Iberica...)</Td></tr>
            <tr><Td><Badge color="blue">OTHER</Badge></Td><Td>BR, MX, AR, PT, CO, CL, PE, US, UK, FR, DE</Td><Td>LATAM + resto mondo</Td></tr>
          </tbody>
        </table>
        <p>Status: <Badge color="red">declining</Badge> (&le; -5%), <Badge color="gray">stable</Badge> (-5% / +2%), <Badge color="green">growing</Badge> (&ge; +2%).</p>
      </Section>

      {/* ENVIRONMENT */}
      <Section id="env" icon={Monitor} title="Analisi per Ambiente (WEB, AMP, APP)" open={openSections.has('env')} onToggle={toggle}>
        <table className="mb-4 w-full border-collapse">
          <thead><tr><Th>Ambiente</Th><Th>Descrizione</Th></tr></thead>
          <tbody>
            <tr><Td className="font-medium">WEB</Td><Td>Desktop + mobile standard. Volume piu' alto.</Td></tr>
            <tr><Td className="font-medium">AMP</Td><Td>Accelerated Mobile Pages. In declino (deprecation). Sorvegliato speciale.</Td></tr>
            <tr><Td className="font-medium">APP</Td><Td>In-app (SDK mobile). Stagionalita' diversa.</Td></tr>
          </tbody>
        </table>
        <p><strong>AMP Drift:</strong> rilevato quando AMP cala &ge; -8% e almeno 5pp peggio di WEB o APP.</p>
      </Section>

      {/* MULTI-METRIC INTELLIGENCE */}
      <Section id="multi-metric" icon={BarChart3} title="Intelligenza Multi-Metrica per Publisher" open={openSections.has('multi-metric')} onToggle={toggle}>
        <p className="mb-4">
          La pagina dettaglio publisher integra <strong>4 livelli di analisi</strong> che vanno oltre il semplice eCPM
          per fornire un quadro completo della salute di un editore.
        </p>
        <div className="space-y-3">
          <div className="flex gap-3">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700">1</div>
            <div><span className="font-semibold text-gray-900">Finestre di Ottimizzazione eCPM</span> — Periodi stagionali con eCPM sopra o sotto la media. Badge RAISE/LOWER + driver causale.</div>
          </div>
          <div className="flex gap-3">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700">2</div>
            <div><span className="font-semibold text-gray-900">Pattern Storici eCPM</span> — Pattern ricorrenti che si verificano nello stesso periodo in entrambi gli anni (2024 e 2025).</div>
          </div>
          <div className="flex gap-3">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700">3</div>
            <div><span className="font-semibold text-gray-900">Pattern di Volume Nascosti</span> — Variazioni di revenue/impressions che l'eCPM non cattura perche' le componenti calano proporzionalmente.</div>
          </div>
          <div className="flex gap-3">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700">4</div>
            <div><span className="font-semibold text-gray-900">Zone di Rischio</span> — Periodi in cui eCPM e coverage calano insieme, indicando vera debolezza della domanda.</div>
          </div>
        </div>
        <div className="mt-4 rounded-lg bg-blue-50 p-3">
          <p className="text-sm text-blue-800">
            <strong>Perche' 4 livelli?</strong> L'eCPM da solo puo' essere fuorviante: puo' salire mentre la revenue scende
            (compressione supply), o restare piatto mentre il publisher perde migliaia di euro (pattern nascosti).
            L'analisi multi-metrica rivela cosa succede davvero.
          </p>
        </div>
      </Section>

      {/* OPTIMIZATION WINDOWS */}
      <Section id="opt-windows" icon={Target} title="Finestre di Ottimizzazione eCPM" open={openSections.has('opt-windows')} onToggle={toggle}>
        <p className="mb-4">
          Le finestre di ottimizzazione identificano <strong>periodi stagionali</strong> (Pasqua, Estate, Black Friday, Natale, ecc.)
          in cui l'eCPM si discosta significativamente dalla media annuale del publisher.
        </p>

        <h4 className="mb-2 font-semibold text-gray-900">Come leggerle</h4>
        <div className="space-y-3 mb-4">
          <div>
            <p><Badge color="green">RAISE</Badge> — L'eCPM e' <strong>sopra</strong> la media nel periodo. Opportunita' di ottimizzazione floor price.</p>
          </div>
          <div>
            <p><Badge color="orange">LOWER</Badge> — L'eCPM e' <strong>sotto</strong> la media nel periodo. Valutare riduzione floor per mantenere fill rate.</p>
          </div>
          <div>
            <p><strong>Driver badge:</strong> indica la <strong>causa</strong> della variazione (vedi sezione Guida ai Driver). Attenzione ai badge arancioni con triangolo: segnale potenzialmente fuorviante.</p>
          </div>
        </div>

        <h4 className="mb-2 font-semibold text-gray-900">% Match (Affidabilita')</h4>
        <p className="mb-4">
          Misura quanto il pattern e' <strong>affidabile e preciso</strong> per prendere decisioni operative.
          Non e' un confronto anno su anno, ma un punteggio composito basato su: coerenza interna dei dati settimanali (35%),
          ricorrenza cross-anno (30%), similarita' della magnitudine (20%), ampiezza del campione (15%).
          Piu' alto = pattern piu' affidabile per prendere decisioni.
        </p>

        <h4 className="mb-2 font-semibold text-gray-900">Metriche aggiuntive</h4>
        <p className="mb-2">Sotto ogni finestra di ottimizzazione trovi:</p>
        <ul className="list-disc space-y-1 pl-5">
          <li><strong>Bacino:</strong> variazione % delle ad requests rispetto alla media</li>
          <li><strong>Coverage:</strong> variazione % del fill rate</li>
          <li><strong>Impressions:</strong> variazione % delle impressioni servite</li>
          <li><strong>Revenue:</strong> variazione % dei ricavi</li>
        </ul>
        <div className="mt-4 rounded-lg bg-amber-50 p-3">
          <p className="text-sm text-amber-800">
            <strong>Consiglio:</strong> guarda sempre il driver insieme alla direzione. Un eCPM in salita con driver
            "Compressione Supply" (arancione) NON e' una buona notizia — significa che l'inventory si sta contraendo.
          </p>
        </div>
      </Section>

      {/* ECPM PATTERNS */}
      <Section id="ecpm-patterns" icon={Activity} title="Pattern Storici eCPM" open={openSections.has('ecpm-patterns')} onToggle={toggle}>
        <p className="mb-4">
          I pattern storici identificano variazioni di eCPM <strong>ricorrenti</strong> che si verificano nello
          <strong> stesso periodo</strong> in entrambi gli anni analizzati (2024 e 2025).
        </p>

        <h4 className="mb-2 font-semibold text-gray-900">Come leggerli</h4>
        <ul className="list-disc space-y-2 pl-5 mb-4">
          <li><strong>Confronto diretto:</strong> eCPM 2024 vs eCPM 2025 nello stesso periodo. Mostra se il pattern si ripete e con quale intensita'.</li>
          <li><strong>% Match (Affidabilita'):</strong> quanto il pattern e' affidabile. Calcolato come correlazione di Pearson dei delta% settimanali — misura la coerenza e ripetibilita' del segnale.</li>
          <li><strong>Driver:</strong> classifica la causa sottostante della variazione.</li>
        </ul>

        <h4 className="mb-2 font-semibold text-gray-900">Quando agire</h4>
        <div className="space-y-2">
          <p>I pattern piu' <strong>affidabili</strong> per prendere decisioni sono quelli che combinano:</p>
          <ul className="list-disc space-y-1 pl-5">
            <li><strong>Alta % match</strong> (il pattern e' affidabile e si ripete fedelmente)</li>
            <li><strong>Driver "Domanda"</strong> (verde) — indica vera domanda pubblicitaria, non artefatti statistici</li>
          </ul>
          <p className="mt-2">Pattern con bassa % match o driver arancione richiedono cautela: il segnale potrebbe non ripetersi.</p>
        </div>
      </Section>

      {/* HIDDEN PATTERNS */}
      <Section id="hidden-patterns" icon={Eye} title="Pattern di Volume Nascosti" open={openSections.has('hidden-patterns')} onToggle={toggle}>
        <p className="mb-4">
          I pattern di volume nascosti rilevano variazioni di <strong>revenue e impressions</strong> che l'eCPM
          <strong> non e' in grado di catturare</strong>.
        </p>

        <h4 className="mb-2 font-semibold text-gray-900">Perche' esistono</h4>
        <p className="mb-4">
          L'eCPM e' un rapporto: <code className="rounded bg-gray-100 px-1 text-xs">revenue / impressions * 1000</code>.
          Quando revenue e impressions calano <strong>proporzionalmente</strong> (es. entrambe -20%), l'eCPM resta piatto.
          Il publisher sta perdendo soldi, ma guardando solo l'eCPM non lo vedresti.
        </p>

        <h4 className="mb-2 font-semibold text-gray-900">Come leggerli</h4>
        <ul className="list-disc space-y-2 pl-5 mb-4">
          <li><strong>"eCPM nel periodo":</strong> mostra cosa fa l'eCPM durante il pattern. Se dice <Badge color="gray">PIATTO</Badge>, il pattern e' davvero nascosto — l'eCPM non lo rileva.</li>
          <li><strong>"Impatto":</strong> il valore in <strong>EUR/settimana</strong> quantifica l'effetto economico reale del pattern.</li>
          <li><strong>% Match (Affidabilita'):</strong> ogni pattern mostra una % match che indica l'affidabilita' del segnale, basata su: coerenza direzionale tra i due anni (40%), similarita' della magnitudine (30%), ampiezza del campione (15%), e grado di mascheramento eCPM (15%).</li>
        </ul>

        <div className="rounded-lg bg-amber-50 p-3">
          <p className="text-sm text-amber-800">
            <strong>Esempio pratico:</strong> Un publisher con eCPM stabile a 2.50 EUR ma revenue che cala da 5.000 a 3.000 EUR/settimana.
            L'eCPM non si muove perche' le impressioni calano in proporzione. Il pattern nascosto lo rileva e quantifica
            l'impatto: -2.000 EUR/settimana.
          </p>
        </div>
      </Section>

      {/* DANGER ZONES */}
      <Section id="danger-zones" icon={ShieldAlert} title="Zone di Rischio" open={openSections.has('danger-zones')} onToggle={toggle}>
        <p className="mb-4">
          Le zone di rischio identificano periodi in cui <strong>sia l'eCPM che la coverage calano insieme</strong>.
          Questo e' il segnale piu' preoccupante dell'analisi multi-metrica.
        </p>

        <h4 className="mb-2 font-semibold text-gray-900">Perche' sono pericolose</h4>
        <p className="mb-4">
          Quando l'eCPM cala da solo, puo' essere un effetto stagionale o un aumento di volume (piu' impressioni a prezzo
          leggermente inferiore). Ma quando <strong>anche la coverage cala</strong>, significa che la domanda pubblicitaria
          e' in vera difficolta': meno annunci disponibili E a prezzi piu' bassi.
        </p>

        <h4 className="mb-2 font-semibold text-gray-900">Livelli di severity</h4>
        <table className="mb-4 w-full border-collapse">
          <thead><tr><Th>Severity</Th><Th>Condizione</Th><Th>Significato</Th></tr></thead>
          <tbody>
            <tr><Td><Badge color="red">HIGH</Badge></Td><Td className="font-mono">eCPM &lt; -15% E coverage &lt; -15%</Td><Td>Crollo domanda grave. Azione immediata necessaria.</Td></tr>
            <tr><Td><Badge color="orange">MEDIUM</Badge></Td><Td className="font-mono">eCPM &lt; -5% E coverage &lt; -5%</Td><Td>Debolezza domanda significativa. Monitorare attentamente.</Td></tr>
          </tbody>
        </table>

        <h4 className="mb-2 font-semibold text-gray-900">% Match (Affidabilita')</h4>
        <p className="mb-4">
          Ogni zona mostra una % match che indica la forza dell'evidenza, basata su: severita' del calo (35%),
          doppia conferma eCPM+coverage (30%), ampiezza del campione (20%), e tripla conferma con bacino (15%).
        </p>

        <h4 className="mb-2 font-semibold text-gray-900">Come reagire</h4>
        <ul className="list-disc space-y-1 pl-5">
          <li>Verificare se la <strong>competizione</strong> ha offerte migliori per gli stessi advertiser</li>
          <li><strong>Contattare gli advertiser</strong> principali per capire se hanno ridotto i budget</li>
          <li>Valutare riduzione dei <strong>floor price</strong> per non perdere ulteriori impressioni</li>
          <li>Controllare se il problema e' <strong>specifico del publisher</strong> o di mercato (confrontare con altri publisher nella stessa geo)</li>
        </ul>

        <div className="mt-4 rounded-lg bg-red-50 p-3">
          <p className="text-sm text-red-800">
            <strong>Regola d'oro:</strong> le Zone di Rischio richiedono SEMPRE attenzione. A differenza di altri pattern che
            possono essere stagionali o fisiologici, il doppio calo eCPM + coverage indica vera debolezza strutturale della domanda.
          </p>
        </div>
      </Section>

      {/* DRIVER GUIDE */}
      <Section id="driver-guide" icon={BookOpen} title="Guida ai Driver" open={openSections.has('driver-guide')} onToggle={toggle}>
        <p className="mb-4">
          Il driver classifica la <strong>causa sottostante</strong> di una variazione di eCPM. Ogni finestra di ottimizzazione
          e pattern ricorrente ha un driver associato.
        </p>
        <table className="mb-4 w-full border-collapse">
          <thead><tr><Th>Driver</Th><Th>Significato</Th><Th>Azione Consigliata</Th></tr></thead>
          <tbody>
            <tr>
              <Td><Badge color="green">Domanda</Badge></Td>
              <Td>Vera domanda pubblicitaria in aumento. Bacino e coverage stabili o in crescita.</Td>
              <Td>Ottimizzare floor price, e' il momento giusto. Segnale genuino e affidabile.</Td>
            </tr>
            <tr>
              <Td><Badge color="orange">Compressione Supply</Badge></Td>
              <Td>eCPM sale perche' l'inventory si contrae (bacino in calo &gt; 5%).</Td>
              <Td><strong>NON alzare i floor</strong> — il segnale e' fuorviante. L'eCPM alto nasconde una perdita di volume.</Td>
            </tr>
            <tr>
              <Td><Badge color="orange">Effetto Fill</Badge></Td>
              <Td>eCPM sale perche' solo le impressioni premium vengono servite (coverage in calo &gt; 5%).</Td>
              <Td>Verificare perche' la coverage cala. Il prezzo unitario sale ma il volume servito scende.</Td>
            </tr>
            <tr>
              <Td><Badge color="blue">Volume</Badge></Td>
              <Td>eCPM scende per aumento volume di impressioni (&gt; 5%).</Td>
              <Td>Verificare la revenue totale — potrebbe crescere nonostante l'eCPM piu' basso.</Td>
            </tr>
            <tr>
              <Td><Badge color="purple">Stagionale</Badge></Td>
              <Td>Effetto stagionale: l'offerta supera la domanda, eCPM in calo fisiologico.</Td>
              <Td>Normale. Ridurre floor per mantenere fill rate nel periodo.</Td>
            </tr>
            <tr>
              <Td><Badge color="gray">Misto</Badge></Td>
              <Td>Nessun driver dominante identificato. Combinazione di fattori.</Td>
              <Td>Analisi manuale necessaria. Controllare le metriche individualmente.</Td>
            </tr>
          </tbody>
        </table>
        <div className="rounded-lg bg-amber-50 p-3">
          <p className="text-sm text-amber-800">
            <strong>Badge arancione con triangolo:</strong> indica un segnale <strong>potenzialmente fuorviante</strong>.
            L'eCPM sta salendo, ma non perche' la domanda e' forte — piuttosto perche' il denominatore (inventory o fill)
            si sta contraendo. Non ottimizzare i floor price in queste condizioni.
          </p>
        </div>
      </Section>

      {/* FAQ */}
      <Section id="faq" icon={HelpCircle} title="FAQ" open={openSections.has('faq')} onToggle={toggle}>
        <div className="space-y-5">
          <div><h4 className="font-semibold text-gray-900">Cos'e' la baseline?</h4><p>Media dei ricavi per stessa ora/giorno nelle <strong>7 settimane</strong> precedenti (7 same-weekday same-hour data points). Deviazione standard calcolata con formula campionaria (N-1).</p></div>
          <div><h4 className="font-semibold text-gray-900">Perche' piu' alert per lo stesso publisher?</h4><p>Alert generati per canale (GOOGLE/OPEN_BIDDING) e per regola (A1/A2/A3) separatamente.</p></div>
          <div><h4 className="font-semibold text-gray-900">GOOGLE vs OPEN_BIDDING?</h4><p><strong>GOOGLE:</strong> domanda diretta AdX/AdSense. <strong>OPEN_BIDDING:</strong> SSP terze (Amazon, Index Exchange...) via asta OB.</p></div>
          <div><h4 className="font-semibold text-gray-900">Quando preoccuparsi davvero?</h4><p><Badge color="red">P0</Badge> sempre. <Badge color="orange">P1</Badge> verificare se concentrato o distribuito. <Badge color="yellow">P2</Badge> monitora, spesso si risolve in 4-8h.</p></div>
          <div><h4 className="font-semibold text-gray-900">REVENUE_ONLY?</h4><p>Cambio mix inventory, calo CPM inserzionisti, o variazione stagionale domanda. Controlla eCPM nella pagina publisher.</p></div>
          <div><h4 className="font-semibold text-gray-900">Soglie modificabili?</h4><p>Si': <code className="rounded bg-gray-100 px-1 text-xs">config/alerting_rules.yaml</code>. P0: -15%, drift: -8%, triage: -10%.</p></div>
          <div><h4 className="font-semibold text-gray-900">Frequenza?</h4><p>Alert A1+A3 ogni <strong>2h</strong>. Drift A2 ogni <strong>6h</strong>. Recheck alert aperti ogni <strong>5 min</strong>. Configurabile in YAML.</p></div>
          <div><h4 className="font-semibold text-gray-900">Backtest?</h4><p>Esegue pipeline su dati storici. Valida nuove soglie. Alert marcati separatamente, no notifiche.</p></div>
          <div><h4 className="font-semibold text-gray-900">Cos'e' un alert A0?</h4><p>Alert tecnico generato quando i dati mancano per piu' di 4 ore consecutive. Bypassa triage e analisi. Richiede verifica immediata del data pipeline.</p></div>
          <div><h4 className="font-semibold text-gray-900">C'e' un rate limit?</h4><p>Si': <strong>5 backtest/ora</strong>, <strong>10 admin/ora</strong>, <strong>30 mutazioni/minuto</strong> (ACK/resolve/etc), <strong>60 GET/minuto</strong>. Protegge il sistema da abusi.</p></div>

          <hr className="border-gray-200" />
          <h4 className="text-xs font-bold uppercase tracking-wider text-gray-500">Intelligenza Multi-Metrica</h4>

          <div>
            <h4 className="font-semibold text-gray-900">Perche' l'eCPM sale ma la revenue scende?</h4>
            <p><strong>Compressione Supply:</strong> meno inventory (bacino in calo) significa che il prezzo unitario sale, ma il volume
            totale scende. L'eCPM e' un rapporto — puo' salire anche quando le cose vanno male. Guarda sempre il driver: se e'
            arancione (Compressione Supply o Effetto Fill), il segnale e' fuorviante.</p>
          </div>
          <div>
            <h4 className="font-semibold text-gray-900">Cosa significa il badge arancione con triangolo?</h4>
            <p>Indica un segnale <strong>potenzialmente fuorviante</strong>. L'eCPM si muove nella direzione indicata, ma la causa
            non e' un aumento di domanda reale. Non prendere decisioni di ottimizzazione floor price basandoti solo su questo segnale.</p>
          </div>
          <div>
            <h4 className="font-semibold text-gray-900">La % match e' bassa, devo preoccuparmi?</h4>
            <p>La % match indica quanto il pattern e' affidabile e preciso. Si basa su coerenza interna dei dati, conferma cross-anno,
            e ampiezza del campione. Una % alta significa che puoi fidarti del segnale per prendere decisioni operative.
            Una % bassa non e' allarmante di per se', ma indica che il segnale va trattato con cautela.
            I pattern piu' affidabili combinano alta % match e driver "Domanda" (verde).</p>
          </div>
          <div>
            <h4 className="font-semibold text-gray-900">Quando devo intervenire su una Zona di Rischio?</h4>
            <p><strong>Sempre.</strong> Le Zone di Rischio indicano vera debolezza della domanda (eCPM e coverage entrambi in calo).
            A differenza di altri pattern che possono essere stagionali, il doppio calo richiede sempre attenzione: verificare la
            competizione, contattare advertiser, valutare riduzione floor price.</p>
          </div>
        </div>
      </Section>
    </>
  )
}

// ---------------------------------------------------------------------------
// Technical Tab
// ---------------------------------------------------------------------------

const TECH_SECTIONS = ['arch', 'stack', 'api', 'db', 'langgraph', 'data', 'multi-metric-arch', 'multi-metric-api', 'driver-classification', 'consistency-score', 'danger-zone-detection', 'deploy', 'security', 'config', 'scheduling']

function TechnicalDocs({ openSections, toggle }: { openSections: Set<string>; toggle: (id: string) => void }) {
  return (
    <>
      {/* ARCHITECTURE */}
      <Section id="arch" icon={Network} title="Architettura di Sistema" open={openSections.has('arch')} onToggle={toggle}>
        <p className="mb-4">Sentinel e' un monolite modulare: un unico processo Python che espone API REST, gestisce lo scheduling e orchestra la pipeline di analisi.</p>

        <CodeBlock>{`┌─────────────────────────────────────────────────────────────┐
│  Browser (React SPA)                                        │
│  localhost:5173 (dev) / :8000 (prod, served by FastAPI)     │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP / JSON
┌──────────────────────────▼──────────────────────────────────┐
│  FastAPI  (backend/main.py)                     port 8000   │
│  ├── /auth/*    Google OAuth + session cookies              │
│  ├── /api/*     REST API (alerts, publishers, backtest)     │
│  └── /*         Static files (prod only, SPA catch-all)     │
├─────────────────────────────────────────────────────────────┤
│  APScheduler    (async, in-process)                         │
│  ├── alerting_cycle (A1+A3) ogni 2h                         │
│  ├── drift_cycle (A2)       ogni 6h                         │
│  └── check_recheck_queue    ogni 5min                       │
├─────────────────────────────────────────────────────────────┤
│  LangGraph Pipeline  (11 agenti)                            │
│  orchestrator → data_fetcher → validator → anomaly_detector │
│  → triage → [contributor | geo | env] → insight → report    │
│  → notifier                                                 │
├─────────────────────────────────────────────────────────────┤
│  Data Layer                                                 │
│  ├── SQLite (WAL)     alerts, events, recheck_queue         │
│  ├── Parquet (3 file) dati storici baseline                 │
│  └── [Athena / GAM]  future data sources                   │
└─────────────────────────────────────────────────────────────┘`}</CodeBlock>

        <div className="space-y-3">
          <div>
            <h4 className="font-semibold text-gray-900">Scelte architetturali</h4>
            <ul className="mt-1 list-disc space-y-1 pl-5">
              <li><strong>Monolite:</strong> un singolo processo semplifica deploy, debugging e ops. Il team e' piccolo (&lt;20), non serve microservizi.</li>
              <li><strong>SQLite WAL:</strong> zero-config, supporta letture concorrenti, sufficiente per ~200 alert. Migrazione a Postgres se necessario e' banale (stesso SQL).</li>
              <li><strong>LangGraph:</strong> permette di modellare la pipeline come grafo con state management, branching condizionale e parallelismo.</li>
              <li><strong>Dual mode:</strong> ogni agente ha fallback statistico (no LLM) se <code className="rounded bg-gray-100 px-1 text-xs">ANTHROPIC_API_KEY</code> non e' configurata.</li>
            </ul>
          </div>
        </div>
      </Section>

      {/* TECH STACK */}
      <Section id="stack" icon={FolderTree} title="Tech Stack e Dipendenze" open={openSections.has('stack')} onToggle={toggle}>
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <div>
            <h4 className="mb-2 font-semibold text-gray-900">Backend</h4>
            <table className="w-full border-collapse">
              <tbody>
                <tr><Td className="font-mono text-xs">fastapi 0.115</Td><Td>Framework REST async</Td></tr>
                <tr><Td className="font-mono text-xs">uvicorn 0.34</Td><Td>ASGI server (reload dev, 1 worker prod)</Td></tr>
                <tr><Td className="font-mono text-xs">pydantic 2.10</Td><Td>Validazione dati + schema API</Td></tr>
                <tr><Td className="font-mono text-xs">langgraph 0.2</Td><Td>Orchestrazione pipeline multi-agente</Td></tr>
                <tr><Td className="font-mono text-xs">langchain-anthropic 0.3</Td><Td>Integrazione Claude (Haiku/Sonnet)</Td></tr>
                <tr><Td className="font-mono text-xs">pandas 2.2 + pyarrow 18</Td><Td>Lettura/manipolazione Parquet</Td></tr>
                <tr><Td className="font-mono text-xs">apscheduler 3.11</Td><Td>Scheduling pipeline (async)</Td></tr>
                <tr><Td className="font-mono text-xs">authlib 1.3</Td><Td>Google OAuth client</Td></tr>
                <tr><Td className="font-mono text-xs">httpx 0.28</Td><Td>HTTP client async</Td></tr>
                <tr><Td className="font-mono text-xs">slowapi 0.1</Td><Td>Rate limiting per endpoint</Td></tr>
                <tr><Td className="font-mono text-xs">sqlite3 (stdlib)</Td><Td>Database embedded (WAL mode)</Td></tr>
              </tbody>
            </table>
          </div>
          <div>
            <h4 className="mb-2 font-semibold text-gray-900">Frontend</h4>
            <table className="w-full border-collapse">
              <tbody>
                <tr><Td className="font-mono text-xs">react 18</Td><Td>UI framework</Td></tr>
                <tr><Td className="font-mono text-xs">typescript 5</Td><Td>Type safety</Td></tr>
                <tr><Td className="font-mono text-xs">vite 7</Td><Td>Build + dev server + HMR</Td></tr>
                <tr><Td className="font-mono text-xs">tailwind css 4</Td><Td>Utility-first styling</Td></tr>
                <tr><Td className="font-mono text-xs">@tanstack/react-query</Td><Td>Server state + caching</Td></tr>
                <tr><Td className="font-mono text-xs">recharts</Td><Td>Grafici (trend, KPI)</Td></tr>
                <tr><Td className="font-mono text-xs">react-router-dom 6</Td><Td>Routing SPA</Td></tr>
                <tr><Td className="font-mono text-xs">lucide-react</Td><Td>Icone</Td></tr>
              </tbody>
            </table>
          </div>
        </div>
        <div className="mt-4 rounded-lg bg-amber-50 p-3">
          <p className="text-sm text-amber-800">
            <strong>Dipendenze future (predisposte, non ancora attive):</strong> boto3 + pyathena (AWS Athena),
            slack-sdk (notifiche Slack), aiosmtplib (email). Le configurazioni sono gestibili da Admin page.
          </p>
        </div>
      </Section>

      {/* API REFERENCE */}
      <Section id="api" icon={Code} title="API Reference" open={openSections.has('api')} onToggle={toggle}>
        <p className="mb-4">Tutte le API sono sotto <code className="rounded bg-gray-100 px-1 text-xs">/api</code>. Auth su <code className="rounded bg-gray-100 px-1 text-xs">/auth</code>. Documentazione OpenAPI live: <code className="rounded bg-gray-100 px-1 text-xs">/docs</code>.</p>

        <h4 className="mb-2 font-semibold text-gray-900">Alert</h4>
        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>Method</Th><Th>Endpoint</Th><Th>Descrizione</Th></tr></thead>
          <tbody>
            <tr><Td><Badge color="green">GET</Badge></Td><Td className="font-mono">/api/alerts</Td><Td>Lista alert con filtri (severity, status, channel, date_from, date_to, limit, offset)</Td></tr>
            <tr><Td><Badge color="green">GET</Badge></Td><Td className="font-mono">/api/alerts/:id</Td><Td>Dettaglio alert completo (contributors, geo, env, insights, events)</Td></tr>
            <tr><Td><Badge color="green">GET</Badge></Td><Td className="font-mono">/api/alerts/:id/trend</Td><Td>Trend 7gg revenue vs baseline (da parquet)</Td></tr>
            <tr><Td><Badge color="blue">POST</Badge></Td><Td className="font-mono">/api/alerts/:id/ack</Td><Td>Acknowledge (OPEN → ACK)</Td></tr>
            <tr><Td><Badge color="blue">POST</Badge></Td><Td className="font-mono">/api/alerts/:id/resolve</Td><Td>Resolve (qualsiasi → RESOLVED)</Td></tr>
            <tr><Td><Badge color="blue">POST</Badge></Td><Td className="font-mono">/api/alerts/:id/recheck</Td><Td>Schedula recheck (+1h)</Td></tr>
            <tr><Td><Badge color="blue">POST</Badge></Td><Td className="font-mono">/api/alerts/:id/comment</Td><Td>Aggiunge commento</Td></tr>
          </tbody>
        </table>

        <h4 className="mb-2 font-semibold text-gray-900">Publisher</h4>
        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>Method</Th><Th>Endpoint</Th><Th>Descrizione</Th></tr></thead>
          <tbody>
            <tr><Td><Badge color="green">GET</Badge></Td><Td className="font-mono">/api/publishers/top</Td><Td>Top publisher per revenue (year, limit)</Td></tr>
            <tr><Td><Badge color="green">GET</Badge></Td><Td className="font-mono">/api/publishers/:id/weekly-kpis</Td><Td>KPI settimanali (revenue, eCPM, bacino, coverage)</Td></tr>
            <tr><Td><Badge color="green">GET</Badge></Td><Td className="font-mono">/api/publishers/:id/ecpm-analysis</Td><Td>Analisi stagionale eCPM con optimization windows</Td></tr>
            <tr><Td><Badge color="green">GET</Badge></Td><Td className="font-mono">/api/publishers/:id/recurring-patterns</Td><Td>Pattern ricorrenti cross-anno (eCPM, nascosti, zone di rischio)</Td></tr>
          </tbody>
        </table>

        <h4 className="mb-2 font-semibold text-gray-900">Sistema</h4>
        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>Method</Th><Th>Endpoint</Th><Th>Descrizione</Th></tr></thead>
          <tbody>
            <tr><Td><Badge color="green">GET</Badge></Td><Td className="font-mono">/api/health</Td><Td>Health check (DB, scheduler, version)</Td></tr>
            <tr><Td><Badge color="green">GET</Badge></Td><Td className="font-mono">/api/backtest</Td><Td>Lista backtest eseguiti</Td></tr>
            <tr><Td><Badge color="blue">POST</Badge></Td><Td className="font-mono">/api/backtest</Td><Td>Avvia backtest (start_date, end_date, step_hours)</Td></tr>
            <tr><Td><Badge color="green">GET</Badge></Td><Td className="font-mono">/api/admin/datasources</Td><Td>Configurazione data sources</Td></tr>
            <tr><Td><Badge color="blue">POST</Badge></Td><Td className="font-mono">/api/admin/datasources</Td><Td>Aggiorna configurazione data sources</Td></tr>
          </tbody>
        </table>

        <h4 className="mb-2 font-semibold text-gray-900">Auth</h4>
        <table className="w-full border-collapse text-xs">
          <thead><tr><Th>Method</Th><Th>Endpoint</Th><Th>Descrizione</Th></tr></thead>
          <tbody>
            <tr><Td><Badge color="green">GET</Badge></Td><Td className="font-mono">/auth/login</Td><Td>Redirect a Google OAuth consent (dev: redirect a frontend)</Td></tr>
            <tr><Td><Badge color="green">GET</Badge></Td><Td className="font-mono">/auth/callback</Td><Td>Callback OAuth, crea sessione, set cookie</Td></tr>
            <tr><Td><Badge color="green">GET</Badge></Td><Td className="font-mono">/auth/me</Td><Td>Utente corrente (dev: user fittizio)</Td></tr>
            <tr><Td><Badge color="blue">POST</Badge></Td><Td className="font-mono">/auth/logout</Td><Td>Cancella sessione e cookie</Td></tr>
          </tbody>
        </table>
      </Section>

      {/* DATABASE */}
      <Section id="db" icon={Database} title="Database Schema (SQLite)" open={openSections.has('db')} onToggle={toggle}>
        <p className="mb-4">SQLite con WAL (Write-Ahead Logging) per letture concorrenti. File: <code className="rounded bg-gray-100 px-1 text-xs">data/vna_alerts.db</code>.</p>

        <h4 className="mb-2 font-semibold text-gray-900">alerts</h4>
        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>Colonna</Th><Th>Tipo</Th><Th>Note</Th></tr></thead>
          <tbody>
            <tr><Td className="font-mono">alert_id</Td><Td>TEXT PK</Td><Td>Formato: <code className="text-xs">ALT-YYYYMMDD-HHMMSS-P{'{0,1,2}'}</code></Td></tr>
            <tr><Td className="font-mono">timestamp</Td><Td>TEXT</Td><Td>ISO 8601</Td></tr>
            <tr><Td className="font-mono">severity</Td><Td>TEXT</Td><Td>CHECK: P0, P1, P2</Td></tr>
            <tr><Td className="font-mono">channel_group</Td><Td>TEXT</Td><Td>CHECK: GOOGLE, OPEN_BIDDING</Td></tr>
            <tr><Td className="font-mono">status</Td><Td>TEXT</Td><Td>CHECK: OPEN, ACK, RESOLVED, SNOOZED</Td></tr>
            <tr><Td className="font-mono">alert_rule</Td><Td>TEXT</Td><Td>CHECK: A0, A1, A2, A3</Td></tr>
            <tr><Td className="font-mono">revenue_current</Td><Td>REAL</Td><Td>Ricavo periodo corrente (EUR)</Td></tr>
            <tr><Td className="font-mono">revenue_baseline</Td><Td>REAL</Td><Td>Ricavo baseline 7gg (EUR)</Td></tr>
            <tr><Td className="font-mono">revenue_delta_pct</Td><Td>REAL</Td><Td>Delta percentuale</Td></tr>
            <tr><Td className="font-mono">triage_label</Td><Td>TEXT</Td><Td>TRAFFIC_DRIVEN, COVERAGE_DRIVEN, MIXED, REVENUE_ONLY</Td></tr>
            <tr><Td className="font-mono">contributors_json</Td><Td>TEXT</Td><Td>JSON array dei top publisher</Td></tr>
            <tr><Td className="font-mono">geo_breakdown_json</Td><Td>TEXT</Td><Td>JSON array breakdown geografico</Td></tr>
            <tr><Td className="font-mono">environment_split_json</Td><Td>TEXT</Td><Td>JSON object split WEB/AMP/APP</Td></tr>
            <tr><Td className="font-mono">insights_json</Td><Td>TEXT</Td><Td>JSON object findings + next steps</Td></tr>
            <tr><Td className="font-mono">execution_time_sec</Td><Td>REAL</Td><Td>Durata pipeline</Td></tr>
            <tr><Td className="font-mono">data_source</Td><Td>TEXT</Td><Td>athena, parquet, cache</Td></tr>
            <tr><Td className="font-mono">config_version</Td><Td>TEXT</Td><Td>Versione della configurazione (default: "1.0.0")</Td></tr>
          </tbody>
        </table>

        <h4 className="mb-2 font-semibold text-gray-900">alert_events</h4>
        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>Colonna</Th><Th>Tipo</Th><Th>Note</Th></tr></thead>
          <tbody>
            <tr><Td className="font-mono">event_id</Td><Td>INTEGER PK</Td><Td>Autoincrement</Td></tr>
            <tr><Td className="font-mono">alert_id</Td><Td>TEXT FK</Td><Td>Riferimento a alerts.alert_id</Td></tr>
            <tr><Td className="font-mono">event_type</Td><Td>TEXT</Td><Td>ACK, RESOLVE, RECHECK, COMMENT</Td></tr>
            <tr><Td className="font-mono">user_id</Td><Td>TEXT</Td><Td>Chi ha eseguito l'azione</Td></tr>
            <tr><Td className="font-mono">comment</Td><Td>TEXT</Td><Td>Opzionale</Td></tr>
          </tbody>
        </table>

        <h4 className="mb-2 font-semibold text-gray-900">recheck_queue</h4>
        <p className="text-xs text-gray-500">Coda dei recheck schedulati. Status: PENDING → COMPLETED / FAILED.</p>

        <h4 className="mb-2 font-semibold text-gray-900">backtest_results</h4>
        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>Colonna</Th><Th>Tipo</Th><Th>Note</Th></tr></thead>
          <tbody>
            <tr><Td className="font-mono">backtest_id</Td><Td>TEXT PK</Td><Td>ID univoco del backtest</Td></tr>
            <tr><Td className="font-mono">status</Td><Td>TEXT</Td><Td>RUNNING, COMPLETED, FAILED</Td></tr>
            <tr><Td className="font-mono">date_range</Td><Td>JSON</Td><Td>{'{"start", "end", "step_hours"}'}</Td></tr>
            <tr><Td className="font-mono">alerts_generated</Td><Td>INTEGER</Td><Td>Numero alert generati</Td></tr>
            <tr><Td className="font-mono">trigger_rate</Td><Td>REAL</Td><Td>% checks che hanno generato alert</Td></tr>
          </tbody>
        </table>

        <div className="mt-3 rounded-lg bg-gray-50 p-3 text-xs text-gray-600">
          Indici: <code>idx_alerts_timestamp</code>, <code>idx_alerts_status</code>, <code>idx_alerts_severity</code>.
          Foreign keys abilitate (<code>PRAGMA foreign_keys=ON</code>).
        </div>
      </Section>

      {/* LANGGRAPH */}
      <Section id="langgraph" icon={Cpu} title="LangGraph Pipeline (Dettaglio Tecnico)" open={openSections.has('langgraph')} onToggle={toggle}>
        <p className="mb-4">
          La pipeline e' implementata come <code className="rounded bg-gray-100 px-1 text-xs">StateGraph</code> di LangGraph.
          Ogni nodo e' una funzione <code className="rounded bg-gray-100 px-1 text-xs">(AlertState) → AlertState</code> che arricchisce lo stato.
        </p>

        <h4 className="mb-2 font-semibold text-gray-900">AlertState (TypedDict)</h4>
        <CodeBlock>{`AlertState = {
  # Input
  trigger_type: str       # A0, A1, A2, A3
  channel_group: str      # GOOGLE, OPEN_BIDDING
  mode: str               # LIVE, BACKTEST
  timestamp: str          # ISO 8601

  # Data (populated by data_fetcher)
  current_metrics: dict   # {revenue, bacino, coverage, ...}
  baseline_metrics: dict  # {revenue, bacino, coverage, ...}
  delta: dict             # {revenue_pct, bacino_pct, coverage_pct, publishers, geo, env}
  historical_stats: dict  # {revenue_std, hour_of_day, day_of_week, ...}

  # Analysis results
  validation_status: str  # "OK" or error
  alert_triggered: bool
  severity: str           # P0, P1, P2, NONE
  z_score: float
  confidence: float       # 0.0 - 1.0
  triage_label: str       # TRAFFIC_DRIVEN, COVERAGE_DRIVEN, MIXED, REVENUE_ONLY
  contributors: list      # [{publisher_id, delta_eur, quota_of_drop, ...}]
  geo_breakdown: list     # [{cluster, delta_pct, status, ...}]
  environment_split: dict # {WEB: {...}, AMP: {...}, APP: {...}, amp_drift_detected}

  # Output
  insights: dict          # {top_findings, diagnosis_confidence, next_steps}
  alert_payload: dict     # Payload finale per DB
  markdown_report: str    # Report formattato
  delivery_status: dict   # {slack: bool, email: bool}

  # Metadata
  execution_errors: list  # Errori non-bloccanti accumulati
  data_source: str        # "athena", "parquet", "cache"
  alert_rule: str         # "A0", "A1", "A2", "A3" (may differ from trigger_type)
}`}</CodeBlock>

        <h4 className="mb-2 font-semibold text-gray-900">Grafo e branching</h4>
        <CodeBlock>{`orchestrator → data_fetcher → data_validator ─┬─ (A0) → report_builder → END
                                               └─ anomaly_detector → triage_classifier
                                                                          │
                                              ┌───── alert_triggered? ────┘
                                              │
                                    YES ──────┼────── NO → END
                                              │
                                    parallel_analysis
                                    ├── contributor_analyzer
                                    ├── geo_analyzer
                                    └── environment_splitter
                                              │
                                    insight_generator → report_builder
                                              │
                                    ┌── mode? ┘
                                    │
                              LIVE ─┼── BACKTEST → END
                                    │
                                notifier → END`}</CodeBlock>

        <h4 className="mb-2 font-semibold text-gray-900">Dual mode: LLM + Fallback</h4>
        <p>
          Gli agenti 4 (Anomaly Detector), 6a (Contributor), 6b (Geo) e 7 (Insight) supportano due modalita':
        </p>
        <ul className="mt-1 list-disc space-y-1 pl-5">
          <li><strong>Con API key:</strong> usano Claude (Haiku per 4/6a/6b, Sonnet per 7) per analisi avanzata.</li>
          <li><strong>Senza API key:</strong> fallback statistico/template deterministico. Zero costi, zero latenza LLM.</li>
          <li>Se l'LLM fallisce a runtime, il fallback viene usato automaticamente e l'errore e' loggato in <code className="rounded bg-gray-100 px-1 text-xs">execution_errors</code>.</li>
        </ul>
      </Section>

      {/* DATA LAYER */}
      <Section id="data" icon={Database} title="Data Layer (Parquet + Athena)" open={openSections.has('data')} onToggle={toggle}>
        <h4 className="mb-2 font-semibold text-gray-900">File Parquet (attuale)</h4>
        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>File</Th><Th>Righe</Th><Th>Size</Th><Th>Contenuto</Th></tr></thead>
          <tbody>
            <tr><Td className="font-mono text-xs">daily_adrequests_aggregated.parquet</Td><Td>~360K</Td><Td>4 MB</Td><Td>Ad requests giornalieri per publisher/country/environment</Td></tr>
            <tr><Td className="font-mono text-xs">daily_channel_aggregated.parquet</Td><Td>~650K</Td><Td>3.4 MB</Td><Td>Revenue/impressioni giornaliere per channel/publisher</Td></tr>
            <tr><Td className="font-mono text-xs">hourly_aggregated.parquet</Td><Td>~740K</Td><Td>5.4 MB</Td><Td>Metriche orarie per channel (usate per alert A1)</Td></tr>
          </tbody>
        </table>
        <p className="mb-3">Range temporale: <strong>Gen 2024 - Gen 2026</strong>. Caricati in memoria (pandas DataFrame) con caching applicativo.</p>

        <h4 className="mb-2 font-semibold text-gray-900">AWS Athena (futuro)</h4>
        <p className="mb-2">Predisposto ma non ancora attivo. Il data fetcher ha gia' la logica per:</p>
        <ul className="list-disc space-y-1 pl-5">
          <li>Query Athena via <code className="rounded bg-gray-100 px-1 text-xs">pyathena</code> con timeout configurabile (default 30s) e 1 retry (2 tentativi totali) con exponential backoff</li>
          <li>Fallback chain: Athena → GAM → Parquet. In LIVE mode, se nessuna fonte reale disponibile, la pipeline si blocca (no synthetic)</li>
          <li>Cache risultati per 24h (<code className="rounded bg-gray-100 px-1 text-xs">data_sources.cache_ttl_hours</code>)</li>
        </ul>

        <h4 className="mt-3 mb-2 font-semibold text-gray-900">GAM API (futuro)</h4>
        <p>Google Ad Manager API come fonte alternativa. Configurabile da Admin page.</p>

        <div className="mt-3 rounded-lg bg-amber-50 p-3">
          <p className="text-sm text-amber-800">
            <strong>Data source switching:</strong> gestito da Admin page (<code>/admin</code>). Il file di configurazione
            e' <code>data/datasource_config.json</code>. Il data fetcher sceglie la fonte in base alla config attiva.
          </p>
        </div>
      </Section>

      {/* MULTI-METRIC DATA ARCHITECTURE */}
      <Section id="multi-metric-arch" icon={BarChart3} title="Architettura Dati Multi-Metrica" open={openSections.has('multi-metric-arch')} onToggle={toggle}>
        <p className="mb-4">
          L'analisi multi-metrica si basa su <strong>3 file JSON pre-computati</strong> generati da script di analisi
          sui dati parquet reali (<code className="rounded bg-gray-100 px-1 text-xs">data/baseline/</code>).
        </p>

        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>File</Th><Th>Path</Th><Th>Contenuto</Th></tr></thead>
          <tbody>
            <tr>
              <Td className="font-mono">ecpm-seasonal-analysis.json</Td>
              <Td className="font-mono text-xs">data/seasonal/</Td>
              <Td>Periodi stagionali con metriche aggregate e lookup settimana → periodo. Identifica Pasqua, Estate, Back to School, Black Friday, Natale, ecc.</Td>
            </tr>
            <tr>
              <Td className="font-mono">enriched-recurring-patterns.json</Td>
              <Td className="font-mono text-xs">data/seasonal/</Td>
              <Td>Pattern ricorrenti cross-year con driver classificato, metriche dettagliate (eCPM, bacino, coverage, impressions, revenue) e consistency score.</Td>
            </tr>
            <tr>
              <Td className="font-mono">optimization-windows-enriched.json</Td>
              <Td className="font-mono text-xs">data/seasonal/</Td>
              <Td>Finestre di ottimizzazione arricchite con driver causale, match YoY, e metriche aggiuntive per ogni finestra.</Td>
            </tr>
          </tbody>
        </table>

        <h4 className="mb-2 font-semibold text-gray-900">Pipeline di generazione</h4>
        <CodeBlock>{`data/baseline/*.parquet
        │
        ├── Script analisi stagionale
        │   └── ecpm-seasonal-analysis.json
        │
        ├── Script pattern ricorrenti
        │   └── enriched-recurring-patterns.json
        │       (cross-year matching, Pearson correlation, driver classification)
        │
        └── Script finestre ottimizzazione
            └── optimization-windows-enriched.json
                (driver enrichment, YoY consistency scoring)`}</CodeBlock>

        <div className="mt-3 rounded-lg bg-blue-50 p-3">
          <p className="text-sm text-blue-800">
            <strong>Dati reali:</strong> tutti i file sono generati da dati parquet reali (Gen 2024 - Gen 2026).
            Nessun dato sintetico o mock. La rigenerazione richiede accesso ai file parquet in <code className="text-xs">data/baseline/</code>.
          </p>
        </div>
      </Section>

      {/* MULTI-METRIC API ENDPOINTS */}
      <Section id="multi-metric-api" icon={Code} title="API Multi-Metrica" open={openSections.has('multi-metric-api')} onToggle={toggle}>
        <p className="mb-4">Endpoint dedicati all'analisi multi-metrica dei publisher.</p>

        <h4 className="mb-2 font-semibold text-gray-900">GET /api/publishers/{'{id}'}/recurring-patterns</h4>
        <p className="mb-2">Pattern ricorrenti cross-year con analisi completa.</p>
        <CodeBlock>{`{
  "ecpm_patterns": [
    {
      "period_name": "Estate 2024",
      "weeks": "W26-W35",
      "ecpm_delta_pct": -12.3,
      "ecpm_2024": 1.85,
      "ecpm_2025": 1.62,
      "driver": "SEASONAL_DEMAND",
      "consistency_score": 0.82,
      "bacino_delta_pct": 8.5,
      "coverage_delta_pct": -7.2,
      "revenue_delta_pct": -4.1
    }
  ],
  "hidden_patterns": [
    {
      "period_name": "Q1 Slowdown",
      "weeks": "W3-W8",
      "revenue_delta_pct": -18.5,
      "impressions_delta_pct": -17.8,
      "ecpm_status": "FLAT",  // eCPM piatto → pattern nascosto
      "weekly_impact_eur": -2150.0,
      "reliability_score": 0.85,    // affidabilità (0-1)
      "business_impact": "Durante Q1 Slowdown (6 settimane) la revenue cala..."
    }
  ],
  "danger_zones": [
    {
      "period_name": "Post-Natale",
      "weeks": "W1-W3",
      "ecpm_delta_pct": -22.1,
      "coverage_delta_pct": -18.4,
      "severity": "HIGH",
      "reliability_score": 0.78,    // affidabilità (0-1)
      "explanation": "Durante Post-Natale sia l'eCPM (-22.1%) che la coverage (-18.4%) calano..."
    }
  ],
  "yearly_avg": {
    "ecpm_2024": 2.15,
    "ecpm_2025": 2.08
  }
}`}</CodeBlock>

        <h4 className="mt-4 mb-2 font-semibold text-gray-900">GET /api/publishers/{'{id}'}/ecpm-analysis</h4>
        <p className="mb-2">Analisi stagionale eCPM con finestre di ottimizzazione arricchite.</p>
        <CodeBlock>{`{
  "optimization_windows": [
    {
      "period_name": "Black Friday",
      "signal": "RAISE",
      "ecpm_delta_pct": 28.5,
      "driver": "DEMAND_DRIVEN",
      "consistency_score": 0.91,  // score affidabilità a 4 componenti (vedi sezione dedicata)
      "bacino_delta_pct": 2.1,
      "coverage_delta_pct": 1.8,
      "impressions_delta_pct": 3.5,
      "revenue_delta_pct": 32.1,
      "match_prev_year": true,
      "prev_year_delta_pct": 25.2
    }
  ],
  "publisher_avg_ecpm": 2.15,
  "analysis_period": "2024-01 / 2026-01"
}`}</CodeBlock>

        <h4 className="mt-4 mb-2 font-semibold text-gray-900">GET /api/publishers/{'{id}'}/weekly-kpis</h4>
        <p className="mb-2">KPI settimanali con campi YoY e flag pattern ricorrenti.</p>
        <CodeBlock>{`{
  "weeks": [...],
  "has_recurring_patterns": true,
  "compare_prev_year": true,  // true se dati 2024 disponibili
  "yoy_fields": {
    "revenue_yoy_pct": -5.2,
    "ecpm_yoy_pct": 3.1,
    "bacino_yoy_pct": -8.0,
    "coverage_yoy_pct": -0.5
  }
}`}</CodeBlock>
      </Section>

      {/* DRIVER CLASSIFICATION */}
      <Section id="driver-classification" icon={Target} title="Classificazione Driver (Criteri)" open={openSections.has('driver-classification')} onToggle={toggle}>
        <p className="mb-4">
          Ogni variazione di eCPM viene classificata con un <strong>driver causale</strong> basato sulla combinazione
          di variazioni delle metriche principali. Soglia di riferimento: <strong>+/- 5%</strong>.
        </p>

        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>Driver</Th><Th>eCPM</Th><Th>Bacino</Th><Th>Coverage</Th><Th>Impressions</Th><Th>Logica</Th></tr></thead>
          <tbody>
            <tr>
              <Td><Badge color="green">DEMAND_DRIVEN</Badge></Td>
              <Td className="font-mono">&gt; +5%</Td>
              <Td className="font-mono">&ge; -5%</Td>
              <Td className="font-mono">&ge; -5%</Td>
              <Td className="font-mono">—</Td>
              <Td>eCPM sale con inventory e fill rate stabili → vera domanda</Td>
            </tr>
            <tr>
              <Td><Badge color="orange">SUPPLY_SQUEEZE</Badge></Td>
              <Td className="font-mono">&gt; +5%</Td>
              <Td className="font-mono">&lt; -5%</Td>
              <Td className="font-mono">—</Td>
              <Td className="font-mono">—</Td>
              <Td>eCPM sale ma bacino cala → prezzo alto su meno inventory</Td>
            </tr>
            <tr>
              <Td><Badge color="orange">FILL_EFFECT</Badge></Td>
              <Td className="font-mono">&gt; +5%</Td>
              <Td className="font-mono">&ge; -5%</Td>
              <Td className="font-mono">&lt; -5%</Td>
              <Td className="font-mono">—</Td>
              <Td>eCPM sale con bacino stabile ma coverage in calo → solo impressioni premium servite</Td>
            </tr>
            <tr>
              <Td><Badge color="blue">VOLUME_DRIVEN</Badge></Td>
              <Td className="font-mono">&lt; -5%</Td>
              <Td className="font-mono">—</Td>
              <Td className="font-mono">—</Td>
              <Td className="font-mono">&gt; +5%</Td>
              <Td>eCPM scende con piu' impressioni → diluizione prezzo su volume maggiore</Td>
            </tr>
            <tr>
              <Td><Badge color="purple">SEASONAL_DEMAND</Badge></Td>
              <Td className="font-mono">&lt; -5%</Td>
              <Td className="font-mono">&gt; +5%</Td>
              <Td className="font-mono">&lt; -5%</Td>
              <Td className="font-mono">—</Td>
              <Td>eCPM scende con bacino in crescita e coverage in calo → offerta supera domanda</Td>
            </tr>
            <tr>
              <Td><Badge color="gray">MIXED</Badge></Td>
              <Td className="font-mono" colSpan={4}>Nessuna combinazione sopra soddisfatta</Td>
              <Td>Nessun driver dominante identificabile</Td>
            </tr>
          </tbody>
        </table>

        <div className="rounded-lg bg-blue-50 p-3">
          <p className="text-sm text-blue-800">
            <strong>Ordine di valutazione:</strong> i criteri vengono valutati nell'ordine mostrato. Il primo match vince.
            Se nessun criterio e' soddisfatto, il driver e' MIXED. La soglia del 5% e' configurabile.
          </p>
        </div>
      </Section>

      {/* SCORE DI AFFIDABILITA' */}
      <Section id="consistency-score" icon={Zap} title="Calcolo Score di Affidabilità (% Match)" open={openSections.has('consistency-score')} onToggle={toggle}>
        <p className="mb-4">
          Lo score di affidabilita' misura quanto un pattern e' attendibile e riproducibile.
          Viene calcolato con metodologie diverse per pattern ricorrenti, finestre di ottimizzazione,
          pattern di volume nascosti e zone di rischio.
        </p>

        <h4 className="mb-2 font-semibold text-gray-900">Pattern Ricorrenti (eCPM)</h4>
        <p className="mb-2">
          Correlazione di <strong>Pearson</strong> dei delta% settimanali tra 2024 e 2025 nello stesso periodo.
        </p>
        <CodeBlock>{`# Per ogni settimana nel periodo del pattern:
delta_2024[w] = (ecpm[w] - avg_ecpm_2024) / avg_ecpm_2024 * 100
delta_2025[w] = (ecpm[w] - avg_ecpm_2025) / avg_ecpm_2025 * 100

consistency = pearson_correlation(delta_2024, delta_2025)
# Range: -1.0 (inverso) → 0.0 (nessuna correlazione) → 1.0 (perfetto)`}</CodeBlock>

        <h4 className="mt-4 mb-2 font-semibold text-gray-900">Finestre di Ottimizzazione</h4>
        <p className="mb-2">
          Score composito basato su 4 componenti pesate che misurano l'affidabilita' della finestra:
        </p>
        <CodeBlock>{`# Score di affidabilità per Finestre di Ottimizzazione
score = 0.0

# 1. Coerenza interna (0.35)
# Bassa varianza dei delta% settimanali nella finestra = segnale preciso
week_deltas = [delta_pct per ogni settimana nella finestra]
if len(week_deltas) >= 2:
    mean_d = mean(week_deltas)
    cv = std(week_deltas) / max(|mean_d|, 1)   # coefficiente di variazione
    score += 0.35 * max(0, 1 - cv)
elif len(week_deltas) == 1:
    score += 0.35 * 0.5   # credito parziale per singola settimana

# 2. Ricorrenza cross-anno (0.30)
if same_signal_prev_year:        # stesso segnale RAISE/LOWER
    score += 0.30
elif exists_in_prev_year:        # presente ma segnale diverso
    score += 0.10

# 3. Similarità magnitudine (0.20)
diff = |delta_current - delta_prev_year|
max_abs = max(|delta_current|, |delta_prev_year|, 1)
score += 0.20 * (1 - min(diff / max_abs, 1))

# 4. Ampiezza campione (0.15)
if weeks >= 4: score += 0.15
elif weeks >= 2: score += 0.15 * (weeks / 4)
else: score += 0.15 * 0.3   # singola settimana: credito minimo`}</CodeBlock>

        <h4 className="mt-4 mb-2 font-semibold text-gray-900">Pattern di Volume Nascosti (Hidden Patterns)</h4>
        <p className="mb-2">
          Score di affidabilita' per pattern nascosti sotto l'eCPM. 4 componenti pesate:
        </p>
        <CodeBlock>{`# Score di affidabilità per Pattern Nascosti
score = 0.0

# 1. Coerenza direzionale cross-anno (0.40)
# Stessa direzione (entrambi DOWN o entrambi UP) nel 2024 e 2025
same_dir = (d2024 < 0 and d2025 < 0) or (d2024 > 0 and d2025 > 0)
if same_dir:
    score += 0.40
elif one_year_neutral:    # un anno a zero
    score += 0.15

# 2. Similarità magnitudine (0.30)
diff = |avg_delta_2024 - avg_delta_2025|
max_abs = max(|avg_delta_2024|, |avg_delta_2025|, 1)
score += 0.30 * (1 - min(diff / max_abs, 1))

# 3. Ampiezza campione (0.15)
if weeks >= 4: score += 0.15
elif weeks >= 2: score += 0.15 * (weeks / 4)
else: score += 0.05

# 4. Mascheramento eCPM (0.15)
# Pattern realmente nascosti (eCPM FLAT) sono più affidabili
if ecpm_status == "FLAT":    score += 0.15   # completamente nascosto
elif ecpm_UP and signal_DOWN: score += 0.10   # mascherato da eCPM crescente
else:                         score += 0.05   # parzialmente visibile`}</CodeBlock>

        <h4 className="mt-4 mb-2 font-semibold text-gray-900">Zone di Rischio (Danger Zones)</h4>
        <p className="mb-2">
          Score di affidabilita' per le danger zone. 4 componenti pesate:
        </p>
        <CodeBlock>{`# Score di affidabilità per Danger Zones
score = 0.0

# 1. Severità calo (0.35)
# Cali più grandi = evidenza più forte di un problema reale
avg_decline = (|ecpm_delta| + |coverage_delta|) / 2
if avg_decline >= 15: score += 0.35
else: score += 0.35 * (avg_decline / 15)

# 2. Doppia conferma (0.30)
# eCPM + coverage entrambi < -5% = segnale forte
if ecpm_delta < -5% AND coverage_delta < -5%:
    score += 0.30
else:
    score += 0.15

# 3. Ampiezza campione (0.20)
if weeks >= 4: score += 0.20
elif weeks >= 2: score += 0.20 * (weeks / 4)
else: score += 0.05

# 4. Tripla conferma (0.15)
# Bonus se anche il bacino cala
if bacino_delta < -5%: score += 0.15         # triplo calo = fortissimo segnale
elif bacino_delta > +5%: score += 0.05       # bacino sale ma coverage giù = interessante
else: score += 0.08                           # bacino neutro

# Score finale: min(score, 1.0)`}</CodeBlock>

        <div className="mt-3 rounded-lg bg-gray-50 p-3 text-xs text-gray-600">
          <strong>Interpretazione:</strong> &gt; 0.7 = pattern stabile e affidabile. 0.4 - 0.7 = pattern presente ma variabile.
          &lt; 0.4 = pattern debole, non fare affidamento per decisioni operative.
        </div>
      </Section>

      {/* DANGER ZONE DETECTION */}
      <Section id="danger-zone-detection" icon={ShieldAlert} title="Danger Zone Detection" open={openSections.has('danger-zone-detection')} onToggle={toggle}>
        <p className="mb-4">
          Le danger zone vengono rilevate automaticamente analizzando i periodi in cui coverage e eCPM
          calano simultaneamente.
        </p>

        <h4 className="mb-2 font-semibold text-gray-900">Criteri di rilevamento</h4>
        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>Condizione</Th><Th>Valore</Th></tr></thead>
          <tbody>
            <tr><Td>Coverage delta</Td><Td className="font-mono">&lt; -5%</Td></tr>
            <tr><Td>eCPM delta</Td><Td className="font-mono">&lt; -5%</Td></tr>
            <tr><Td>Entrambi nello stesso periodo</Td><Td>Si' (condizione AND)</Td></tr>
          </tbody>
        </table>

        <h4 className="mb-2 font-semibold text-gray-900">Assegnazione severity</h4>
        <CodeBlock>{`if coverage_delta < -15% AND ecpm_delta < -15%:
    severity = "HIGH"
elif coverage_delta < -5% AND ecpm_delta < -5%:
    severity = "MEDIUM"
else:
    # Non e' una danger zone`}</CodeBlock>

        <h4 className="mt-3 mb-2 font-semibold text-gray-900">Struttura dati</h4>
        <CodeBlock>{`{
  "period_name": "Post-Natale",
  "weeks": "W1-W3",
  "ecpm_delta_pct": -22.1,
  "coverage_delta_pct": -18.4,
  "severity": "HIGH",
  "bacino_delta_pct": 5.2,       // il bacino puo' essere stabile o crescente
  "revenue_impact_eur": -8500.0,
  "reliability_score": 0.78,     // score di affidabilità (0-1), vedi sezione dedicata
  "explanation": "Durante Post-Natale (3 settimane) sia l'eCPM (-22.1%) che la coverage (-18.4%) calano contemporaneamente. Rischio elevato: il calo congiunto è significativo..."
}`}</CodeBlock>

        <div className="mt-3 rounded-lg bg-amber-50 p-3">
          <p className="text-sm text-amber-800">
            <strong>Nota:</strong> il bacino nelle danger zone puo' essere stabile o persino in crescita.
            Il segnale critico e' il doppio calo di eCPM (prezzo) e coverage (fill rate), che indica che
            nonostante il traffico sia presente, la domanda pubblicitaria non riesce a riempirlo ne' a prezzi adeguati.
            Il campo <code className="text-xs">explanation</code> contiene una descrizione in italiano generata automaticamente dal backend,
            e il <code className="text-xs">reliability_score</code> indica quanto il pattern e' affidabile (vedi sezione "Calcolo Score di Affidabilita'").
          </p>
        </div>
      </Section>

      {/* DEPLOY */}
      <Section id="deploy" icon={Container} title="Deploy e Infrastruttura" open={openSections.has('deploy')} onToggle={toggle}>
        <h4 className="mb-2 font-semibold text-gray-900">Sviluppo locale</h4>
        <CodeBlock>{`# Terminal 1 - Backend
python3 -m backend.main          # :8000, ENVIRONMENT=development, hot reload

# Terminal 2 - Frontend
cd frontend && npm run dev        # :5173, Vite proxy → :8000, HMR`}</CodeBlock>
        <p className="mb-4 text-xs text-gray-500">In dev: nessun login, CORS aperto, uvicorn con reload, 1 worker.</p>

        <h4 className="mb-2 font-semibold text-gray-900">Produzione (Docker)</h4>
        <CodeBlock>{`# Build e run
docker compose build              # Multi-stage: node:20 → python:3.11
docker compose up -d              # .env con ENVIRONMENT=production + OAuth

# Dockerfile stages:
# 1. frontend-build: npm ci + npm run build → frontend/dist/
# 2. runtime: pip install + copia backend + frontend/dist + config
# CMD: uvicorn --host 0.0.0.0 --port 8000 --workers 1`}</CodeBlock>

        <h4 className="mt-3 mb-2 font-semibold text-gray-900">Environment Variables (produzione)</h4>
        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>Variabile</Th><Th>Required</Th><Th>Default</Th><Th>Note</Th></tr></thead>
          <tbody>
            <tr><Td className="font-mono">ENVIRONMENT</Td><Td><Badge color="red">Si'</Badge></Td><Td>development</Td><Td>Settare a "production" per abilitare auth e static serving</Td></tr>
            <tr><Td className="font-mono">GOOGLE_CLIENT_ID</Td><Td><Badge color="red">Si'</Badge></Td><Td>-</Td><Td>Da Google Cloud Console</Td></tr>
            <tr><Td className="font-mono">GOOGLE_CLIENT_SECRET</Td><Td><Badge color="red">Si'</Badge></Td><Td>-</Td><Td>Da Google Cloud Console</Td></tr>
            <tr><Td className="font-mono">SESSION_SECRET</Td><Td><Badge color="red">Si'</Badge></Td><Td>dev-secret</Td><Td>Chiave firma sessioni. OBBLIGATORIO in produzione (il server non parte senza). Generare con <code>openssl rand -hex 32</code></Td></tr>
            <tr><Td className="font-mono">OAUTH_REDIRECT_URI</Td><Td><Badge color="orange">Rec</Badge></Td><Td>localhost:8000/auth/callback</Td><Td>URL callback registrato su Google</Td></tr>
            <tr><Td className="font-mono">FRONTEND_URL</Td><Td><Badge color="orange">Rec</Badge></Td><Td>localhost:5173</Td><Td>URL frontend (per redirect post-login e CORS)</Td></tr>
            <tr><Td className="font-mono">ALLOWED_DOMAIN</Td><Td><Badge color="gray">No</Badge></Td><Td>adkaora.com</Td><Td>Dominio email ammesso per login</Td></tr>
            <tr><Td className="font-mono">ANTHROPIC_API_KEY</Td><Td><Badge color="gray">No</Badge></Td><Td>-</Td><Td>Se presente, abilita analisi LLM (Haiku/Sonnet)</Td></tr>
            <tr><Td className="font-mono">VNA_DB_PATH</Td><Td><Badge color="gray">No</Badge></Td><Td>data/vna_alerts.db</Td><Td>Path database SQLite</Td></tr>
          </tbody>
        </table>

        <h4 className="mb-2 font-semibold text-gray-900">Infrastruttura AWS (target)</h4>
        <ul className="list-disc space-y-1 pl-5">
          <li><strong>EC2:</strong> singola istanza (t3.medium sufficiente). Docker Compose.</li>
          <li><strong>Volume:</strong> <code className="rounded bg-gray-100 px-1 text-xs">./data</code> montato come bind volume per persistenza DB e parquet.</li>
          <li><strong>Porta:</strong> 8000 unica. Frontend servito da FastAPI. Reverse proxy (nginx/ALB) consigliato per TLS.</li>
        </ul>
      </Section>

      {/* SECURITY */}
      <Section id="security" icon={Shield} title="Sicurezza" open={openSections.has('security')} onToggle={toggle}>
        <div className="space-y-4">
          <div>
            <h4 className="font-semibold text-gray-900">Autenticazione</h4>
            <ul className="mt-1 list-disc space-y-1 pl-5">
              <li><strong>Google OAuth 2.0</strong> con OpenID Connect. Solo email <code className="rounded bg-gray-100 px-1 text-xs">@adkaora.com</code>.</li>
              <li>Sessioni in-memory (dict Python). Cookie <code className="rounded bg-gray-100 px-1 text-xs">session_id</code> con token casuale (32 bytes, urlsafe).</li>
              <li>Cookie flags: <code className="rounded bg-gray-100 px-1 text-xs">httponly=True</code>, <code className="rounded bg-gray-100 px-1 text-xs">samesite=lax</code>, <code className="rounded bg-gray-100 px-1 text-xs">secure=True</code> (solo prod).</li>
              <li>TTL sessione: 24 ore. Dopo: sessione scade, cookie eliminato, redirect a login.</li>
              <li><strong>Dev bypass:</strong> <code className="rounded bg-gray-100 px-1 text-xs">ENVIRONMENT=development</code> → nessun login, utente fittizio <code className="text-xs">dev@localhost</code>.</li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold text-gray-900">Autorizzazione</h4>
            <ul className="mt-1 list-disc space-y-1 pl-5">
              <li>Dependency <code className="rounded bg-gray-100 px-1 text-xs">require_auth</code> applicata a tutte le route <code className="text-xs">/api/*</code>.</li>
              <li>Route <code className="text-xs">/auth/*</code> escluse (necessarie per il flow di login).</li>
              <li>Nessun RBAC (tutti gli utenti autenticati hanno accesso completo). Sufficiente per team &lt;20.</li>
              <li><code className="rounded bg-gray-100 px-1 text-xs">user_id</code> estratto dalla sessione server-side (<code className="text-xs">require_auth()</code>), mai dal body della request.</li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold text-gray-900">CORS</h4>
            <ul className="mt-1 list-disc space-y-1 pl-5">
              <li><strong>Dev:</strong> <code className="rounded bg-gray-100 px-1 text-xs">allow_origins=["*"]</code> (Vite su porta diversa).</li>
              <li><strong>Prod:</strong> <code className="rounded bg-gray-100 px-1 text-xs">allow_origins=[FRONTEND_URL]</code> (stessa origin, ma ristretto per sicurezza).</li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold text-gray-900">Middleware</h4>
            <p>Stack (ordine di esecuzione): CORSMiddleware → SessionMiddleware → SlowAPI Rate Limiter → Route handlers.</p>
            <p className="mt-1">Rate limiting via SlowAPI: 5 backtest/ora, 10 admin/ora, 30 mutazioni/min, 60 GET/min.</p>
            <p className="mt-1">SessionMiddleware (Starlette) usato per lo state OAuth durante il redirect flow. Secret da env var.</p>
          </div>
        </div>

        <div className="mt-4 rounded-lg bg-amber-50 p-3">
          <p className="text-sm text-amber-800">
            <strong>Limitazioni note:</strong> sessioni in-memory si perdono al restart del server (utenti devono ri-loggare).
            Per alta disponibilita', migrare a Redis o cookie-based sessions. Non critico per team piccolo.
          </p>
        </div>
      </Section>

      {/* CONFIG */}
      <Section id="config" icon={Settings} title="Configurazione (alerting_rules.yaml)" open={openSections.has('config')} onToggle={toggle}>
        <p className="mb-4">File: <code className="rounded bg-gray-100 px-1 text-xs">config/alerting_rules.yaml</code>. Tutte le soglie e i parametri del sistema.</p>
        <CodeBlock>{`revenue_anomaly:        # Regola A1 - soglie drop
  P0: {drop_percent: -15, duration_hours: 2}
  P1: {drop_percent: -10, duration_hours: 2}
  P2: {drop_percent: -5,  duration_hours: 4}

drift_detection:        # Regola A2 - drift settimanale
  enabled: true
  window_days: 7
  threshold_percent: -8

near_zero:              # Regola A3 - near-zero
  revenue_threshold_eur: 100
  coverage_threshold: 0.05
  consecutive_periods: 3

data_gap:               # Regola A0 - dati mancanti
  enabled: true
  max_gap_hours: 4
  severity: P1

triage:                 # Soglie classificazione triage
  traffic_driven_threshold: -10   # bacino drop %
  coverage_driven_threshold: -10  # coverage drop %

top_contributors:       # Contributor analysis
  top_n: 15
  min_quota_percent: 1

geo_clusters:           # Mapping country → cluster
  ITA: [IT]
  ES: [ES]
  OTHER: [BR, MX, AR, PT, CO, CL, PE, US, UK, FR, DE]

scheduling:
  interval_hours: 2               # A1+A3 ogni 2h, A2 ogni 6h (3x)
  recheck_interval_minutes: 5     # Recheck queue ogni 5min
  channels: [GOOGLE, OPEN_BIDDING]

data_sources:
  athena_timeout_seconds: 30
  athena_retry_count: 1          # 2 tentativi totali
  cache_ttl_hours: 24

notifications:
  slack_enabled: true
  email_enabled: true

top_publishers:         # 36 publisher monitorati
  - vocento
  - prensaiberica
  - mondadori
  # ... (36 totali)`}</CodeBlock>

        <div className="mt-3 rounded-lg bg-blue-50 p-3">
          <p className="text-sm text-blue-800">
            <strong>Hot reload:</strong> il config viene riletto ad ogni ciclo di alerting. Modificare il YAML e il prossimo
            ciclo usera' i nuovi valori. Non serve restart del server.
          </p>
        </div>
      </Section>

      {/* SCHEDULING */}
      <Section id="scheduling" icon={Clock} title="Scheduling e Monitoring" open={openSections.has('scheduling')} onToggle={toggle}>
        <h4 className="mb-2 font-semibold text-gray-900">APScheduler (AsyncIO)</h4>
        <p className="mb-3">Tre job schedulati in-process:</p>
        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>Job</Th><Th>Intervallo</Th><Th>Funzione</Th><Th>Descrizione</Th></tr></thead>
          <tbody>
            <tr><Td className="font-mono">alerting_cycle</Td><Td>2 ore</Td><Td className="font-mono text-xs">run_alerting_cycle()</Td><Td>Esegue A1+A3 pipeline per GOOGLE + OPEN_BIDDING</Td></tr>
            <tr><Td className="font-mono">drift_cycle</Td><Td>6 ore</Td><Td className="font-mono text-xs">run_drift_cycle()</Td><Td>Esegue A2 drift detection per GOOGLE + OPEN_BIDDING</Td></tr>
            <tr><Td className="font-mono">recheck_queue</Td><Td>5 min</Td><Td className="font-mono text-xs">check_recheck_queue()</Td><Td>Processa recheck in coda (PENDING → COMPLETED/FAILED)</Td></tr>
          </tbody>
        </table>

        <h4 className="mb-2 font-semibold text-gray-900">Health Check</h4>
        <p className="mb-3"><code className="rounded bg-gray-100 px-1 text-xs">GET /api/health</code> ritorna:</p>
        <CodeBlock>{`{
  "status": "healthy",     // "healthy" | "degraded"
  "version": "1.0.0",
  "db_ok": true,           // SQLite SELECT 1 check
  "scheduler_running": true,
  "timestamp": "2026-02-13T14:00:00Z"
}`}</CodeBlock>

        <h4 className="mb-2 font-semibold text-gray-900">Logging</h4>
        <ul className="list-disc space-y-1 pl-5">
          <li>Format: <code className="rounded bg-gray-100 px-1 text-xs">timestamp | level | module | message</code></li>
          <li>Ogni agente logga start/end con metriche chiave</li>
          <li>Errori LLM loggati come WARNING con fallback automatico</li>
          <li>Livello configurabile via <code className="rounded bg-gray-100 px-1 text-xs">LOG_LEVEL</code> env var (default: INFO)</li>
        </ul>

        <div className="mt-3 rounded-lg bg-green-50 p-3">
          <p className="text-sm text-green-800">
            <strong>Stato:</strong> lo scheduler invoca la pipeline LangGraph per A1+A3 ogni 2h e A2 ogni 6h.
            Graceful shutdown via SIGTERM handler (chiude scheduler e DB correttamente).
          </p>
        </div>
      </Section>
    </>
  )
}

// ---------------------------------------------------------------------------
// Main Page with Tabs
// ---------------------------------------------------------------------------

function DocsPageShell({ title, subtitle, sections, defaultOpen, children }: {
  title: string
  subtitle: string
  sections: string[]
  defaultOpen: string
  children: (props: { openSections: Set<string>; toggle: (id: string) => void }) => React.ReactNode
}) {
  const [openSections, setOpenSections] = useState<Set<string>>(new Set([defaultOpen]))

  const toggle = (id: string) => {
    setOpenSections((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const expandAll = () => setOpenSections(new Set(sections))
  const collapseAll = () => setOpenSections(new Set())

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
          <p className="mt-1 text-gray-500">{subtitle}</p>
        </div>
        <div className="flex gap-2">
          <button onClick={expandAll} className="rounded border border-gray-300 px-3 py-1 text-xs text-gray-600 hover:bg-gray-50">Espandi tutto</button>
          <button onClick={collapseAll} className="rounded border border-gray-300 px-3 py-1 text-xs text-gray-600 hover:bg-gray-50">Chiudi tutto</button>
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
        {children({ openSections, toggle })}
      </div>
    </div>
  )
}

export function OperationalDocsPage() {
  return (
    <DocsPageShell
      title="Documentazione Operativa"
      subtitle="Come funziona il sistema di alerting, le regole, e come interpretare i risultati."
      sections={OP_SECTIONS}
      defaultOpen="alert-rules"
    >
      {({ openSections, toggle }) => <OperationalDocs openSections={openSections} toggle={toggle} />}
    </DocsPageShell>
  )
}

export function TechnicalDocsPage() {
  return (
    <DocsPageShell
      title="Documentazione Tecnica"
      subtitle="Architettura, API, database, deploy e configurazione per il team IT."
      sections={TECH_SECTIONS}
      defaultOpen="arch"
    >
      {({ openSections, toggle }) => <TechnicalDocs openSections={openSections} toggle={toggle} />}
    </DocsPageShell>
  )
}

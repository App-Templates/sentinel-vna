import { useState } from 'react'
import {
  ChevronDown, ChevronRight, AlertTriangle, TrendingDown, Activity,
  Layers, Globe, Monitor, Users, Cpu, HelpCircle, Database,
  Network, Shield, Settings, Clock, FolderTree, Code, Container,
  BarChart3, Eye, Zap, ShieldAlert, BookOpen, Target,
} from 'lucide-react'
import { cn } from '../lib/utils'
import { useTranslation } from '../i18n/context'

// ---------------------------------------------------------------------------
// Shared Components
// ---------------------------------------------------------------------------

function Section({
  id, icon: Icon, title, children, open, onToggle,
}: {
  id: string; icon: React.ElementType; title: string; children: React.ReactNode; open: boolean; onToggle: (id: string) => void
}) {
  return (
    <div className="border-b border-slate-200 last:border-b-0">
      <button onClick={() => onToggle(id)} className="flex w-full items-center gap-3 px-4 py-4 text-left transition-colors hover:bg-slate-50">
        <Icon size={20} className="shrink-0 text-blue-600" />
        <span className="flex-1 text-base font-semibold text-slate-900">{title}</span>
        {open ? <ChevronDown size={18} className="text-slate-400" /> : <ChevronRight size={18} className="text-slate-400" />}
      </button>
      {open && <div className="px-4 pb-6 pt-0 pl-11 text-sm leading-relaxed text-slate-700">{children}</div>}
    </div>
  )
}

function Th({ children }: { children: React.ReactNode }) {
  return <th className="border border-slate-200 bg-slate-50 px-3 py-2 text-left text-xs font-semibold uppercase text-slate-600">{children}</th>
}

function Td({ children, className, ...rest }: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return <td className={cn('border border-slate-200 px-3 py-2 text-sm', className)} {...rest}>{children}</td>
}

function Badge({ color, children }: { color: 'red' | 'orange' | 'yellow' | 'blue' | 'green' | 'gray' | 'purple'; children: React.ReactNode }) {
  const colors = {
    red: 'bg-red-100 text-red-800', orange: 'bg-orange-100 text-orange-800',
    yellow: 'bg-yellow-100 text-yellow-800', blue: 'bg-blue-100 text-blue-800',
    green: 'bg-green-100 text-green-800', gray: 'bg-slate-100 text-slate-700',
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

const OP_SECTIONS = ['alert-rules', 'channels', 'severity', 'triage', 'metrics', 'revenue-share', 'comparative', 'leading-indicators', 'cross-channel', 'pipeline', 'contributors', 'geo', 'env', 'multi-metric', 'opt-windows', 'ecpm-patterns', 'hidden-patterns', 'danger-zones', 'driver-guide', 'faq', 'operator-workflow-feedback', 'operator-workflow-assignment', 'operator-workflow-intervention', 'slack-notifications']

function OperationalDocs({ openSections, toggle, t }: { openSections: Set<string>; toggle: (id: string) => void; t: (key: string) => string }) {
  return (
    <>
      {/* ALERT RULES */}
      <Section id="alert-rules" icon={AlertTriangle} title={t('docs.alert-rules')} open={openSections.has('alert-rules')} onToggle={toggle}>
        <p className="mb-4">
          Sentinel monitors Adkaora ad network revenue by comparing current metrics against a
          <strong> historical baseline</strong> (same hour, same weekday, average of the <strong>7 previous weeks</strong>).
          When an anomaly is detected, it generates an alert based on one of seven rules:
        </p>
        <table className="mb-4 w-full border-collapse">
          <thead><tr><Th>Rule</Th><Th>Name</Th><Th>What it detects</Th><Th>When it triggers</Th></tr></thead>
          <tbody>
            <tr>
              <Td><Badge color="red">A1</Badge></Td><Td className="font-medium">Revenue Drop</Td>
              <Td>Sudden revenue drop vs hourly/daily baseline</Td>
              <Td>When revenue delta % exceeds P0/P1/P2 thresholds. Z-score check + off-peak suppression (22-06).</Td>
            </tr>
            <tr>
              <Td><Badge color="orange">A2</Badge></Td><Td className="font-medium">Drift (Regression + 7d MA)</Td>
              <Td>Gradual negative trend detected via linear regression (14-30d) or 7d moving average</Td>
              <Td>Linear regression: slope <strong>&le; -2%/day</strong>, cumulative drop <strong>&ge; -15%</strong>, R² <strong>&ge; 0.5</strong>, p <strong>&lt; 0.05</strong>. Fallback: 7d MA <strong>-8%</strong>.</Td>
            </tr>
            <tr>
              <Td><Badge color="yellow">A3</Badge></Td><Td className="font-medium">Near-Zero</Td>
              <Td>Revenue or coverage near zero</Td>
              <Td>Revenue &lt; <strong>100 EUR</strong> or coverage &lt; <strong>5%</strong> for <strong>3 consecutive</strong> periods.</Td>
            </tr>
            <tr>
              <Td><Badge color="purple">A0</Badge></Td><Td className="font-medium">Data Gap</Td>
              <Td>Missing data beyond configured threshold</Td>
              <Td>Gap &gt; <strong>4 hours</strong> without data. Immediate technical alert, bypasses triage and analysis.</Td>
            </tr>
            <tr>
              <Td><Badge color="purple">A5</Badge></Td><Td className="font-medium">Margin/eCPM Drop</Td>
              <Td>Significant eCPM drop vs baseline</Td>
              <Td>eCPM dropped <strong>&ge; 25%</strong> (P1) or <strong>&ge; 15%</strong> (P2) with min <strong>1000 impressions</strong>. Indicates pricing deterioration.</Td>
            </tr>
            <tr>
              <Td><Badge color="red">A6</Badge></Td><Td className="font-medium">Coverage Zero</Td>
              <Td>Coverage zeroed or near-zero on publisher</Td>
              <Td>Coverage &lt; <strong>0.1%</strong> (threshold 0.001) with min <strong>100 ad requests</strong> for <strong>2 consecutive hours</strong>. Severity always <strong>P1</strong>. Dedicated triage identifies cause: GOOGLE_POLICY, MCM_CONFIG, ADS_TXT, TECHNICAL_ISSUE.</Td>
            </tr>
            <tr>
              <Td><Badge color="orange">A7</Badge></Td><Td className="font-medium">Pricing Rule Error</Td>
              <Td>Coverage drops while CPM spikes (inverse correlation)</Td>
              <Td>Correlation score <strong>&le; -0.7</strong> between coverage and CPM with min <strong>500 impressions</strong>. Severity always <strong>P1</strong>.</Td>
            </tr>
            <tr>
              <Td><Badge color="red">A8</Badge></Td><Td className="font-medium">Gross Margin Alert</Td>
              <Td>Gross margin below threshold — revenue_net = revenue_gross x share_rate diverges significantly</Td>
              <Td>gross_margin_pct below configured threshold per publisher. Severity always <strong>P1</strong>. Requires per-publisher config in <code className="rounded bg-slate-100 px-1 text-xs">revenue_share.yaml</code>.</Td>
            </tr>
          </tbody>
        </table>
        <div className="rounded-lg bg-blue-50 p-3">
          <p className="text-sm text-blue-800">
            <strong>Why 8 rules?</strong> A0 catches technical issues (missing data). A1 catches sudden drops. A2 slow erosions (-2%/day = -14%/week). A3 silent deaths (publishers that stop generating revenue). A5 detects pricing deterioration (eCPM). A6 detects demand/config blocks (coverage zero). A7 detects floor pricing errors (coverage vs CPM inverse). A8 monitors gross margin to identify revenue share anomalies.
          </p>
        </div>
      </Section>

      {/* CHANNELS */}
      <Section id="channels" icon={Network} title={t('docs.channels')} open={openSections.has('channels')} onToggle={toggle}>
        <p className="mb-4">
          Sentinel monitors <strong>7 monetization channels</strong> separately. Each channel represents a different path
          through which impressions are sold. Monitoring them individually allows identifying specific issues
          without being masked by aggregates.
        </p>
        <table className="mb-4 w-full border-collapse">
          <thead><tr><Th>Channel</Th><Th>Description</Th><Th>Notes</Th></tr></thead>
          <tbody>
            <tr><Td><Badge color="blue">GOOGLE_ADEX</Badge></Td><Td>Direct demand from Google Ad Exchange / AdSense</Td><Td>Main channel by volume. Only one with hourly scheduling.</Td></tr>
            <tr><Td><Badge color="green">OPEN_BIDDING</Badge></Td><Td>Third-party SSPs (Amazon, Index Exchange...) via Open Bidding auction</Td><Td>Demand diversification. Higher auction latency.</Td></tr>
            <tr><Td><Badge color="purple">HB_MAGNITE</Badge></Td><Td>Header Bidding via Magnite (ex-Rubicon)</Td><Td>Premium SSP, strong on video.</Td></tr>
            <tr><Td><Badge color="purple">HB_PUBMATIC</Badge></Td><Td>Header Bidding via PubMatic</Td><Td>Strong on display and mobile.</Td></tr>
            <tr><Td><Badge color="orange">TAM</Badge></Td><Td>Transparent Ad Marketplace (Amazon)</Td><Td>Server-side bidding, minimal latency.</Td></tr>
            <tr><Td><Badge color="red">DIRECT</Badge></Td><Td>Campaigns sold directly by the commercial team</Td><Td>Guaranteed revenue, can divert traffic from Open Market.</Td></tr>
            <tr><Td><Badge color="gray">DEAL</Badge></Td><Td>Preferred Deal and Private Marketplace (PMP)</Td><Td>Preferential agreements with specific advertisers.</Td></tr>
          </tbody>
        </table>
        <div className="rounded-lg bg-amber-50 p-3">
          <p className="text-sm text-amber-800">
            <strong>DIRECT campaign case:</strong> When a direct campaign is activated, it absorbs traffic that would normally
            go to Open Market (GOOGLE_ADEX, OPEN_BIDDING, HB_*). The drop on these channels is not an anomaly but an
            expected effect. The <strong>cross-channel detection</strong> system automatically detects this pattern
            (DIRECT increasing + Open Market decreasing) and reduces false positives.
          </p>
        </div>
      </Section>

      {/* SEVERITY */}
      <Section id="severity" icon={TrendingDown} title={t('docs.severity')} open={openSections.has('severity')} onToggle={toggle}>
        <p className="mb-4">Severity determines priority and response times. Assigned by the Anomaly Detector based on delta % and temporal context.</p>
        <table className="mb-4 w-full border-collapse">
          <thead><tr><Th>Severity</Th><Th>Threshold</Th><Th>Window</Th><Th>Meaning</Th><Th>Action</Th></tr></thead>
          <tbody>
            <tr><Td><Badge color="red">P0</Badge></Td><Td className="font-mono">&ge; -15%</Td><Td>2h consecutive</Td><Td>Severe drop, significant impact on daily revenue</Td><Td>Investigate within 30 min</Td></tr>
            <tr><Td><Badge color="orange">P1</Badge></Td><Td className="font-mono">&ge; -10%</Td><Td>2h consecutive</Td><Td>Important drop, significant impact if it persists</Td><Td>Investigate within 2 hours</Td></tr>
            <tr><Td><Badge color="yellow">P2</Badge></Td><Td className="font-mono">&ge; -5%</Td><Td>4h consecutive</Td><Td>Moderate drop, possibly physiological</Td><Td>Monitor, investigate if it persists</Td></tr>
            <tr><Td><Badge color="blue">P2-WATCH</Badge></Td><Td className="font-mono">-15%</Td><Td>2h consecutive</Td><Td>Attention threshold - requires monitoring</Td><Td>Observe, no immediate action</Td></tr>
          </tbody>
        </table>
        <p className="mb-3 mt-4"><strong>Dual threshold system (Phase 1):</strong> A1/A2 rules use dual thresholds: operational (-30% for yesterday, standard P0/P1/P2 for baseline) and attention (-15%). Alerts below operational threshold but above attention threshold generate P2-WATCH.</p>
        <p className="mb-3"><strong>A8 (Gross Margin):</strong> Severity always <strong>P1</strong> — a gross margin anomaly indicates a revenue share problem requiring rapid intervention.</p>
        <p className="mb-3"><strong>P2-WATCH for Leading Indicators:</strong> When CTR or Viewability drop <strong>&ge; 15%</strong> vs baseline, the system generates a <Badge color="blue">P2-WATCH</Badge> alert. These are early warning signals: a CTR/Viewability drop often precedes a revenue drop by 24-48h.</p>
        <div className="space-y-2">
          <p><strong>Contextual adjustments:</strong></p>
          <ul className="list-disc space-y-1 pl-5">
            <li><strong>Off-peak (22-06):</strong> thresholds relaxed 1.5x. A -15% overnight becomes P1.</li>
            <li><strong>Weekend:</strong> thresholds relaxed 1.2x.</li>
            <li><strong>Z-score &lt; 1.5 + off-peak:</strong> alert suppressed (probable false positive).</li>
            <li><strong>Dual thresholds:</strong> Comparative alerting applies dual thresholds to distinguish operational urgencies from monitoring signals.</li>
          </ul>
        </div>
      </Section>

      {/* TRIAGE */}
      <Section id="triage" icon={Activity} title={t('docs.triage')} open={openSections.has('triage')} onToggle={toggle}>
        <p className="mb-4">Triage classifies the <strong>primary cause</strong> by comparing changes in ad requests and coverage.</p>
        <table className="mb-4 w-full border-collapse">
          <thead><tr><Th>Classification</Th><Th>Condition</Th><Th>Meaning</Th><Th>Where to investigate</Th></tr></thead>
          <tbody>
            <tr><Td><Badge color="blue">TRAFFIC_DRIVEN</Badge></Td><Td className="font-mono">ad_requests &le; -10%<br/>coverage &gt; -10%</Td><Td>Traffic dropped, fill rate stable</Td><Td>Publisher, traffic sources, tag</Td></tr>
            <tr><Td><Badge color="green">COVERAGE_DRIVEN</Badge></Td><Td className="font-mono">coverage &le; -10%<br/>ad_requests &gt; -10%</Td><Td>Traffic stable, fewer monetized impressions</Td><Td>Demand partner, floor price, bid</Td></tr>
            <tr><Td><Badge color="orange">MIXED</Badge></Td><Td className="font-mono">both &le; -10%</Td><Td>Both traffic and coverage dropping</Td><Td>Platform, ad server, market</Td></tr>
            <tr><Td><Badge color="gray">REVENUE_ONLY</Badge></Td><Td className="font-mono">both &gt; -10%</Td><Td>Revenue drops without visible drivers</Td><Td>CPM, eCPM, inventory mix, demand</Td></tr>
            <tr><Td><Badge color="purple">MARGIN_DRIVEN</Badge></Td><Td className="font-mono">gross_margin_pct anomalous</Td><Td>Net revenue drops due to share rate or gross revenue change</Td><Td>Revenue share config, publisher contracts, revenue_share.yaml</Td></tr>
          </tbody>
        </table>
        <div className="rounded-lg bg-blue-50 p-3">
          <p className="text-sm text-blue-800"><strong>-10% threshold:</strong> below 10% the signal is indistinguishable from noise. Symmetric to avoid bias.</p>
        </div>
        <div className="mt-4">
          <p className="mb-2"><strong>Coverage-Zero Triage (A6):</strong></p>
          <p className="mb-3">When an A6 alert is generated, the standard triage (TRAFFIC/COVERAGE/MIXED/REVENUE_ONLY) does NOT apply. The system uses a dedicated triage that classifies as:</p>
          <ul className="list-disc space-y-1 pl-5">
            <li><strong>GOOGLE_POLICY:</strong> Sudden zero, stable ad requests → Google policy violation</li>
            <li><strong>MCM_CONFIG:</strong> Gradual zero, stable ad requests → MCM configuration issue</li>
            <li><strong>ADS_TXT:</strong> Zero with ad request variation + historically high coverage → ads.txt issue</li>
            <li><strong>TECHNICAL_ISSUE:</strong> Fallback for technical edge cases</li>
          </ul>
        </div>
      </Section>

      {/* METRICS */}
      <Section id="metrics" icon={Layers} title={t('docs.metrics')} open={openSections.has('metrics')} onToggle={toggle}>
        <div className="space-y-4">
          <div>
            <h4 className="font-semibold text-slate-900">Ad Requests (Supply)</h4>
            <p>Available impressions. If it drops: fewer page views or tags not loaded. <code className="rounded bg-slate-100 px-1 text-xs">SUM(ad_requests)</code></p>
          </div>
          <div>
            <h4 className="font-semibold text-slate-900">Coverage (Fill Rate)</h4>
            <p>% of ad requests with an ad served. <code className="rounded bg-slate-100 px-1 text-xs">impressions_filled / ad_requests</code>. If it drops: demand struggling.</p>
          </div>
          <div>
            <h4 className="font-semibold text-slate-900">eCPM</h4>
            <p>Average revenue per 1000 impressions. <code className="rounded bg-slate-100 px-1 text-xs">(revenue / impressions) * 1000</code>. Monetization quality indicator.</p>
          </div>
          <div>
            <h4 className="font-semibold text-slate-900">RPM (Revenue Per Mille) <Badge color="purple">v1.2</Badge></h4>
            <p>Revenue per 1000 pageviews. <code className="rounded bg-slate-100 px-1 text-xs">revenue / pageviews * 1000</code>. Primary KPI for publishers: measures overall monetization efficiency considering all traffic, not just served impressions. More reliable than eCPM because it is not affected by supply compression.</p>
          </div>
          <div>
            <h4 className="font-semibold text-slate-900">CTR (Click-Through Rate) <Badge color="purple">v1.2</Badge></h4>
            <p>% of impressions clicked. <code className="rounded bg-slate-100 px-1 text-xs">clicks / impressions * 100</code>. Leading indicator: a CTR drop often anticipates a revenue drop by 24-48h. Attention threshold: <strong>-15%</strong> vs baseline.</p>
          </div>
          <div>
            <h4 className="font-semibold text-slate-900">Viewability <Badge color="purple">v1.2</Badge></h4>
            <p>% of impressions actually viewed (IAB standard: 50% pixels visible for 1 second). <code className="rounded bg-slate-100 px-1 text-xs">viewable_impressions / measurable_impressions * 100</code>. Leading indicator: low viewability reduces inventory value for advertisers. Attention threshold: <strong>-15%</strong> vs baseline.</p>
          </div>
          <div>
            <h4 className="font-semibold text-slate-900">Gross Margin % <Badge color="purple">v1.2</Badge></h4>
            <p>Gross margin percentage. <code className="rounded bg-slate-100 px-1 text-xs">(revenue_gross - revenue_net) / revenue_gross * 100</code>. Monitored by A8. Depends on share_rate configured per publisher in <code className="rounded bg-slate-100 px-1 text-xs">revenue_share.yaml</code>.</p>
          </div>
          <div>
            <h4 className="font-semibold text-slate-900">Revenue</h4>
            <p>Product: <code className="rounded bg-slate-100 px-1 text-xs">revenue = ad_requests x coverage x eCPM / 1000</code>. This is why triage decomposes into components.</p>
          </div>
        </div>
      </Section>

      {/* REVENUE SHARE */}
      <Section id="revenue-share" icon={Target} title={t('docs.revenue-share')} open={openSections.has('revenue-share')} onToggle={toggle}>
        <p className="mb-4">
          The system distinguishes between <strong>gross revenue</strong> (total generated by inventory) and <strong>net revenue</strong> (publisher share after the intermediation fee).
        </p>
        <div className="space-y-3">
          <div>
            <h4 className="font-semibold text-slate-900">Formula</h4>
            <p><code className="rounded bg-slate-100 px-1 text-xs">revenue_net = revenue_gross x share_rate</code></p>
            <p className="mt-1">The share_rate is the percentage belonging to the publisher (default: <strong>60%</strong>, i.e. 0.60). The remaining 40% is the Adkaora fee.</p>
          </div>
          <div>
            <h4 className="font-semibold text-slate-900">Gross Margin %</h4>
            <p><code className="rounded bg-slate-100 px-1 text-xs">gross_margin_pct = (revenue_gross - revenue_net) / revenue_gross * 100</code></p>
            <p className="mt-1">With share_rate 60%, the expected gross_margin_pct is <strong>40%</strong>. Significant deviations indicate anomalies in calculation or configuration.</p>
          </div>
          <div>
            <h4 className="font-semibold text-slate-900">Per-Publisher Configuration</h4>
            <p>The share_rate can vary per publisher (different contracts). Configured in <code className="rounded bg-slate-100 px-1 text-xs">config/revenue_share.yaml</code> with fallback to global default.</p>
          </div>
        </div>
        <div className="mt-4 rounded-lg bg-blue-50 p-3">
          <p className="text-sm text-blue-800">
            <strong>Alert A8:</strong> When gross_margin_pct deviates significantly from the expected value for a publisher, the system generates an A8 alert (severity P1). Typical causes: share_rate configuration error, revenue_gross data anomaly from GAM, or contractual renegotiation not updated in config.
          </p>
        </div>
      </Section>

      {/* COMPARATIVE ALERTING */}
      <Section id="comparative" icon={TrendingDown} title={t('docs.comparative')} open={openSections.has('comparative')} onToggle={toggle}>
        <p className="mb-4">
          Phase 1 introduced comparisons aligned with the TAM&amp;Yield team operational practice:
        </p>
        <div className="space-y-3">
          <div>
            <h4 className="font-semibold text-slate-900">Yesterday comparison</h4>
            <p>Hourly revenue compared to same hours yesterday. Alert when deviation <strong>&ge; 30%</strong> (P0/P1/P2 operational) or <strong>&ge; 15%</strong> (P2-WATCH attention).</p>
          </div>
          <div>
            <h4 className="font-semibold text-slate-900">14-day moving average</h4>
            <p>Revenue compared against last 14 days average (same-weekday pattern). Detects divergences from recent trend.</p>
          </div>
          <div>
            <h4 className="font-semibold text-slate-900">Display</h4>
            <p>Dedicated sections in alert detail when data is available (dynamic steps 8-9).</p>
          </div>
        </div>
      </Section>

      {/* LEADING INDICATORS */}
      <Section id="leading-indicators" icon={Eye} title={t('docs.leading-indicators')} open={openSections.has('leading-indicators')} onToggle={toggle}>
        <p className="mb-4">
          CTR and Viewability are <strong>early warning signals</strong> of revenue drops. Deterioration of these metrics
          typically precedes a revenue drop by <strong>24-48 hours</strong>, giving the team time to investigate before the impact becomes visible.
        </p>
        <div className="space-y-3">
          <div>
            <h4 className="font-semibold text-slate-900">CTR as early warning</h4>
            <p>A CTR drop indicates users are engaging less with ads. Advertisers notice and reduce bids, causing a deferred revenue drop. Threshold: <strong>-15%</strong> vs baseline triggers <Badge color="blue">P2-WATCH</Badge>.</p>
          </div>
          <div>
            <h4 className="font-semibold text-slate-900">Viewability as early warning</h4>
            <p>Low viewability indicates layout or ad placement issues. Advertisers penalize non-viewable inventory by reducing bids. Threshold: <strong>-15%</strong> vs baseline triggers <Badge color="blue">P2-WATCH</Badge>.</p>
          </div>
          <div>
            <h4 className="font-semibold text-slate-900">Severity P2-WATCH</h4>
            <p>Leading indicator alerts are always <Badge color="blue">P2-WATCH</Badge>: they require monitoring but not immediate action. If the revenue drop materializes, the alert will be escalated to A1 with appropriate severity.</p>
          </div>
        </div>
        <div className="mt-4 rounded-lg bg-amber-50 p-3">
          <p className="text-sm text-amber-800">
            <strong>Why -15%?</strong> Threshold calibrated to balance sensitivity and false positives. CTR and Viewability have high daily variance — below 15% the signal is indistinguishable from noise.
          </p>
        </div>
      </Section>

      {/* CROSS-CHANNEL DETECTION */}
      <Section id="cross-channel" icon={Zap} title={t('docs.cross-channel')} open={openSections.has('cross-channel')} onToggle={toggle}>
        <p className="mb-4">
          The system automatically detects inverse correlations between channels to reduce false positives. The most common case:
          a <strong>DIRECT campaign</strong> absorbing traffic normally served by Open Market.
        </p>
        <div className="space-y-3">
          <div>
            <h4 className="font-semibold text-slate-900">Pattern: DIRECT growing + Open Market dropping</h4>
            <p>When the DIRECT channel shows a significant increase in the same hours that GOOGLE_ADEX, OPEN_BIDDING or HB_* are dropping, the system identifies a probable active direct campaign. The Open Market alert is annotated with cross-channel context.</p>
          </div>
          <div>
            <h4 className="font-semibold text-slate-900">False positive reduction</h4>
            <p>Without cross-channel detection, every Open Market drop would generate an A1 alert. With detection active, the system:</p>
            <ul className="mt-1 list-disc space-y-1 pl-5">
              <li>Annotates the alert with context <code className="rounded bg-slate-100 px-1 text-xs">cross_channel: DIRECT_CAMPAIGN_DETECTED</code></li>
              <li>Reduces severity (e.g. from P1 to P2-WATCH)</li>
              <li>Adds correlation detail with DIRECT in findings</li>
            </ul>
          </div>
          <div>
            <h4 className="font-semibold text-slate-900">Configuration</h4>
            <p>Enabled in <code className="rounded bg-slate-100 px-1 text-xs">config/alerting_rules.yaml</code> section <code className="rounded bg-slate-100 px-1 text-xs">cross_channel_detection</code>. Correlation threshold and channels to compare are configurable.</p>
          </div>
        </div>
      </Section>

      {/* PIPELINE */}
      <Section id="pipeline" icon={Cpu} title={t('docs.pipeline')} open={openSections.has('pipeline')} onToggle={toggle}>
        <p className="mb-4">Pipeline of 11 specialized agents that analyze the anomaly from different angles:</p>
        <div className="space-y-3">
          {[
            { n: 1, name: 'Orchestrator', d: 'Prepares context: channel, timestamp, trigger type.' },
            { n: 2, name: 'Data Fetcher', d: 'Fetches data (Athena → GAM → Parquet fallback chain), calculates 7-week baseline and delta. Excludes periods with registered manual interventions. Cache with TTL.' },
            { n: 3, name: 'Data Validator', d: 'Verifies data quality: completeness, consistency, outliers. If missing data > 4h, generates A0 alert.' },
            { n: 4, name: 'Anomaly Detector', d: 'Applies A1/A2/A3 rules with consecutive hour check, Z-scores (sample std N-1), assigns severity. A0 bypasses this step. Optional: Claude Haiku.' },
            { n: 5, name: 'Triage Classifier', d: 'Classifies cause: TRAFFIC/COVERAGE/MIXED/REVENUE_ONLY.' },
            { n: '6a', name: 'Contributor Analyzer', d: 'Top publishers by drop share. Optional: Claude Haiku for name normalization.' },
            { n: '6b', name: 'Geo Analyzer', d: 'Breaks down by geo cluster (ITA/ES/OTHER).' },
            { n: '6c', name: 'Environment Splitter', d: 'Breaks down by WEB/AMP/APP. Detects AMP drift.' },
            { n: 7, name: 'Insight Generator', d: 'Correlates results, generates ordered findings. Optional: Claude Sonnet.' },
            { n: 8, name: 'Report Builder', d: 'Composes final structured report.' },
            { n: 9, name: 'Notifier', d: 'Sends immediate Slack notifications (P0) or queues for daily digest (P1/P2/P2-WATCH). Uses severity-based Block Kit templates. Retry with exponential backoff for P0. Async via ThreadPoolExecutor (LIVE mode only, not backtest).' },
          ].map((a) => (
            <div key={a.n} className="flex gap-3">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700">{a.n}</div>
              <div><span className="font-semibold text-slate-900">{a.name}</span><span className="text-slate-400"> — </span>{a.d}</div>
            </div>
          ))}
        </div>
        <div className="mt-4 rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
          6a/6b/6c run in parallel (different state keys, no dependencies). Reduces pipeline latency. Note: A0 alerts (data gap) bypass triage and analysis, jumping directly to report_builder.
        </div>
        <div className="mt-4 rounded-lg bg-blue-50 p-3">
          <p className="text-sm text-blue-800">
            <strong>Operator Feedback Loop (Phase 3):</strong> After an alert, operators can provide feedback
            (REAL vs FALSE_POSITIVE variants), assign to colleagues, and log manual interventions. Interventions
            are excluded from the future baseline to prevent recurring alerts on known variations.
          </p>
        </div>
        <div className="mt-4 rounded-lg bg-yellow-50 p-3">
          <p className="text-sm text-yellow-800">
            <strong>Backtest Notifications:</strong> During backtest (BACKTEST mode), the notifier agent is completely bypassed. Slack notifications are sent ONLY in LIVE mode.
          </p>
        </div>
      </Section>

      {/* CONTRIBUTORS */}
      <Section id="contributors" icon={Users} title={t('docs.contributors')} open={openSections.has('contributors')} onToggle={toggle}>
        <div className="space-y-3">
          <div><h4 className="font-semibold text-slate-900">Quota of Drop</h4><p><code className="rounded bg-slate-100 px-1 text-xs">(delta_publisher / delta_total) x 100</code>. Drop -10K EUR, publisher -3K = quota 30%.</p></div>
          <div><h4 className="font-semibold text-slate-900">Filters</h4><p>Max <strong>15 publishers</strong>, minimum quota <strong>1%</strong>.</p></div>
          <div><h4 className="font-semibold text-slate-900">Concentration</h4><p>Top 3 &gt; 60%: <strong>concentrated</strong> problem (targeted action). Distributed: <strong>systemic</strong>.</p></div>
          <div>
            <h4 className="font-semibold text-slate-900">Metrics breakdown per contributor <Badge color="purple">v1.2</Badge></h4>
            <p>Each contributor now includes a breakdown of <strong>RPM</strong>, <strong>CTR</strong> and <strong>Viewability</strong> in addition to revenue and eCPM. Helps understand if a publisher's drop is due to engagement deterioration (CTR), visibility (Viewability) or overall efficiency (RPM).</p>
          </div>
          <div>
            <h4 className="font-semibold text-slate-900">Channel breakdown <Badge color="purple">v1.2</Badge></h4>
            <p>Contributors also show channel distribution (GOOGLE_ADEX, OPEN_BIDDING, HB_*, DIRECT, DEAL). Useful to identify if a publisher's drop is concentrated on a specific channel or distributed.</p>
          </div>
        </div>
      </Section>

      {/* GEO */}
      <Section id="geo" icon={Globe} title={t('docs.geo')} open={openSections.has('geo')} onToggle={toggle}>
        <table className="mb-4 w-full border-collapse">
          <thead><tr><Th>Cluster</Th><Th>Countries</Th><Th>Notes</Th></tr></thead>
          <tbody>
            <tr><Td><Badge color="green">ITA</Badge></Td><Td>Italy</Td><Td>Main market</Td></tr>
            <tr><Td><Badge color="orange">ES</Badge></Td><Td>Spain</Td><Td>Second market (Vocento, Prensa Iberica...)</Td></tr>
            <tr><Td><Badge color="yellow">LATAM</Badge></Td><Td>BR, MX, AR, CO, CL, PE</Td><Td>Latin America — growing market <Badge color="purple">v1.2</Badge></Td></tr>
            <tr><Td><Badge color="purple">PT</Badge></Td><Td>Portugal</Td><Td>Iberian market separate from Spain <Badge color="purple">v1.2</Badge></Td></tr>
            <tr><Td><Badge color="blue">OTHER</Badge></Td><Td>US, UK, FR, DE + rest of world</Td><Td>Minor markets and international traffic</Td></tr>
          </tbody>
        </table>
        <p>Status: <Badge color="red">declining</Badge> (&le; -5%), <Badge color="gray">stable</Badge> (-5% / +2%), <Badge color="green">growing</Badge> (&ge; +2%).</p>
      </Section>

      {/* ENVIRONMENT */}
      <Section id="env" icon={Monitor} title={t('docs.env')} open={openSections.has('env')} onToggle={toggle}>
        <table className="mb-4 w-full border-collapse">
          <thead><tr><Th>Environment</Th><Th>Description</Th></tr></thead>
          <tbody>
            <tr><Td className="font-medium">WEB</Td><Td>Desktop + standard mobile. Highest volume.</Td></tr>
            <tr><Td className="font-medium">AMP</Td><Td>Accelerated Mobile Pages. Declining (deprecation). Under special watch.</Td></tr>
            <tr><Td className="font-medium">APP</Td><Td>In-app (mobile SDK). Different seasonality.</Td></tr>
            <tr><Td className="font-medium">UNKNOWN <Badge color="purple">v1.2</Badge></Td><Td>Unclassified environment. Traffic not fitting WEB/AMP/APP (e.g. new SDKs, crawlers, unidentified traffic). Monitored to detect classification anomalies.</Td></tr>
          </tbody>
        </table>
        <p><strong>AMP Drift:</strong> detected when AMP drops &ge; -8% and at least 5pp worse than WEB or APP.</p>
      </Section>

      {/* MULTI-METRIC INTELLIGENCE */}
      <Section id="multi-metric" icon={BarChart3} title={t('docs.multi-metric')} open={openSections.has('multi-metric')} onToggle={toggle}>
        <p className="mb-4">
          The publisher detail page integrates <strong>4 levels of analysis</strong> that go beyond simple eCPM
          to provide a complete picture of a publisher's health.
        </p>
        <div className="space-y-3">
          <div className="flex gap-3">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700">1</div>
            <div><span className="font-semibold text-slate-900">eCPM Optimization Windows</span> — Seasonal periods with eCPM above or below average. RAISE/LOWER badge + causal driver.</div>
          </div>
          <div className="flex gap-3">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700">2</div>
            <div><span className="font-semibold text-slate-900">Historical eCPM Patterns</span> — Recurring patterns occurring in the same period in both years (2024 and 2025).</div>
          </div>
          <div className="flex gap-3">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700">3</div>
            <div><span className="font-semibold text-slate-900">Hidden Volume Patterns</span> — Revenue/impressions changes that eCPM cannot capture because components drop proportionally.</div>
          </div>
          <div className="flex gap-3">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700">4</div>
            <div><span className="font-semibold text-slate-900">Risk Zones</span> — Periods where eCPM and coverage drop together, indicating real demand weakness.</div>
          </div>
        </div>
        <div className="mt-4 rounded-lg bg-blue-50 p-3">
          <p className="text-sm text-blue-800">
            <strong>Why 4 levels?</strong> eCPM alone can be misleading: it can rise while revenue drops
            (supply compression), or stay flat while the publisher loses thousands of euros (hidden patterns).
            Multi-metric analysis reveals what is really happening.
          </p>
        </div>
      </Section>

      {/* OPTIMIZATION WINDOWS */}
      <Section id="opt-windows" icon={Target} title={t('docs.opt-windows')} open={openSections.has('opt-windows')} onToggle={toggle}>
        <p className="mb-4">
          Optimization windows identify <strong>seasonal periods</strong> (Easter, Summer, Black Friday, Christmas, etc.)
          where eCPM deviates significantly from the publisher's annual average.
        </p>

        <h4 className="mb-2 font-semibold text-slate-900">How to read them</h4>
        <div className="space-y-3 mb-4">
          <div>
            <p><Badge color="green">RAISE</Badge> — eCPM is <strong>above</strong> average in the period. Floor price optimization opportunity.</p>
          </div>
          <div>
            <p><Badge color="orange">LOWER</Badge> — eCPM is <strong>below</strong> average in the period. Consider reducing floor to maintain fill rate.</p>
          </div>
          <div>
            <p><strong>Driver badge:</strong> indicates the <strong>cause</strong> of the change (see Driver Guide section). Watch for orange badges with triangle: potentially misleading signal.</p>
          </div>
        </div>

        <h4 className="mb-2 font-semibold text-slate-900">% Match (Reliability)</h4>
        <p className="mb-4">
          Measures how <strong>reliable and precise</strong> the pattern is for making operational decisions.
          It is not a year-over-year comparison, but a composite score based on: internal consistency of weekly data (35%),
          cross-year recurrence (30%), magnitude similarity (20%), sample size (15%).
          Higher = more reliable pattern for decision-making.
        </p>

        <h4 className="mb-2 font-semibold text-slate-900">Additional metrics</h4>
        <p className="mb-2">Below each optimization window you find:</p>
        <ul className="list-disc space-y-1 pl-5">
          <li><strong>Ad Requests:</strong> % change of ad requests vs average</li>
          <li><strong>Coverage:</strong> % change of fill rate</li>
          <li><strong>Impressions:</strong> % change of served impressions</li>
          <li><strong>Revenue:</strong> % change of revenue</li>
        </ul>
        <div className="mt-4 rounded-lg bg-amber-50 p-3">
          <p className="text-sm text-amber-800">
            <strong>Tip:</strong> always look at the driver alongside the direction. A rising eCPM with
            "Supply Squeeze" driver (orange) is NOT good news — it means inventory is contracting.
          </p>
        </div>
      </Section>

      {/* ECPM PATTERNS */}
      <Section id="ecpm-patterns" icon={Activity} title={t('docs.ecpm-patterns')} open={openSections.has('ecpm-patterns')} onToggle={toggle}>
        <p className="mb-4">
          Historical patterns identify <strong>recurring</strong> eCPM variations that occur in the
          <strong> same period</strong> in both analyzed years (2024 and 2025).
        </p>

        <h4 className="mb-2 font-semibold text-slate-900">How to read them</h4>
        <ul className="list-disc space-y-2 pl-5 mb-4">
          <li><strong>Direct comparison:</strong> eCPM 2024 vs eCPM 2025 in the same period. Shows if the pattern repeats and with what intensity.</li>
          <li><strong>% Match (Reliability):</strong> how reliable the pattern is. Calculated as Pearson correlation of weekly delta% — measures signal consistency and repeatability.</li>
          <li><strong>Driver:</strong> classifies the underlying cause of the change.</li>
        </ul>

        <h4 className="mb-2 font-semibold text-slate-900">When to act</h4>
        <div className="space-y-2">
          <p>The most <strong>reliable</strong> patterns for decision-making are those that combine:</p>
          <ul className="list-disc space-y-1 pl-5">
            <li><strong>High % match</strong> (the pattern is reliable and repeats faithfully)</li>
            <li><strong>Driver "Demand"</strong> (green) — indicates real ad demand, not statistical artifacts</li>
          </ul>
          <p className="mt-2">Patterns with low % match or orange driver require caution: the signal may not repeat.</p>
        </div>
      </Section>

      {/* HIDDEN PATTERNS */}
      <Section id="hidden-patterns" icon={Eye} title={t('docs.hidden-patterns')} open={openSections.has('hidden-patterns')} onToggle={toggle}>
        <p className="mb-4">
          Hidden volume patterns detect <strong>revenue and impressions</strong> variations that eCPM
          <strong> cannot capture</strong>.
        </p>

        <h4 className="mb-2 font-semibold text-slate-900">Why they exist</h4>
        <p className="mb-4">
          eCPM is a ratio: <code className="rounded bg-slate-100 px-1 text-xs">revenue / impressions * 1000</code>.
          When revenue and impressions drop <strong>proportionally</strong> (e.g. both -20%), eCPM stays flat.
          The publisher is losing money, but looking only at eCPM you would not see it.
        </p>

        <h4 className="mb-2 font-semibold text-slate-900">How to read them</h4>
        <ul className="list-disc space-y-2 pl-5 mb-4">
          <li><strong>"eCPM during period":</strong> shows what eCPM does during the pattern. If it says <Badge color="gray">FLAT</Badge>, the pattern is truly hidden — eCPM does not detect it.</li>
          <li><strong>"Impact":</strong> the value in <strong>EUR/week</strong> quantifies the real economic effect of the pattern.</li>
          <li><strong>% Match (Reliability):</strong> each pattern shows a % match indicating signal reliability, based on: directional consistency between the two years (40%), magnitude similarity (30%), sample size (15%), and eCPM masking degree (15%).</li>
        </ul>

        <div className="rounded-lg bg-amber-50 p-3">
          <p className="text-sm text-amber-800">
            <strong>Practical example:</strong> A publisher with stable eCPM at 2.50 EUR but revenue dropping from 5,000 to 3,000 EUR/week.
            eCPM does not move because impressions drop proportionally. The hidden pattern detects and quantifies
            the impact: -2,000 EUR/week.
          </p>
        </div>
      </Section>

      {/* DANGER ZONES */}
      <Section id="danger-zones" icon={ShieldAlert} title={t('docs.danger-zones')} open={openSections.has('danger-zones')} onToggle={toggle}>
        <p className="mb-4">
          Risk zones identify periods where <strong>both eCPM and coverage drop together</strong>.
          This is the most concerning signal in multi-metric analysis.
        </p>

        <h4 className="mb-2 font-semibold text-slate-900">Why they are dangerous</h4>
        <p className="mb-4">
          When eCPM drops alone, it can be a seasonal effect or a volume increase (more impressions at a
          slightly lower price). But when <strong>coverage also drops</strong>, it means ad demand
          is in real trouble: fewer available ads AND at lower prices.
        </p>

        <h4 className="mb-2 font-semibold text-slate-900">Severity levels</h4>
        <table className="mb-4 w-full border-collapse">
          <thead><tr><Th>Severity</Th><Th>Condition</Th><Th>Meaning</Th></tr></thead>
          <tbody>
            <tr><Td><Badge color="red">HIGH</Badge></Td><Td className="font-mono">eCPM &lt; -15% E coverage &lt; -15%</Td><Td>Severe demand collapse. Immediate action required.</Td></tr>
            <tr><Td><Badge color="orange">MEDIUM</Badge></Td><Td className="font-mono">eCPM &lt; -5% E coverage &lt; -5%</Td><Td>Significant demand weakness. Monitor closely.</Td></tr>
          </tbody>
        </table>

        <h4 className="mb-2 font-semibold text-slate-900">% Match (Reliability)</h4>
        <p className="mb-4">
          Each zone shows a % match indicating the strength of evidence, based on: drop severity (35%),
          dual eCPM+coverage confirmation (30%), sample size (20%), and triple confirmation with ad requests (15%).
        </p>

        <h4 className="mb-2 font-semibold text-slate-900">How to respond</h4>
        <ul className="list-disc space-y-1 pl-5">
          <li>Check if <strong>competitors</strong> have better offers for the same advertisers</li>
          <li><strong>Contact key advertisers</strong> to understand if they have reduced budgets</li>
          <li>Consider reducing <strong>floor prices</strong> to avoid losing further impressions</li>
          <li>Check if the problem is <strong>publisher-specific</strong> or market-wide (compare with other publishers in the same geo)</li>
        </ul>

        <div className="mt-4 rounded-lg bg-red-50 p-3">
          <p className="text-sm text-red-800">
            <strong>Golden rule:</strong> Risk Zones ALWAYS require attention. Unlike other patterns that
            can be seasonal or physiological, the dual eCPM + coverage drop indicates real structural demand weakness.
          </p>
        </div>
      </Section>

      {/* DRIVER GUIDE */}
      <Section id="driver-guide" icon={BookOpen} title={t('docs.driver-guide')} open={openSections.has('driver-guide')} onToggle={toggle}>
        <p className="mb-4">
          The driver classifies the <strong>underlying cause</strong> of an eCPM change. Every optimization window
          and recurring pattern has an associated driver.
        </p>
        <table className="mb-4 w-full border-collapse">
          <thead><tr><Th>Driver</Th><Th>Meaning</Th><Th>Recommended Action</Th></tr></thead>
          <tbody>
            <tr>
              <Td><Badge color="green">Demand</Badge></Td>
              <Td>Real ad demand increasing. Ad requests and coverage stable or growing.</Td>
              <Td>Optimize floor price, now is the right time. Genuine and reliable signal.</Td>
            </tr>
            <tr>
              <Td><Badge color="orange">Supply Squeeze</Badge></Td>
              <Td>eCPM rising because inventory is contracting (ad requests dropping &gt; 5%).</Td>
              <Td><strong>DO NOT raise floors</strong> — the signal is misleading. High eCPM hides a volume loss.</Td>
            </tr>
            <tr>
              <Td><Badge color="orange">Fill Effect</Badge></Td>
              <Td>eCPM rising because only premium impressions are being served (coverage dropping &gt; 5%).</Td>
              <Td>Check why coverage is dropping. Unit price rises but served volume drops.</Td>
            </tr>
            <tr>
              <Td><Badge color="blue">Volume</Badge></Td>
              <Td>eCPM dropping due to higher impression volume (&gt; 5%).</Td>
              <Td>Check total revenue — it may still grow despite the lower eCPM.</Td>
            </tr>
            <tr>
              <Td><Badge color="purple">Seasonal</Badge></Td>
              <Td>Seasonal effect: supply exceeds demand, eCPM in physiological decline.</Td>
              <Td>Normal. Reduce floors to maintain fill rate in the period.</Td>
            </tr>
            <tr>
              <Td><Badge color="gray">Mixed</Badge></Td>
              <Td>No dominant driver identified. Combination of factors.</Td>
              <Td>Manual analysis needed. Check metrics individually.</Td>
            </tr>
          </tbody>
        </table>
        <div className="rounded-lg bg-amber-50 p-3">
          <p className="text-sm text-amber-800">
            <strong>Orange badge with triangle:</strong> indicates a <strong>potentially misleading</strong> signal.
            eCPM is rising, but not because demand is strong — rather because the denominator (inventory or fill)
            is contracting. Do not optimize floor prices under these conditions.
          </p>
        </div>
      </Section>

      {/* FAQ */}
      <Section id="faq" icon={HelpCircle} title={t('docs.faq')} open={openSections.has('faq')} onToggle={toggle}>
        <div className="space-y-5">
          <div><h4 className="font-semibold text-slate-900">What is the baseline?</h4><p>Average revenue for the same hour/day over the <strong>7 previous weeks</strong> (7 same-weekday same-hour data points). Standard deviation calculated with sample formula (N-1). The same 7w rolling average method is also applied to the YoY comparison: instead of using a single day from the previous year (noisy data), the system computes the rolling average of the 7 weeks prior to the corresponding date last year, ensuring a more stable and reliable year-over-year comparison.</p></div>
          <div><h4 className="font-semibold text-slate-900">How does the YoY comparison work?</h4><p>The Year-over-Year comparison uses the same 7w baseline logic. The system identifies the corresponding date from the previous year (same weekday, same ISO week), then calculates the <strong>rolling average of the 7 previous weeks</strong> from that date. This prevents a single anomalous day from last year from distorting the comparison. The hourly YoY curve is estimated by distributing the daily total according to the hourly proportions of the current baseline.</p></div>
          <div><h4 className="font-semibold text-slate-900">Why multiple alerts for the same publisher?</h4><p>Alerts are generated per channel (GOOGLE/OPEN_BIDDING) and per rule (A1/A2/A3) separately.</p></div>
          <div><h4 className="font-semibold text-slate-900">GOOGLE vs OPEN_BIDDING?</h4><p><strong>GOOGLE:</strong> direct AdX/AdSense demand. <strong>OPEN_BIDDING:</strong> third-party SSPs (Amazon, Index Exchange...) via OB auction.</p></div>
          <div><h4 className="font-semibold text-slate-900">When should I really be concerned?</h4><p><Badge color="red">P0</Badge> always. <Badge color="orange">P1</Badge> check if concentrated or distributed. <Badge color="yellow">P2</Badge> monitor, often resolves in 4-8h.</p></div>
          <div><h4 className="font-semibold text-slate-900">REVENUE_ONLY?</h4><p>Inventory mix change, advertiser CPM drop, or seasonal demand shift. Check eCPM on the publisher page.</p></div>
          <div><h4 className="font-semibold text-slate-900">Are thresholds configurable?</h4><p>Yes: <code className="rounded bg-slate-100 px-1 text-xs">config/alerting_rules.yaml</code>. P0: -15%, drift: -8%, triage: -10%.</p></div>
          <div><h4 className="font-semibold text-slate-900">Frequency?</h4><p>Alerts A1+A3 every <strong>2h</strong>. Drift A2 every <strong>6h</strong>. Open alert recheck every <strong>5 min</strong>. Configurable in YAML.</p></div>
          <div><h4 className="font-semibold text-slate-900">Backtest?</h4><p>Runs the pipeline on historical data. Validates new thresholds. Alerts marked separately, no notifications sent.</p></div>
          <div><h4 className="font-semibold text-slate-900">What is an A0 alert?</h4><p>Technical alert generated when data is missing for more than 4 consecutive hours. Bypasses triage and analysis. Requires immediate data pipeline verification.</p></div>
          <div><h4 className="font-semibold text-slate-900">Is there a rate limit?</h4><p>Yes: <strong>5 backtests/hour</strong>, <strong>10 admin/hour</strong>, <strong>30 mutations/minute</strong> (ACK/resolve/etc), <strong>60 GET/minute</strong>. Protects the system from abuse.</p></div>
          <div><h4 className="font-semibold text-slate-900">How do I mark an alert as a false positive?</h4><p>In the alert detail, use the Feedback panel. Choose the appropriate FALSE_POSITIVE category (there are 5: MANUAL_INTERVENTION, SEASONALITY, TECHNICAL, PUBLISHER_CAMPAIGN, MARKET_NOISE), add a comment explaining the reason, and save. The feedback will be visible in the publisher history for future similar alerts.</p></div>
          <div><h4 className="font-semibold text-slate-900">If I log a manual intervention, will the system stop alerting on that drop?</h4><p>Yes, partially. The intervention hour is excluded from future baseline calculations, so if you make a floor price change at 14:00 on a Tuesday, that specific hour will no longer affect the baseline for future Tuesdays. This prevents recurring alerts on known changes.</p></div>
          <div><h4 className="font-semibold text-slate-900">Can I view the intervention history for a publisher?</h4><p>Not yet from the UI (will be added in a future phase). You can use the API: GET /api/publishers/{'{publisher_id}'}/interventions to see all interventions logged for that publisher.</p></div>

          <hr className="border-slate-200" />
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">What's new in v1.2</h4>

          <div>
            <h4 className="font-semibold text-slate-900">What is the Gross Margin Alert (A8)?</h4>
            <p>A8 monitors gross margin (<code className="rounded bg-slate-100 px-1 text-xs">gross_margin_pct</code>) per publisher. When the difference between gross and net revenue deviates significantly from the configured share_rate, it generates a P1 alert. Typical causes: share_rate misconfiguration, GAM data anomaly, or a contract renegotiation not reflected in config.</p>
          </div>
          <div>
            <h4 className="font-semibold text-slate-900">What are Leading Indicators?</h4>
            <p>CTR and Viewability are metrics that anticipate revenue drops. A deterioration in CTR or Viewability (<strong>-15%</strong> vs baseline) generates a <Badge color="blue">P2-WATCH</Badge> alert. No immediate action required, but they signal a possible revenue drop in the next 24-48h.</p>
          </div>
          <div>
            <h4 className="font-semibold text-slate-900">What does Cross-Channel Detection mean?</h4>
            <p>The system automatically detects when a drop on Open Market (GOOGLE_ADEX, OPEN_BIDDING, HB_*) is caused by an active DIRECT campaign. In this case, traffic is not lost but redistributed to a guaranteed-revenue channel. The alert is annotated and severity reduced to avoid false positives.</p>
          </div>
          <div>
            <h4 className="font-semibold text-slate-900">Why is RPM the primary KPI?</h4>
            <p>RPM (Revenue Per Mille pageview) measures overall monetization efficiency. Unlike eCPM, it is not affected by supply compression: if ad requests drop, eCPM can rise artificially, but RPM reflects the true yield per page view. It is the KPI publishers use to evaluate performance.</p>
          </div>
          <div>
            <h4 className="font-semibold text-slate-900">What are the 7 monitored channels?</h4>
            <p>GOOGLE_ADEX, OPEN_BIDDING, HB_MAGNITE, HB_PUBMATIC, TAM, DIRECT, and DEAL. Each channel has different dynamics and is monitored separately to prevent anomalies on one channel from being masked by positive performance on others.</p>
          </div>

          <hr className="border-slate-200" />
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">Multi-Metric Intelligence</h4>

          <div>
            <h4 className="font-semibold text-slate-900">Why does eCPM rise while revenue drops?</h4>
            <p><strong>Supply Squeeze:</strong> less inventory (ad requests dropping) means unit price rises, but total volume
            falls. eCPM is a ratio — it can rise even when things are going badly. Always check the driver: if it is
            orange (Supply Squeeze or Fill Effect), the signal is misleading.</p>
          </div>
          <div>
            <h4 className="font-semibold text-slate-900">What does the orange badge with triangle mean?</h4>
            <p>It indicates a <strong>potentially misleading</strong> signal. eCPM is moving in the indicated direction, but the cause
            is not real demand growth. Do not make floor price optimization decisions based solely on this signal.</p>
          </div>
          <div>
            <h4 className="font-semibold text-slate-900">The % match is low — should I be concerned?</h4>
            <p>The % match indicates how reliable and precise the pattern is. It is based on internal data consistency, cross-year
            confirmation, and sample size. A high % means you can rely on the signal for operational decisions.
            A low % is not alarming in itself, but indicates the signal should be treated with caution.
            The most reliable patterns combine high % match and a "Demand" driver (green).</p>
          </div>
          <div>
            <h4 className="font-semibold text-slate-900">When should I act on a Risk Zone?</h4>
            <p><strong>Always.</strong> Risk Zones indicate real demand weakness (both eCPM and coverage dropping together).
            Unlike other patterns that may be seasonal, the dual drop always requires attention: check the
            competitive landscape, contact advertisers, consider reducing floor prices.</p>
          </div>
        </div>
      </Section>

      {/* OPERATOR WORKFLOW - FEEDBACK */}
      <Section id="operator-workflow-feedback" icon={Users} title={t('docs.operator-workflow-feedback')} open={openSections.has('operator-workflow-feedback')} onToggle={toggle}>
        <p className="mb-4">
          The system accumulates operational knowledge through operator feedback on each alert.
        </p>
        <div className="mb-4">
          <h4 className="mb-2 font-semibold text-slate-900">Feedback Categories:</h4>
          <ul className="list-disc space-y-1 pl-5">
            <li><strong>REAL:</strong> Alert confirmed as a real anomaly</li>
            <li><strong>FALSE_POSITIVE_MANUAL_INTERVENTION:</strong> Known manual intervention (e.g. floor price change)</li>
            <li><strong>FALSE_POSITIVE_SEASONALITY:</strong> Expected seasonal variation (e.g. holidays)</li>
            <li><strong>FALSE_POSITIVE_TECHNICAL:</strong> Temporary technical issue (e.g. broken tag, then fixed)</li>
            <li><strong>FALSE_POSITIVE_PUBLISHER_CAMPAIGN:</strong> Known publisher campaign (e.g. A/B test)</li>
            <li><strong>FALSE_POSITIVE_MARKET_NOISE:</strong> Normal market noise</li>
          </ul>
        </div>
        <div className="mb-4">
          <h4 className="mb-2 font-semibold text-slate-900">Publisher History:</h4>
          <p>
            When viewing an alert, the system shows the history of previous feedback on the same publisher,
            allowing you to recognize recurring patterns.
          </p>
        </div>
        <div className="rounded-lg bg-blue-50 p-3">
          <p className="text-sm text-blue-800">
            <strong>How to use:</strong> In the alert detail, choose the appropriate category from the Feedback panel,
            add an optional comment, and save. Feedback is visible to the whole team.
          </p>
        </div>
      </Section>

      {/* OPERATOR WORKFLOW - ASSIGNMENT */}
      <Section id="operator-workflow-assignment" icon={Users} title={t('docs.operator-workflow-assignment')} open={openSections.has('operator-workflow-assignment')} onToggle={toggle}>
        <p className="mb-4">
          Alerts can be assigned to team members to clarify investigation ownership.
        </p>
        <div className="mb-4">
          <h4 className="mb-2 font-semibold text-slate-900">Email Validation:</h4>
          <p>Only <strong>@adkaora.com</strong> addresses are accepted (validated at the database level).</p>
        </div>
        <div className="mb-4">
          <h4 className="mb-2 font-semibold text-slate-900">Assignment:</h4>
          <p>
            In the alert detail, use the Assignment dropdown at the top to select a colleague.
            The alert will appear in their filtered list.
          </p>
        </div>
        <div className="rounded-lg bg-blue-50 p-3">
          <p className="text-sm text-blue-800">
            <strong>Dashboard Filters:</strong> The dashboard supports filtering by assigned_to to see only
            alerts assigned to you or your team.
          </p>
        </div>
      </Section>

      {/* OPERATOR WORKFLOW - INTERVENTION */}
      <Section id="operator-workflow-intervention" icon={Settings} title={t('docs.operator-workflow-intervention')} open={openSections.has('operator-workflow-intervention')} onToggle={toggle}>
        <p className="mb-4">
          Log manual interventions (floor price, MCM, targeting changes) to exclude them from future baselines and accumulate knowledge.
        </p>
        <div className="mb-4">
          <h4 className="mb-2 font-semibold text-slate-900">Required Fields:</h4>
          <ul className="list-disc space-y-1 pl-5">
            <li><strong>Publisher:</strong> Affected publisher ID</li>
            <li><strong>Type:</strong> FLOOR_PRICE_CHANGE, MCM_CONFIG, TARGETING_CHANGE, AD_UNIT_CHANGE, BLOCK_LIST, OTHER</li>
            <li><strong>Timestamp:</strong> Intervention date/time</li>
            <li><strong>Before/after value:</strong> Optional but recommended for floor price changes</li>
            <li><strong>Reason:</strong> Text description (e.g. 'Floor price raised from 0.50 to 1.20 to improve margin')</li>
          </ul>
        </div>
        <div className="mb-4">
          <h4 className="mb-2 font-semibold text-slate-900">Baseline Exclusion:</h4>
          <p>
            When you log an intervention, the entire hour of that timestamp is excluded from future alert baseline calculations,
            preventing false positives.
          </p>
        </div>
        <div className="mb-4">
          <h4 className="mb-2 font-semibold text-slate-900">Alert Link:</h4>
          <p>
            You can link an intervention to a specific alert to track which alerts led to corrective actions.
          </p>
        </div>
        <div className="rounded-lg bg-blue-50 p-3">
          <p className="text-sm text-blue-800 mb-2">
            <strong>Two Save Modes:</strong>
          </p>
          <ul className="list-disc space-y-1 pl-5 text-sm text-blue-800">
            <li><strong>Quick Log:</strong> Save independent intervention (not linked to any alert)</li>
            <li><strong>Link to Alert:</strong> Save intervention AND link it to the current alert</li>
          </ul>
        </div>
      </Section>

      {/* SLACK NOTIFICATIONS */}
      <Section id="slack-notifications" icon={Zap} title={t('docs.slack-notifications')} open={openSections.has('slack-notifications')} onToggle={toggle}>
        <p className="mb-4">
          Alerts are delivered to Slack with a level of detail calibrated to severity, so operators don't need to check the dashboard proactively.
        </p>

        <h4 className="mb-2 font-semibold text-slate-900">Routing by Severity:</h4>
        <table className="mb-4 w-full border-collapse">
          <thead>
            <tr>
              <Th>Severity</Th>
              <Th>Routing</Th>
              <Th>Detail</Th>
              <Th>When</Th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <Td><Badge color="red">P0</Badge></Td>
              <Td>Immediate</Td>
              <Td>Full report (contributors, geo, env, suggested actions)</Td>
              <Td>Immediately after alert generation</Td>
            </tr>
            <tr>
              <Td><Badge color="orange">P1</Badge></Td>
              <Td>Daily Digest</Td>
              <Td>Medium detail (revenue, triage, top 3 contributors)</Td>
              <Td>Daily digest at 08:00 UTC</Td>
            </tr>
            <tr>
              <Td><Badge color="yellow">P2</Badge></Td>
              <Td>Daily Digest</Td>
              <Td>Compact (one line with dashboard link)</Td>
              <Td>Daily digest at 08:00 UTC</Td>
            </tr>
            <tr>
              <Td><Badge color="yellow">P2-WATCH</Badge></Td>
              <Td>Daily Digest</Td>
              <Td>Compact (one line with dashboard link)</Td>
              <Td>Daily digest at 08:00 UTC</Td>
            </tr>
          </tbody>
        </table>

        <h4 className="mb-2 font-semibold text-slate-900">Block Kit Templates:</h4>
        <ul className="list-disc space-y-2 pl-5 mb-4">
          <li>
            <strong>P0 Full:</strong> Red header + revenue status + triage + top 5 contributors + geo breakdown + env breakdown + suggested actions + alert detail link
          </li>
          <li>
            <strong>P1 Medium:</strong> Orange header + revenue status + triage + top 3 contributors + alert detail link
          </li>
          <li>
            <strong>P2 Compact:</strong> Yellow header + revenue delta + triage label + alert detail link
          </li>
        </ul>

        <h4 className="mb-2 font-semibold text-slate-900">Configuration:</h4>
        <p className="mb-2">Admins configure the Slack webhook from the /admin page:</p>
        <ol className="list-decimal space-y-1 pl-5 mb-4">
          <li>Create a Slack webhook in the Adkaora workspace</li>
          <li>Enter the webhook URL and channel name in Admin &gt; Slack Configuration</li>
          <li>Test the connection using the "Test Connection" button</li>
          <li>Save the configuration (stored in alerting_rules.yaml)</li>
        </ol>

        <h4 className="mb-2 font-semibold text-slate-900">Daily Digest:</h4>
        <ul className="list-disc space-y-1 pl-5 mb-4">
          <li>Scheduled job at 08:00 UTC every day</li>
          <li>Collects all P1/P2/P2-WATCH alerts generated in the last 24h</li>
          <li>Sends a single Slack message with a summary</li>
          <li>If no alerts in the last 24h, the digest is not sent</li>
          <li>Manual endpoint: <code className="rounded bg-slate-100 px-1 text-xs">POST /api/admin/trigger-digest</code> (for testing or on-demand delivery)</li>
        </ul>

        <h4 className="mb-2 font-semibold text-slate-900">Delivery Status:</h4>
        <p className="mb-2">Alerts show delivery_status in the database:</p>
        <ul className="list-disc space-y-1 pl-5 mb-4">
          <li><code className="rounded bg-slate-100 px-1 text-xs">slack_sent</code>: Immediate notification sent successfully</li>
          <li><code className="rounded bg-slate-100 px-1 text-xs">slack_queued</code>: Queued for daily digest</li>
          <li><code className="rounded bg-slate-100 px-1 text-xs">pending</code>: Not yet processed</li>
          <li><code className="rounded bg-slate-100 px-1 text-xs">failed</code>: Send failed (webhook not configured or Slack error)</li>
        </ul>

        <h4 className="mb-2 font-semibold text-slate-900">Retry Logic:</h4>
        <p>
          Immediate notifications (P0) have automatic retry with exponential backoff (max 3 attempts). Digest notifications do not retry (if the digest fails, alerts remain in pending_notifications).
        </p>
      </Section>
    </>
  )
}

// ---------------------------------------------------------------------------
// Technical Tab
// ---------------------------------------------------------------------------

const TECH_SECTIONS = ['arch', 'stack', 'api', 'db', 'langgraph', 'data', 'multi-metric-arch', 'multi-metric-api', 'driver-classification', 'consistency-score', 'danger-zone-detection', 'deploy', 'security', 'config', 'scheduling']

function TechnicalDocs({ openSections, toggle, t }: { openSections: Set<string>; toggle: (id: string) => void; t: (key: string) => string }) {
  return (
    <>
      {/* ARCHITECTURE */}
      <Section id="arch" icon={Network} title={t('docs.arch')} open={openSections.has('arch')} onToggle={toggle}>
        <p className="mb-4">Sentinel is a modular monolith: a single Python process that exposes REST APIs, manages scheduling, and orchestrates the analysis pipeline.</p>

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
│  ├── alerting_cycle (A1+A3) every 2h                        │
│  ├── drift_cycle (A2)       every 6h                        │
│  └── check_recheck_queue    every 5min                      │
├─────────────────────────────────────────────────────────────┤
│  LangGraph Pipeline  (11 agenti)                            │
│  orchestrator → data_fetcher → validator → anomaly_detector │
│  → triage → [contributor | geo | env] → insight → report    │
│  → notifier                                                 │
├─────────────────────────────────────────────────────────────┤
│  Data Layer                                                 │
│  ├── SQLite (WAL)     alerts, events, recheck_queue         │
│  ├── Parquet (2 files) historical baseline data             │
│  └── [Athena / GAM]  future data sources                   │
└─────────────────────────────────────────────────────────────┘`}</CodeBlock>

        <div className="space-y-3">
          <div>
            <h4 className="font-semibold text-slate-900">Architectural decisions</h4>
            <ul className="mt-1 list-disc space-y-1 pl-5">
              <li><strong>Monolith:</strong> a single process simplifies deployment, debugging, and ops. The team is small (&lt;20), microservices are not needed.</li>
              <li><strong>SQLite WAL:</strong> zero-config, supports concurrent reads, sufficient for ~200 alerts. Migration to Postgres if needed is trivial (same SQL).</li>
              <li><strong>LangGraph:</strong> models the pipeline as a graph with state management, conditional branching, and parallelism.</li>
              <li><strong>Dual mode:</strong> every agent has a statistical fallback (no LLM) if <code className="rounded bg-slate-100 px-1 text-xs">ANTHROPIC_API_KEY</code> is not configured.</li>
            </ul>
          </div>
        </div>
      </Section>

      {/* TECH STACK */}
      <Section id="stack" icon={FolderTree} title={t('docs.stack')} open={openSections.has('stack')} onToggle={toggle}>
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <div>
            <h4 className="mb-2 font-semibold text-slate-900">Backend</h4>
            <table className="w-full border-collapse">
              <tbody>
                <tr><Td className="tabular-nums text-xs">fastapi 0.115</Td><Td>Framework REST async</Td></tr>
                <tr><Td className="tabular-nums text-xs">uvicorn 0.34</Td><Td>ASGI server (reload dev, 1 worker prod)</Td></tr>
                <tr><Td className="tabular-nums text-xs">pydantic 2.10</Td><Td>Data validation + API schema</Td></tr>
                <tr><Td className="tabular-nums text-xs">langgraph 0.2</Td><Td>Multi-agent pipeline orchestration</Td></tr>
                <tr><Td className="tabular-nums text-xs">langchain-anthropic 0.3</Td><Td>Claude integration (Haiku/Sonnet)</Td></tr>
                <tr><Td className="tabular-nums text-xs">pandas 2.2 + pyarrow 18</Td><Td>Parquet read/manipulation</Td></tr>
                <tr><Td className="tabular-nums text-xs">apscheduler 3.11</Td><Td>Pipeline scheduling (async)</Td></tr>
                <tr><Td className="tabular-nums text-xs">authlib 1.3</Td><Td>Google OAuth client</Td></tr>
                <tr><Td className="tabular-nums text-xs">httpx 0.28</Td><Td>Async HTTP client</Td></tr>
                <tr><Td className="tabular-nums text-xs">slowapi 0.1</Td><Td>Per-endpoint rate limiting</Td></tr>
                <tr><Td className="tabular-nums text-xs">sqlite3 (stdlib)</Td><Td>Embedded database (WAL mode)</Td></tr>
              </tbody>
            </table>
          </div>
          <div>
            <h4 className="mb-2 font-semibold text-slate-900">Frontend</h4>
            <table className="w-full border-collapse">
              <tbody>
                <tr><Td className="tabular-nums text-xs">react 18</Td><Td>UI framework</Td></tr>
                <tr><Td className="tabular-nums text-xs">typescript 5</Td><Td>Type safety</Td></tr>
                <tr><Td className="tabular-nums text-xs">vite 7</Td><Td>Build + dev server + HMR</Td></tr>
                <tr><Td className="tabular-nums text-xs">tailwind css 4</Td><Td>Utility-first styling</Td></tr>
                <tr><Td className="tabular-nums text-xs">@tanstack/react-query</Td><Td>Server state + caching</Td></tr>
                <tr><Td className="tabular-nums text-xs">recharts</Td><Td>Charts (trend, KPI)</Td></tr>
                <tr><Td className="tabular-nums text-xs">react-router-dom 6</Td><Td>SPA routing</Td></tr>
                <tr><Td className="tabular-nums text-xs">lucide-react</Td><Td>Icons</Td></tr>
              </tbody>
            </table>
          </div>
        </div>
        <div className="mt-4 rounded-lg bg-amber-50 p-3">
          <p className="text-sm text-amber-800">
            <strong>Future dependencies (prepared, not yet active):</strong> boto3 + pyathena (AWS Athena),
            slack-sdk (Slack notifications), aiosmtplib (email). Configuration managed from the Admin page.
          </p>
        </div>
      </Section>

      {/* API REFERENCE */}
      <Section id="api" icon={Code} title={t('docs.api')} open={openSections.has('api')} onToggle={toggle}>
        <p className="mb-4">All APIs are under <code className="rounded bg-slate-100 px-1 text-xs">/api</code>. Auth under <code className="rounded bg-slate-100 px-1 text-xs">/auth</code>. Live OpenAPI docs: <code className="rounded bg-slate-100 px-1 text-xs">/docs</code>. <strong>~34 endpoints total</strong> (v1.0: 19, Phase 3-4: +15).</p>
        <div className="mb-4 rounded-lg bg-blue-50 p-3">
          <p className="text-sm text-blue-800">
            <strong>v1.2 — New response fields:</strong> Alert and publisher endpoints now include: <code className="text-xs">rpm</code>, <code className="text-xs">ctr</code>, <code className="text-xs">viewability</code>, <code className="text-xs">gross_margin_pct</code>, <code className="text-xs">revenue_gross</code>. Fields are present when data is available (nullable).
          </p>
        </div>

        <h4 className="mb-2 font-semibold text-slate-900">Alert</h4>
        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>Method</Th><Th>Endpoint</Th><Th>Description</Th></tr></thead>
          <tbody>
            <tr><Td><Badge color="green">GET</Badge></Td><Td className="font-mono">/api/alerts</Td><Td>List alerts with filters (severity, status, channel, date_from, date_to, limit, offset)</Td></tr>
            <tr><Td><Badge color="green">GET</Badge></Td><Td className="font-mono">/api/alerts/:id</Td><Td>Full alert detail (contributors, geo, env, insights, events)</Td></tr>
            <tr><Td><Badge color="green">GET</Badge></Td><Td className="font-mono">/api/alerts/:id/trend</Td><Td>7-day revenue trend vs baseline (from parquet)</Td></tr>
            <tr><Td><Badge color="blue">POST</Badge></Td><Td className="font-mono">/api/alerts/:id/ack</Td><Td>Acknowledge (OPEN → ACK)</Td></tr>
            <tr><Td><Badge color="blue">POST</Badge></Td><Td className="font-mono">/api/alerts/:id/resolve</Td><Td>Resolve (any → RESOLVED)</Td></tr>
            <tr><Td><Badge color="blue">POST</Badge></Td><Td className="font-mono">/api/alerts/:id/recheck</Td><Td>Schedule recheck (+1h)</Td></tr>
            <tr><Td><Badge color="blue">POST</Badge></Td><Td className="font-mono">/api/alerts/:id/comment</Td><Td>Add comment</Td></tr>
          </tbody>
        </table>

        <h4 className="mb-2 font-semibold text-slate-900">Publisher</h4>
        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>Method</Th><Th>Endpoint</Th><Th>Description</Th></tr></thead>
          <tbody>
            <tr><Td><Badge color="green">GET</Badge></Td><Td className="font-mono">/api/publishers/top</Td><Td>Top publishers by revenue (year, limit)</Td></tr>
            <tr><Td><Badge color="green">GET</Badge></Td><Td className="font-mono">/api/publishers/:id/weekly-kpis</Td><Td>Weekly KPIs (revenue, eCPM, ad requests, coverage)</Td></tr>
            <tr><Td><Badge color="green">GET</Badge></Td><Td className="font-mono">/api/publishers/:id/ecpm-analysis</Td><Td>Seasonal eCPM analysis with optimization windows</Td></tr>
            <tr><Td><Badge color="green">GET</Badge></Td><Td className="font-mono">/api/publishers/:id/recurring-patterns</Td><Td>Cross-year recurring patterns (eCPM, hidden volume, risk zones)</Td></tr>
            <tr><Td><Badge color="green">GET</Badge></Td><Td className="font-mono">/api/publishers/:id/feedback-history</Td><Td>Feedback history for publisher with alert context (limit default 50, max 200). Rate limit: 60/min. <Badge color="purple">Phase 3</Badge></Td></tr>
            <tr><Td><Badge color="green">GET</Badge></Td><Td className="font-mono">/api/publishers/:id/interventions</Td><Td>Interventions for publisher (limit default 50, max 200). Rate limit: 60/min. <Badge color="purple">Phase 3</Badge></Td></tr>
          </tbody>
        </table>

        <h4 className="mb-2 font-semibold text-slate-900">Feedback <Badge color="purple">Phase 3</Badge></h4>
        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>Method</Th><Th>Endpoint</Th><Th>Description</Th></tr></thead>
          <tbody>
            <tr><Td><Badge color="blue">POST</Badge></Td><Td className="font-mono">/api/alerts/:id/feedback</Td><Td>Submit feedback for alert. Body: {'{"feedback_type": "REAL|FALSE_POSITIVE_*", "comment": "..."}'}. Auto-extracts publisher_id. Rate limit: 30/min.</Td></tr>
            <tr><Td><Badge color="green">GET</Badge></Td><Td className="font-mono">/api/alerts/:id/feedbacks</Td><Td>List all feedback for an alert (ordered by timestamp DESC). Rate limit: 60/min.</Td></tr>
          </tbody>
        </table>

        <h4 className="mb-2 font-semibold text-slate-900">Assignment <Badge color="purple">Phase 3</Badge></h4>
        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>Method</Th><Th>Endpoint</Th><Th>Description</Th></tr></thead>
          <tbody>
            <tr><Td><Badge color="blue">POST</Badge></Td><Td className="font-mono">/api/alerts/:id/assign</Td><Td>Assign alert. Body: {'{"assigned_to": "user@adkaora.com"}'}. @adkaora.com validation. INSERT OR REPLACE for reassignment. Rate limit: 30/min.</Td></tr>
            <tr><Td><Badge color="red">DELETE</Badge></Td><Td className="font-mono">/api/alerts/:id/assign</Td><Td>Remove assignment from alert. Rate limit: 30/min.</Td></tr>
            <tr><Td><Badge color="green">GET</Badge></Td><Td className="font-mono">/api/alerts?assigned_to=email</Td><Td>Filter alerts by assignee (extension of existing GET /api/alerts endpoint).</Td></tr>
          </tbody>
        </table>

        <h4 className="mb-2 font-semibold text-slate-900">Interventions <Badge color="purple">Phase 3</Badge></h4>
        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>Method</Th><Th>Endpoint</Th><Th>Description</Th></tr></thead>
          <tbody>
            <tr><Td><Badge color="blue">POST</Badge></Td><Td className="font-mono">/api/interventions</Td><Td>Create intervention. Body: {'{"publisher_id", "intervention_type", "timestamp", "description", "value_before?", "value_after?", "alert_id?"}'}. Types: PRICING_RULE, FLOOR_CPM, DEMAND_PARTNER_CONFIG, AD_UNIT_SETUP, POLICY_CHANGE, OTHER. Rate limit: 30/min.</Td></tr>
            <tr><Td><Badge color="blue">POST</Badge></Td><Td className="font-mono">/api/alerts/:id/link-intervention</Td><Td>Link existing intervention to alert. Body: {'{"intervention_id": N}'}. Rate limit: 30/min.</Td></tr>
          </tbody>
        </table>

        <h4 className="mb-2 font-semibold text-slate-900">Metrics <Badge color="blue">Phase 4</Badge></h4>
        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>Method</Th><Th>Endpoint</Th><Th>Description</Th></tr></thead>
          <tbody>
            <tr><Td><Badge color="green">GET</Badge></Td><Td className="font-mono">/api/metrics</Td><Td>Pipeline metrics for last N days (runs count, success rate, avg duration, LLM usage). Params: days (default 7). Rate limit: 60/min.</Td></tr>
            <tr><Td><Badge color="green">GET</Badge></Td><Td className="font-mono">/api/metrics/revenue-status-24h</Td><Td>24h revenue: current vs baseline 7w (rolling avg same weekday) + YoY 7w (rolling avg same weekday prior year). Rate limit: 60/min.</Td></tr>
          </tbody>
        </table>

        <h4 className="mb-2 font-semibold text-slate-900">System</h4>
        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>Method</Th><Th>Endpoint</Th><Th>Description</Th></tr></thead>
          <tbody>
            <tr><Td><Badge color="green">GET</Badge></Td><Td className="font-mono">/api/health</Td><Td>Health check (DB, scheduler, version)</Td></tr>
            <tr><Td><Badge color="green">GET</Badge></Td><Td className="font-mono">/api/backtest</Td><Td>List executed backtests</Td></tr>
            <tr><Td><Badge color="blue">POST</Badge></Td><Td className="font-mono">/api/backtest</Td><Td>Start backtest (start_date, end_date, step_hours)</Td></tr>
            <tr><Td><Badge color="green">GET</Badge></Td><Td className="font-mono">/api/admin/datasources</Td><Td>Data sources configuration</Td></tr>
            <tr><Td><Badge color="blue">POST</Badge></Td><Td className="font-mono">/api/admin/datasources</Td><Td>Update data sources configuration</Td></tr>
            <tr><Td><Badge color="blue">POST</Badge></Td><Td className="font-mono">/api/admin/datasources/test</Td><Td>Test connection to parquet/Athena/GAM. Rate limit: 10/hour.</Td></tr>
          </tbody>
        </table>

        <h4 className="mb-2 font-semibold text-slate-900">Admin - Slack <Badge color="blue">Phase 4</Badge></h4>
        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>Method</Th><Th>Endpoint</Th><Th>Description</Th></tr></thead>
          <tbody>
            <tr><Td><Badge color="green">GET</Badge></Td><Td className="font-mono">/api/admin/slack-config</Td><Td>Current Slack config (webhook_url masked). Rate limit: 60/min.</Td></tr>
            <tr><Td><Badge color="orange">PUT</Badge></Td><Td className="font-mono">/api/admin/slack-config</Td><Td>Update Slack config. Body: {'{"webhook_url", "channel"}'}. Saved to alerting_rules.yaml. Rate limit: 10/hour.</Td></tr>
            <tr><Td><Badge color="blue">POST</Badge></Td><Td className="font-mono">/api/admin/test-slack</Td><Td>Test Slack webhook with a test message. Rate limit: 10/hour.</Td></tr>
            <tr><Td><Badge color="blue">POST</Badge></Td><Td className="font-mono">/api/admin/trigger-digest</Td><Td>Manually trigger daily digest (for testing). Rate limit: 10/hour.</Td></tr>
          </tbody>
        </table>

        <h4 className="mb-2 font-semibold text-slate-900">Admin - Alerting Rules <Badge color="blue">Phase 4</Badge></h4>
        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>Method</Th><Th>Endpoint</Th><Th>Description</Th></tr></thead>
          <tbody>
            <tr><Td><Badge color="green">GET</Badge></Td><Td className="font-mono">/api/admin/alerting-rules</Td><Td>Current alerting rules as JSON. Rate limit: 60/min.</Td></tr>
            <tr><Td><Badge color="orange">PUT</Badge></Td><Td className="font-mono">/api/admin/alerting-rules</Td><Td>Update rules, validate, persist YAML, reload config. Rate limit: 10/hour.</Td></tr>
          </tbody>
        </table>

        <h4 className="mb-2 font-semibold text-slate-900">Auth</h4>
        <table className="w-full border-collapse text-xs">
          <thead><tr><Th>Method</Th><Th>Endpoint</Th><Th>Description</Th></tr></thead>
          <tbody>
            <tr><Td><Badge color="green">GET</Badge></Td><Td className="font-mono">/auth/login</Td><Td>Redirect to Google OAuth consent (dev: redirect to frontend)</Td></tr>
            <tr><Td><Badge color="green">GET</Badge></Td><Td className="font-mono">/auth/callback</Td><Td>OAuth callback, create session, set cookie</Td></tr>
            <tr><Td><Badge color="green">GET</Badge></Td><Td className="font-mono">/auth/me</Td><Td>Current user (dev: mock user)</Td></tr>
            <tr><Td><Badge color="blue">POST</Badge></Td><Td className="font-mono">/auth/logout</Td><Td>Delete session and cookie</Td></tr>
          </tbody>
        </table>
      </Section>

      {/* DATABASE */}
      <Section id="db" icon={Database} title={t('docs.db')} open={openSections.has('db')} onToggle={toggle}>
        <p className="mb-4">SQLite with WAL (Write-Ahead Logging) for concurrent reads. File: <code className="rounded bg-slate-100 px-1 text-xs">data/vna_alerts.db</code>. <strong>10 tables total</strong> (4 core + 6 operator workflow/notifications).</p>

        <h4 className="mb-2 font-semibold text-slate-900">alerts</h4>
        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>Column</Th><Th>Type</Th><Th>Notes</Th></tr></thead>
          <tbody>
            <tr><Td className="font-mono">alert_id</Td><Td>TEXT PK</Td><Td>Format: <code className="text-xs">ALT-YYYYMMDD-HHMMSS-P{'{0,1,2}'}</code></Td></tr>
            <tr><Td className="font-mono">timestamp</Td><Td>TEXT</Td><Td>ISO 8601</Td></tr>
            <tr><Td className="font-mono">severity</Td><Td>TEXT</Td><Td>CHECK: P0, P1, P2</Td></tr>
            <tr><Td className="font-mono">channel_group</Td><Td>TEXT</Td><Td>CHECK: GOOGLE_ADEX, OPEN_BIDDING, HB_MAGNITE, HB_PUBMATIC, TAM, DIRECT, DEAL</Td></tr>
            <tr><Td className="font-mono">status</Td><Td>TEXT</Td><Td>CHECK: OPEN, ACK, RESOLVED, SNOOZED</Td></tr>
            <tr><Td className="font-mono">alert_rule</Td><Td>TEXT</Td><Td>CHECK: A0, A1, A2, A3, A5, A6, A7, A8</Td></tr>
            <tr><Td className="font-mono">revenue_current</Td><Td>REAL</Td><Td>Current period revenue (EUR)</Td></tr>
            <tr><Td className="font-mono">revenue_baseline</Td><Td>REAL</Td><Td>7-day baseline revenue (EUR)</Td></tr>
            <tr><Td className="font-mono">revenue_delta_pct</Td><Td>REAL</Td><Td>Percentage delta</Td></tr>
            <tr><Td className="font-mono">triage_label</Td><Td>TEXT</Td><Td>TRAFFIC_DRIVEN, COVERAGE_DRIVEN, MIXED, REVENUE_ONLY, MARGIN_DRIVEN</Td></tr>
            <tr><Td className="font-mono">contributors_json</Td><Td>TEXT</Td><Td>JSON array of top publishers</Td></tr>
            <tr><Td className="font-mono">geo_breakdown_json</Td><Td>TEXT</Td><Td>JSON array geographic breakdown</Td></tr>
            <tr><Td className="font-mono">environment_split_json</Td><Td>TEXT</Td><Td>JSON object WEB/AMP/APP split</Td></tr>
            <tr><Td className="font-mono">insights_json</Td><Td>TEXT</Td><Td>JSON object findings + next steps</Td></tr>
            <tr><Td className="font-mono">execution_time_sec</Td><Td>REAL</Td><Td>Pipeline duration</Td></tr>
            <tr><Td className="font-mono">data_source</Td><Td>TEXT</Td><Td>athena, parquet, cache</Td></tr>
            <tr><Td className="font-mono">config_version</Td><Td>TEXT</Td><Td>Configuration version (default: "1.0.0")</Td></tr>
          </tbody>
        </table>

        <h4 className="mb-2 font-semibold text-slate-900">alert_events</h4>
        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>Column</Th><Th>Type</Th><Th>Notes</Th></tr></thead>
          <tbody>
            <tr><Td className="font-mono">event_id</Td><Td>INTEGER PK</Td><Td>Autoincrement</Td></tr>
            <tr><Td className="font-mono">alert_id</Td><Td>TEXT FK</Td><Td>Reference to alerts.alert_id</Td></tr>
            <tr><Td className="font-mono">event_type</Td><Td>TEXT</Td><Td>ACK, RESOLVE, RECHECK, COMMENT</Td></tr>
            <tr><Td className="font-mono">user_id</Td><Td>TEXT</Td><Td>Who performed the action</Td></tr>
            <tr><Td className="font-mono">comment</Td><Td>TEXT</Td><Td>Optional</Td></tr>
          </tbody>
        </table>

        <h4 className="mb-2 font-semibold text-slate-900">recheck_queue</h4>
        <p className="text-xs text-slate-500">Queue of scheduled rechecks. Status: PENDING → COMPLETED / FAILED.</p>

        <h4 className="mb-2 font-semibold text-slate-900">backtest_results</h4>
        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>Column</Th><Th>Type</Th><Th>Notes</Th></tr></thead>
          <tbody>
            <tr><Td className="font-mono">backtest_id</Td><Td>TEXT PK</Td><Td>Unique backtest ID</Td></tr>
            <tr><Td className="font-mono">status</Td><Td>TEXT</Td><Td>RUNNING, COMPLETED, FAILED</Td></tr>
            <tr><Td className="font-mono">date_range</Td><Td>JSON</Td><Td>{'{"start", "end", "step_hours"}'}</Td></tr>
            <tr><Td className="font-mono">alerts_generated</Td><Td>INTEGER</Td><Td>Number of alerts generated</Td></tr>
            <tr><Td className="font-mono">trigger_rate</Td><Td>REAL</Td><Td>% checks that generated an alert</Td></tr>
          </tbody>
        </table>

        <h4 className="mb-2 font-semibold text-slate-900">alert_feedback <Badge color="purple">Phase 3</Badge></h4>
        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>Column</Th><Th>Type</Th><Th>Notes</Th></tr></thead>
          <tbody>
            <tr><Td className="font-mono">feedback_id</Td><Td>INTEGER PK</Td><Td>Autoincrement</Td></tr>
            <tr><Td className="font-mono">alert_id</Td><Td>TEXT FK</Td><Td>→ alerts.alert_id</Td></tr>
            <tr><Td className="font-mono">user_id</Td><Td>TEXT NOT NULL</Td><Td>Operator who submitted feedback</Td></tr>
            <tr><Td className="font-mono">feedback_type</Td><Td>TEXT NOT NULL</Td><Td>CHECK: REAL, FALSE_POSITIVE_MANUAL_INTERVENTION, FALSE_POSITIVE_SEASONALITY, FALSE_POSITIVE_TECHNICAL, FALSE_POSITIVE_PUBLISHER_CAMPAIGN, FALSE_POSITIVE_MARKET_NOISE</Td></tr>
            <tr><Td className="font-mono">comment</Td><Td>TEXT</Td><Td>Optional comment</Td></tr>
            <tr><Td className="font-mono">publisher_id</Td><Td>TEXT</Td><Td>Auto-extracted from contributors for historical tracking</Td></tr>
            <tr><Td className="font-mono">timestamp</Td><Td>TEXT NOT NULL</Td><Td>ISO 8601</Td></tr>
          </tbody>
        </table>
        <p className="mb-4 text-xs text-slate-600">
          <strong>Purpose:</strong> Tracks operator feedback on alerts. publisher_id is auto-extracted from contributors for historical false positive pattern analysis per publisher.
          <br/><strong>Index:</strong> <code>idx_feedback_publisher</code>
        </p>

        <h4 className="mb-2 font-semibold text-slate-900">alert_assignments <Badge color="purple">Phase 3</Badge></h4>
        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>Column</Th><Th>Type</Th><Th>Notes</Th></tr></thead>
          <tbody>
            <tr><Td className="font-mono">assignment_id</Td><Td>INTEGER PK</Td><Td>Autoincrement</Td></tr>
            <tr><Td className="font-mono">alert_id</Td><Td>TEXT UNIQUE FK</Td><Td>→ alerts.alert_id (one assignment per alert)</Td></tr>
            <tr><Td className="font-mono">assigned_to</Td><Td>TEXT NOT NULL</Td><Td>@adkaora.com email (validated at Pydantic/API level)</Td></tr>
            <tr><Td className="font-mono">assigned_by</Td><Td>TEXT NOT NULL</Td><Td>Email of operator who assigned</Td></tr>
            <tr><Td className="font-mono">assigned_at</Td><Td>TEXT NOT NULL</Td><Td>ISO 8601</Td></tr>
          </tbody>
        </table>
        <p className="mb-4 text-xs text-slate-600">
          <strong>Purpose:</strong> One assignment per alert. Reassignment handled via INSERT OR REPLACE. Email @adkaora.com validation at API level.
          <br/><strong>Index:</strong> <code>idx_assignments_assigned_to</code>
        </p>

        <h4 className="mb-2 font-semibold text-slate-900">manual_interventions <Badge color="purple">Phase 3</Badge></h4>
        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>Column</Th><Th>Type</Th><Th>Notes</Th></tr></thead>
          <tbody>
            <tr><Td className="font-mono">intervention_id</Td><Td>INTEGER PK</Td><Td>Autoincrement</Td></tr>
            <tr><Td className="font-mono">timestamp</Td><Td>TEXT NOT NULL</Td><Td>When intervention was applied (for baseline exclusion)</Td></tr>
            <tr><Td className="font-mono">publisher_id</Td><Td>TEXT NOT NULL</Td><Td>Publisher the intervention was applied to</Td></tr>
            <tr><Td className="font-mono">intervention_type</Td><Td>TEXT NOT NULL</Td><Td>CHECK: PRICING_RULE, FLOOR_CPM, DEMAND_PARTNER_CONFIG, AD_UNIT_SETUP, POLICY_CHANGE, OTHER</Td></tr>
            <tr><Td className="font-mono">description</Td><Td>TEXT NOT NULL</Td><Td>Intervention description</Td></tr>
            <tr><Td className="font-mono">value_before</Td><Td>TEXT</Td><Td>Before value (optional)</Td></tr>
            <tr><Td className="font-mono">value_after</Td><Td>TEXT</Td><Td>After value (optional)</Td></tr>
            <tr><Td className="font-mono">user_id</Td><Td>TEXT NOT NULL</Td><Td>Operator who applied the intervention</Td></tr>
            <tr><Td className="font-mono">created_at</Td><Td>TEXT NOT NULL</Td><Td>ISO 8601</Td></tr>
          </tbody>
        </table>
        <p className="mb-4 text-xs text-slate-600">
          <strong>Purpose:</strong> Tracks manual operator interventions. Timestamp used for baseline exclusion query (excludes hours with interventions from baseline calculation).
          <br/><strong>Indexes:</strong> <code>idx_interventions_publisher</code>, <code>idx_interventions_timestamp</code>
        </p>

        <h4 className="mb-2 font-semibold text-slate-900">alert_intervention_links <Badge color="purple">Phase 3</Badge></h4>
        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>Column</Th><Th>Type</Th><Th>Notes</Th></tr></thead>
          <tbody>
            <tr><Td className="font-mono">link_id</Td><Td>INTEGER PK</Td><Td>Autoincrement</Td></tr>
            <tr><Td className="font-mono">alert_id</Td><Td>TEXT FK</Td><Td>→ alerts.alert_id</Td></tr>
            <tr><Td className="font-mono">intervention_id</Td><Td>INTEGER FK</Td><Td>→ manual_interventions.intervention_id</Td></tr>
            <tr><Td className="font-mono">linked_at</Td><Td>TEXT NOT NULL</Td><Td>ISO 8601</Td></tr>
          </tbody>
        </table>
        <p className="mb-4 text-xs text-slate-600">
          <strong>Purpose:</strong> Many-to-many junction table between alerts and interventions. Tracks which alerts led to corrective actions.
          <br/><strong>Index:</strong> <code>idx_intervention_links_alert</code>
        </p>

        <h4 className="mb-2 font-semibold text-slate-900">pending_notifications <Badge color="blue">Phase 4</Badge></h4>
        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>Column</Th><Th>Type</Th><Th>Notes</Th></tr></thead>
          <tbody>
            <tr><Td className="font-mono">id</Td><Td>INTEGER PK</Td><Td>Autoincrement</Td></tr>
            <tr><Td className="font-mono">alert_id</Td><Td>TEXT FK</Td><Td>→ alerts.alert_id ON DELETE CASCADE</Td></tr>
            <tr><Td className="font-mono">severity</Td><Td>TEXT NOT NULL</Td><Td>P1, P2, P2-WATCH</Td></tr>
            <tr><Td className="font-mono">channel_group</Td><Td>TEXT NOT NULL</Td><Td>GOOGLE, OPEN_BIDDING</Td></tr>
            <tr><Td className="font-mono">timestamp</Td><Td>TEXT NOT NULL</Td><Td>Alert timestamp</Td></tr>
            <tr><Td className="font-mono">created_at</Td><Td>TEXT NOT NULL</Td><Td>ISO 8601</Td></tr>
          </tbody>
        </table>
        <p className="mb-4 text-xs text-slate-600">
          <strong>Purpose:</strong> Queue for P1/P2/P2-WATCH alerts awaiting daily digest. P0 skips this table (immediate send). Emptied by the daily_slack_digest job.
          <br/><strong>Index:</strong> <code>idx_pending_notifications_created_at</code>
        </p>

        <h4 className="mb-2 font-semibold text-slate-900">pipeline_runs <Badge color="blue">Phase 4</Badge></h4>
        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>Column</Th><Th>Type</Th><Th>Notes</Th></tr></thead>
          <tbody>
            <tr><Td className="font-mono">id</Td><Td>INTEGER PK</Td><Td>Autoincrement</Td></tr>
            <tr><Td className="font-mono">run_id</Td><Td>TEXT NOT NULL</Td><Td>Run UUID</Td></tr>
            <tr><Td className="font-mono">timestamp</Td><Td>TEXT NOT NULL</Td><Td>ISO 8601</Td></tr>
            <tr><Td className="font-mono">channel_group</Td><Td>TEXT NOT NULL</Td><Td>GOOGLE, OPEN_BIDDING</Td></tr>
            <tr><Td className="font-mono">trigger_type</Td><Td>TEXT NOT NULL</Td><Td>A0, A1, A2, A3, A5, A6, A7</Td></tr>
            <tr><Td className="font-mono">mode</Td><Td>TEXT NOT NULL</Td><Td>LIVE, BACKTEST</Td></tr>
            <tr><Td className="font-mono">status</Td><Td>TEXT NOT NULL</Td><Td>SUCCESS, FAILED, SKIPPED</Td></tr>
            <tr><Td className="font-mono">duration_sec</Td><Td>REAL</Td><Td>Pipeline execution duration</Td></tr>
            <tr><Td className="font-mono">llm_used</Td><Td>INTEGER</Td><Td>0 or 1 (boolean)</Td></tr>
            <tr><Td className="font-mono">llm_fallback</Td><Td>INTEGER</Td><Td>0 or 1 (boolean)</Td></tr>
            <tr><Td className="font-mono">alert_id</Td><Td>TEXT</Td><Td>Alert generated (null if no alert)</Td></tr>
            <tr><Td className="font-mono">error_message</Td><Td>TEXT</Td><Td>Error message if FAILED</Td></tr>
            <tr><Td className="font-mono">created_at</Td><Td>TEXT NOT NULL</Td><Td>ISO 8601</Td></tr>
          </tbody>
        </table>
        <p className="mb-4 text-xs text-slate-600">
          <strong>Purpose:</strong> Records every pipeline execution for performance tracking and debugging. Used for GET /api/metrics.
          <br/><strong>Index:</strong> <code>idx_pipeline_runs_created</code>
        </p>

        <div className="mt-3 rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
          Core indexes: <code>idx_alerts_timestamp</code>, <code>idx_alerts_status</code>, <code>idx_alerts_severity</code>.
          Foreign keys enabled (<code>PRAGMA foreign_keys=ON</code>).
        </div>
      </Section>

      {/* LANGGRAPH */}
      <Section id="langgraph" icon={Cpu} title={t('docs.langgraph')} open={openSections.has('langgraph')} onToggle={toggle}>
        <p className="mb-4">
          The pipeline is implemented as a <code className="rounded bg-slate-100 px-1 text-xs">StateGraph</code> of LangGraph.
          Each node is a function <code className="rounded bg-slate-100 px-1 text-xs">(AlertState) → AlertState</code> that enriches the state.
        </p>

        <h4 className="mb-2 font-semibold text-slate-900">AlertState (TypedDict)</h4>
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
  alert_payload: dict     # Final payload for DB
  markdown_report: str    # Formatted report
  delivery_status: dict   # {slack: bool, email: bool}

  # Metadata
  execution_errors: list  # Accumulated non-blocking errors
  data_source: str        # "athena", "parquet", "cache"
  alert_rule: str         # "A0", "A1", "A2", "A3" (may differ from trigger_type)
}`}</CodeBlock>

        <h4 className="mb-2 font-semibold text-slate-900">Graph and branching</h4>
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

        <h4 className="mb-2 font-semibold text-slate-900">Dual mode: LLM + Fallback</h4>
        <p>
          Agents 4 (Anomaly Detector), 6a (Contributor), 6b (Geo) and 7 (Insight) support two modes:
        </p>
        <ul className="mt-1 list-disc space-y-1 pl-5">
          <li><strong>With API key:</strong> use Claude (Haiku for 4/6a/6b, Sonnet for 7) for advanced analysis.</li>
          <li><strong>Without API key:</strong> statistical/deterministic template fallback. Zero cost, zero LLM latency.</li>
          <li>If the LLM fails at runtime, the fallback is used automatically and the error is logged in <code className="rounded bg-slate-100 px-1 text-xs">execution_errors</code>.</li>
        </ul>
      </Section>

      {/* DATA LAYER */}
      <Section id="data" icon={Database} title={t('docs.data')} open={openSections.has('data')} onToggle={toggle}>
        <h4 className="mb-2 font-semibold text-slate-900">Parquet files (v1.2 — 2 consolidated files)</h4>
        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>File</Th><Th>Rows</Th><Th>Size</Th><Th>Content</Th></tr></thead>
          <tbody>
            <tr><Td className="tabular-nums text-xs">daily_aggregated.parquet</Td><Td>~1M</Td><Td>~8 MB</Td><Td>Daily metrics aggregated by publisher/channel/country/environment. Includes ad_requests, impressions, revenue_gross, revenue_net, clicks, viewable_impressions.</Td></tr>
            <tr><Td className="tabular-nums text-xs">hourly_aggregated.parquet</Td><Td>~740K</Td><Td>~6 MB</Td><Td>Hourly metrics by channel (used for A1 alerts). Same fields as daily + hourly granularity.</Td></tr>
          </tbody>
        </table>
        <p className="mb-3">Time range: <strong>Jan 2024 - Mar 2026</strong>. Loaded into memory (pandas DataFrame) with application-level caching. <Badge color="purple">v1.2</Badge> consolidated from 3 to 2 files.</p>
        <h4 className="mb-2 font-semibold text-slate-900">Schema (18 fields)</h4>
        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>Field</Th><Th>Type</Th><Th>Description</Th></tr></thead>
          <tbody>
            <tr><Td className="font-mono">date / hour</Td><Td>DATE / TIMESTAMP</Td><Td>Date (daily) or hour (hourly)</Td></tr>
            <tr><Td className="font-mono">publisher_id</Td><Td>STRING</Td><Td>Publisher identifier</Td></tr>
            <tr><Td className="font-mono">channel</Td><Td>STRING</Td><Td>One of the 7 monitored channels</Td></tr>
            <tr><Td className="font-mono">country</Td><Td>STRING</Td><Td>ISO 2 country code</Td></tr>
            <tr><Td className="font-mono">environment</Td><Td>STRING</Td><Td>WEB, AMP, APP, UNKNOWN</Td></tr>
            <tr><Td className="font-mono">ad_requests</Td><Td>INT</Td><Td>Ad requests (bacino)</Td></tr>
            <tr><Td className="font-mono">impressions_filled</Td><Td>INT</Td><Td>Served impressions</Td></tr>
            <tr><Td className="font-mono">revenue_gross</Td><Td>FLOAT</Td><Td>Gross revenue (EUR)</Td></tr>
            <tr><Td className="font-mono">revenue_net</Td><Td>FLOAT</Td><Td>Net publisher revenue (EUR)</Td></tr>
            <tr><Td className="font-mono">clicks</Td><Td>INT</Td><Td>Ad clicks</Td></tr>
            <tr><Td className="font-mono">viewable_impressions</Td><Td>INT</Td><Td>Viewable impressions (IAB standard)</Td></tr>
            <tr><Td className="font-mono">measurable_impressions</Td><Td>INT</Td><Td>Measurable impressions for viewability</Td></tr>
            <tr><Td className="font-mono">pageviews</Td><Td>INT</Td><Td>Pageviews for RPM calculation</Td></tr>
            <tr><Td className="font-mono">ecpm</Td><Td>FLOAT</Td><Td>Calculated: (revenue / impressions) * 1000</Td></tr>
            <tr><Td className="font-mono">rpm</Td><Td>FLOAT</Td><Td>Calculated: (revenue / pageviews) * 1000</Td></tr>
            <tr><Td className="font-mono">ctr</Td><Td>FLOAT</Td><Td>Calculated: clicks / impressions * 100</Td></tr>
            <tr><Td className="font-mono">viewability</Td><Td>FLOAT</Td><Td>Calculated: viewable / measurable * 100</Td></tr>
            <tr><Td className="font-mono">coverage</Td><Td>FLOAT</Td><Td>Calculated: impressions / ad_requests</Td></tr>
          </tbody>
        </table>

        <h4 className="mb-2 font-semibold text-slate-900">AWS Athena (future)</h4>
        <p className="mb-2">Prepared but not yet active. The data fetcher already has logic for:</p>
        <ul className="list-disc space-y-1 pl-5">
          <li>Athena queries via <code className="rounded bg-slate-100 px-1 text-xs">pyathena</code> with configurable timeout (default 30s) and 1 retry (2 total attempts) with exponential backoff</li>
          <li>Fallback chain: Athena → GAM → Parquet. In LIVE mode, if no real source is available, the pipeline halts (no synthetic data)</li>
          <li>Result cache for 24h (<code className="rounded bg-slate-100 px-1 text-xs">data_sources.cache_ttl_hours</code>)</li>
        </ul>

        <h4 className="mt-3 mb-2 font-semibold text-slate-900">GAM API (future)</h4>
        <p>Google Ad Manager API as an alternative source. Configurable from Admin page.</p>

        <div className="mt-3 rounded-lg bg-amber-50 p-3">
          <p className="text-sm text-amber-800">
            <strong>Data source switching:</strong> managed from Admin page (<code>/admin</code>). The configuration file
            is <code>data/datasource_config.json</code>. The data fetcher selects the source based on the active config.
          </p>
        </div>
      </Section>

      {/* MULTI-METRIC DATA ARCHITECTURE */}
      <Section id="multi-metric-arch" icon={BarChart3} title={t('docs.multi-metric-arch')} open={openSections.has('multi-metric-arch')} onToggle={toggle}>
        <p className="mb-4">
          Multi-metric analysis is based on <strong>3 pre-computed JSON files</strong> generated by analysis scripts
          on real parquet data (<code className="rounded bg-slate-100 px-1 text-xs">data/baseline/</code>).
        </p>

        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>File</Th><Th>Path</Th><Th>Content</Th></tr></thead>
          <tbody>
            <tr>
              <Td className="font-mono">ecpm-seasonal-analysis.json</Td>
              <Td className="tabular-nums text-xs">data/seasonal/</Td>
              <Td>Seasonal periods with aggregated metrics and week → period lookup. Identifies Easter, Summer, Back to School, Black Friday, Christmas, etc.</Td>
            </tr>
            <tr>
              <Td className="font-mono">enriched-recurring-patterns.json</Td>
              <Td className="tabular-nums text-xs">data/seasonal/</Td>
              <Td>Recurring cross-year patterns with classified driver, detailed metrics (eCPM, ad requests, coverage, impressions, revenue) and consistency score.</Td>
            </tr>
            <tr>
              <Td className="font-mono">optimization-windows-enriched.json</Td>
              <Td className="tabular-nums text-xs">data/seasonal/</Td>
              <Td>Optimization windows enriched with causal driver, YoY match, and additional metrics per window.</Td>
            </tr>
          </tbody>
        </table>

        <h4 className="mb-2 font-semibold text-slate-900">Generation pipeline</h4>
        <CodeBlock>{`data/baseline/*.parquet
        │
        ├── Seasonal analysis script
        │   └── ecpm-seasonal-analysis.json
        │
        ├── Recurring patterns script
        │   └── enriched-recurring-patterns.json
        │       (cross-year matching, Pearson correlation, driver classification)
        │
        └── Optimization windows script
            └── optimization-windows-enriched.json
                (driver enrichment, YoY consistency scoring)`}</CodeBlock>

        <div className="mt-3 rounded-lg bg-blue-50 p-3">
          <p className="text-sm text-blue-800">
            <strong>Real data:</strong> all files are generated from real parquet data (Jan 2024 - Jan 2026).
            No synthetic or mock data. Regeneration requires access to the parquet files in <code className="text-xs">data/baseline/</code>.
          </p>
        </div>
      </Section>

      {/* MULTI-METRIC API ENDPOINTS */}
      <Section id="multi-metric-api" icon={Code} title={t('docs.multi-metric-api')} open={openSections.has('multi-metric-api')} onToggle={toggle}>
        <p className="mb-4">Dedicated endpoints for publisher multi-metric analysis.</p>

        <h4 className="mb-2 font-semibold text-slate-900">GET /api/publishers/{'{id}'}/recurring-patterns</h4>
        <p className="mb-2">Cross-year recurring patterns with full analysis.</p>
        <CodeBlock>{`{
  "ecpm_patterns": [
    {
      "period_name": "Summer 2024",
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
      "ecpm_status": "FLAT",  // eCPM flat → hidden pattern
      "weekly_impact_eur": -2150.0,
      "reliability_score": 0.85,    // reliability (0-1)
      "business_impact": "During Q1 Slowdown (6 weeks) revenue drops..."
    }
  ],
  "danger_zones": [
    {
      "period_name": "Post-Christmas",
      "weeks": "W1-W3",
      "ecpm_delta_pct": -22.1,
      "coverage_delta_pct": -18.4,
      "severity": "HIGH",
      "reliability_score": 0.78,    // reliability (0-1)
      "explanation": "During Post-Christmas both eCPM (-22.1%) and coverage (-18.4%) drop..."
    }
  ],
  "yearly_avg": {
    "ecpm_2024": 2.15,
    "ecpm_2025": 2.08
  }
}`}</CodeBlock>

        <h4 className="mt-4 mb-2 font-semibold text-slate-900">GET /api/publishers/{'{id}'}/ecpm-analysis</h4>
        <p className="mb-2">Seasonal eCPM analysis with enriched optimization windows.</p>
        <CodeBlock>{`{
  "optimization_windows": [
    {
      "period_name": "Black Friday",
      "signal": "RAISE",
      "ecpm_delta_pct": 28.5,
      "driver": "DEMAND_DRIVEN",
      "consistency_score": 0.91,  // 4-component reliability score (see dedicated section)
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

        <h4 className="mt-4 mb-2 font-semibold text-slate-900">GET /api/publishers/{'{id}'}/weekly-kpis</h4>
        <p className="mb-2">Weekly KPIs with YoY fields and recurring pattern flags.</p>
        <CodeBlock>{`{
  "weeks": [...],
  "has_recurring_patterns": true,
  "compare_prev_year": true,  // true if 2024 data available
  "yoy_fields": {
    "revenue_yoy_pct": -5.2,
    "ecpm_yoy_pct": 3.1,
    "bacino_yoy_pct": -8.0,
    "coverage_yoy_pct": -0.5
  }
}`}</CodeBlock>
      </Section>

      {/* DRIVER CLASSIFICATION */}
      <Section id="driver-classification" icon={Target} title={t('docs.driver-classification')} open={openSections.has('driver-classification')} onToggle={toggle}>
        <p className="mb-4">
          Each eCPM change is classified with a <strong>causal driver</strong> based on the combination
          of main metric changes. Reference threshold: <strong>+/- 5%</strong>.
        </p>

        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>Driver</Th><Th>eCPM</Th><Th>Ad Requests</Th><Th>Coverage</Th><Th>Impressions</Th><Th>Logic</Th></tr></thead>
          <tbody>
            <tr>
              <Td><Badge color="green">DEMAND_DRIVEN</Badge></Td>
              <Td className="font-mono">&gt; +5%</Td>
              <Td className="font-mono">&ge; -5%</Td>
              <Td className="font-mono">&ge; -5%</Td>
              <Td className="font-mono">—</Td>
              <Td>eCPM rises with stable inventory and fill rate → genuine demand</Td>
            </tr>
            <tr>
              <Td><Badge color="orange">SUPPLY_SQUEEZE</Badge></Td>
              <Td className="font-mono">&gt; +5%</Td>
              <Td className="font-mono">&lt; -5%</Td>
              <Td className="font-mono">—</Td>
              <Td className="font-mono">—</Td>
              <Td>eCPM rises but ad requests drop → high price on less inventory</Td>
            </tr>
            <tr>
              <Td><Badge color="orange">FILL_EFFECT</Badge></Td>
              <Td className="font-mono">&gt; +5%</Td>
              <Td className="font-mono">&ge; -5%</Td>
              <Td className="font-mono">&lt; -5%</Td>
              <Td className="font-mono">—</Td>
              <Td>eCPM rises with stable ad requests but falling coverage → only premium impressions served</Td>
            </tr>
            <tr>
              <Td><Badge color="blue">VOLUME_DRIVEN</Badge></Td>
              <Td className="font-mono">&lt; -5%</Td>
              <Td className="font-mono">—</Td>
              <Td className="font-mono">—</Td>
              <Td className="font-mono">&gt; +5%</Td>
              <Td>eCPM drops with more impressions → price diluted over larger volume</Td>
            </tr>
            <tr>
              <Td><Badge color="purple">SEASONAL_DEMAND</Badge></Td>
              <Td className="font-mono">&lt; -5%</Td>
              <Td className="font-mono">&gt; +5%</Td>
              <Td className="font-mono">&lt; -5%</Td>
              <Td className="font-mono">—</Td>
              <Td>eCPM drops with rising ad requests and falling coverage → supply exceeds demand</Td>
            </tr>
            <tr>
              <Td><Badge color="gray">MIXED</Badge></Td>
              <Td className="font-mono" colSpan={4}>None of the above combinations matched</Td>
              <Td>No dominant driver identifiable</Td>
            </tr>
          </tbody>
        </table>

        <div className="rounded-lg bg-blue-50 p-3">
          <p className="text-sm text-blue-800">
            <strong>Evaluation order:</strong> criteria are evaluated in the order shown. The first match wins.
            If no criterion is satisfied, the driver is MIXED. The 5% threshold is configurable.
          </p>
        </div>
      </Section>

      {/* SCORE DI AFFIDABILITA' */}
      <Section id="consistency-score" icon={Zap} title={t('docs.consistency-score')} open={openSections.has('consistency-score')} onToggle={toggle}>
        <p className="mb-4">
          The reliability score measures how reliable and reproducible a pattern is.
          It is calculated with different methodologies for recurring patterns, optimization windows,
          hidden volume patterns, and risk zones.
        </p>

        <h4 className="mb-2 font-semibold text-slate-900">Recurring Patterns (eCPM)</h4>
        <p className="mb-2">
          <strong>Pearson</strong> correlation of weekly delta% between 2024 and 2025 in the same period.
        </p>
        <CodeBlock>{`# For each week in the pattern period:
delta_2024[w] = (ecpm[w] - avg_ecpm_2024) / avg_ecpm_2024 * 100
delta_2025[w] = (ecpm[w] - avg_ecpm_2025) / avg_ecpm_2025 * 100

consistency = pearson_correlation(delta_2024, delta_2025)
# Range: -1.0 (inverse) → 0.0 (no correlation) → 1.0 (perfect)`}</CodeBlock>

        <h4 className="mt-4 mb-2 font-semibold text-slate-900">Optimization Windows</h4>
        <p className="mb-2">
          Composite score based on 4 weighted components measuring window reliability:
        </p>
        <CodeBlock>{`# Reliability score for Optimization Windows
score = 0.0

# 1. Internal consistency (0.35)
# Low variance in weekly delta% within the window = precise signal
week_deltas = [delta_pct for each week in the window]
if len(week_deltas) >= 2:
    mean_d = mean(week_deltas)
    cv = std(week_deltas) / max(|mean_d|, 1)   # coefficient of variation
    score += 0.35 * max(0, 1 - cv)
elif len(week_deltas) == 1:
    score += 0.35 * 0.5   # partial credit for single week

# 2. Cross-year recurrence (0.30)
if same_signal_prev_year:        # same signal RAISE/LOWER
    score += 0.30
elif exists_in_prev_year:        # present but different signal
    score += 0.10

# 3. Magnitude similarity (0.20)
diff = |delta_current - delta_prev_year|
max_abs = max(|delta_current|, |delta_prev_year|, 1)
score += 0.20 * (1 - min(diff / max_abs, 1))

# 4. Sample size (0.15)
if weeks >= 4: score += 0.15
elif weeks >= 2: score += 0.15 * (weeks / 4)
else: score += 0.15 * 0.3   # single week: minimum credit`}</CodeBlock>

        <h4 className="mt-4 mb-2 font-semibold text-slate-900">Hidden Volume Patterns</h4>
        <p className="mb-2">
          Reliability score for patterns hidden below eCPM. 4 weighted components:
        </p>
        <CodeBlock>{`# Reliability score for Hidden Patterns
score = 0.0

# 1. Directional consistency cross-year (0.40)
# Same direction (both DOWN or both UP) in 2024 and 2025
same_dir = (d2024 < 0 and d2025 < 0) or (d2024 > 0 and d2025 > 0)
if same_dir:
    score += 0.40
elif one_year_neutral:    # one year at zero
    score += 0.15

# 2. Magnitude similarity (0.30)
diff = |avg_delta_2024 - avg_delta_2025|
max_abs = max(|avg_delta_2024|, |avg_delta_2025|, 1)
score += 0.30 * (1 - min(diff / max_abs, 1))

# 3. Sample size (0.15)
if weeks >= 4: score += 0.15
elif weeks >= 2: score += 0.15 * (weeks / 4)
else: score += 0.05

# 4. eCPM masking (0.15)
# Truly hidden patterns (eCPM FLAT) are more reliable
if ecpm_status == "FLAT":    score += 0.15   # completely hidden
elif ecpm_UP and signal_DOWN: score += 0.10   # masked by rising eCPM
else:                         score += 0.05   # partially visible`}</CodeBlock>

        <h4 className="mt-4 mb-2 font-semibold text-slate-900">Risk Zones (Danger Zones)</h4>
        <p className="mb-2">
          Reliability score for danger zones. 4 weighted components:
        </p>
        <CodeBlock>{`# Reliability score for Danger Zones
score = 0.0

# 1. Decline severity (0.35)
# Larger declines = stronger evidence of a real problem
avg_decline = (|ecpm_delta| + |coverage_delta|) / 2
if avg_decline >= 15: score += 0.35
else: score += 0.35 * (avg_decline / 15)

# 2. Dual confirmation (0.30)
# eCPM + coverage both < -5% = strong signal
if ecpm_delta < -5% AND coverage_delta < -5%:
    score += 0.30
else:
    score += 0.15

# 3. Sample size (0.20)
if weeks >= 4: score += 0.20
elif weeks >= 2: score += 0.20 * (weeks / 4)
else: score += 0.05

# 4. Triple confirmation (0.15)
# Bonus if ad requests also decline
if ad_requests_delta < -5%: score += 0.15    # triple decline = very strong signal
elif ad_requests_delta > +5%: score += 0.05 # ad requests up but coverage down = interesting
else: score += 0.08                          # neutral ad requests

# Score finale: min(score, 1.0)`}</CodeBlock>

        <div className="mt-3 rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
          <strong>Interpretation:</strong> &gt; 0.7 = stable and reliable pattern. 0.4 - 0.7 = pattern present but variable.
          &lt; 0.4 = weak pattern, do not rely on it for operational decisions.
        </div>
      </Section>

      {/* DANGER ZONE DETECTION */}
      <Section id="danger-zone-detection" icon={ShieldAlert} title={t('docs.danger-zone-detection')} open={openSections.has('danger-zone-detection')} onToggle={toggle}>
        <p className="mb-4">
          Danger zones are automatically detected by analyzing periods where coverage and eCPM
          decline simultaneously.
        </p>

        <h4 className="mb-2 font-semibold text-slate-900">Detection Criteria</h4>
        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>Condition</Th><Th>Value</Th></tr></thead>
          <tbody>
            <tr><Td>Coverage delta</Td><Td className="font-mono">&lt; -5%</Td></tr>
            <tr><Td>eCPM delta</Td><Td className="font-mono">&lt; -5%</Td></tr>
            <tr><Td>Both in the same period</Td><Td>Yes (AND condition)</Td></tr>
          </tbody>
        </table>

        <h4 className="mb-2 font-semibold text-slate-900">Severity Assignment</h4>
        <CodeBlock>{`if coverage_delta < -15% AND ecpm_delta < -15%:
    severity = "HIGH"
elif coverage_delta < -5% AND ecpm_delta < -5%:
    severity = "MEDIUM"
else:
    # Not a danger zone`}</CodeBlock>

        <h4 className="mt-3 mb-2 font-semibold text-slate-900">Data Structure</h4>
        <CodeBlock>{`{
  "period_name": "Post-Christmas",
  "weeks": "W1-W3",
  "ecpm_delta_pct": -22.1,
  "coverage_delta_pct": -18.4,
  "severity": "HIGH",
  "bacino_delta_pct": 5.2,       // ad requests can be stable or growing
  "revenue_impact_eur": -8500.0,
  "reliability_score": 0.78,     // reliability score (0-1), see dedicated section
  "explanation": "During Post-Christmas (3 weeks) both eCPM (-22.1%) and coverage (-18.4%) drop simultaneously. High risk: the joint decline is significant..."
}`}</CodeBlock>

        <div className="mt-3 rounded-lg bg-amber-50 p-3">
          <p className="text-sm text-amber-800">
            <strong>Note:</strong> ad requests in danger zones can be stable or even growing.
            The critical signal is the dual drop in eCPM (price) and coverage (fill rate), which indicates that
            even though traffic is present, ad demand fails to fill it at adequate prices.
            The <code className="text-xs">explanation</code> field contains a description automatically generated by the backend,
            and <code className="text-xs">reliability_score</code> indicates how reliable the pattern is (see "Reliability Score Calculation" section).
          </p>
        </div>
      </Section>

      {/* DEPLOY */}
      <Section id="deploy" icon={Container} title={t('docs.deploy')} open={openSections.has('deploy')} onToggle={toggle}>
        <h4 className="mb-2 font-semibold text-slate-900">Local Development</h4>
        <CodeBlock>{`# Terminal 1 - Backend
python3 -m backend.main          # :8000, ENVIRONMENT=development, hot reload

# Terminal 2 - Frontend
cd frontend && npm run dev        # :5173, Vite proxy → :8000, HMR`}</CodeBlock>
        <p className="mb-4 text-xs text-slate-500">In dev: no login, open CORS, uvicorn with reload, 1 worker.</p>

        <h4 className="mb-2 font-semibold text-slate-900">Production (Docker)</h4>
        <CodeBlock>{`# Build e run
docker compose build              # Multi-stage: node:20 → python:3.11
docker compose up -d              # .env con ENVIRONMENT=production + OAuth

# Dockerfile stages:
# 1. frontend-build: npm ci + npm run build → frontend/dist/
# 2. runtime: pip install + copia backend + frontend/dist + config
# CMD: uvicorn --host 0.0.0.0 --port 8000 --workers 1`}</CodeBlock>

        <h4 className="mt-3 mb-2 font-semibold text-slate-900">Environment Variables (production)</h4>
        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>Variable</Th><Th>Required</Th><Th>Default</Th><Th>Note</Th></tr></thead>
          <tbody>
            <tr><Td className="font-mono">ENVIRONMENT</Td><Td><Badge color="red">Yes</Badge></Td><Td>development</Td><Td>Set to "production" to enable auth and static serving</Td></tr>
            <tr><Td className="font-mono">GOOGLE_CLIENT_ID</Td><Td><Badge color="red">Yes</Badge></Td><Td>-</Td><Td>From Google Cloud Console</Td></tr>
            <tr><Td className="font-mono">GOOGLE_CLIENT_SECRET</Td><Td><Badge color="red">Yes</Badge></Td><Td>-</Td><Td>From Google Cloud Console</Td></tr>
            <tr><Td className="font-mono">SESSION_SECRET</Td><Td><Badge color="red">Yes</Badge></Td><Td>dev-secret</Td><Td>Session signing key. REQUIRED in production (server will not start without it). Generate with <code>openssl rand -hex 32</code></Td></tr>
            <tr><Td className="font-mono">OAUTH_REDIRECT_URI</Td><Td><Badge color="orange">Rec</Badge></Td><Td>localhost:8000/auth/callback</Td><Td>Callback URL registered with Google</Td></tr>
            <tr><Td className="font-mono">FRONTEND_URL</Td><Td><Badge color="orange">Rec</Badge></Td><Td>localhost:5173</Td><Td>Frontend URL (for post-login redirect and CORS)</Td></tr>
            <tr><Td className="font-mono">ALLOWED_DOMAIN</Td><Td><Badge color="gray">No</Badge></Td><Td>adkaora.com</Td><Td>Allowed email domain for login</Td></tr>
            <tr><Td className="font-mono">ANTHROPIC_API_KEY</Td><Td><Badge color="gray">No</Badge></Td><Td>-</Td><Td>If present, enables LLM analysis (Haiku/Sonnet)</Td></tr>
            <tr><Td className="font-mono">VNA_DB_PATH</Td><Td><Badge color="gray">No</Badge></Td><Td>data/vna_alerts.db</Td><Td>SQLite database path</Td></tr>
          </tbody>
        </table>

        <h4 className="mb-2 font-semibold text-slate-900">AWS Infrastructure (target)</h4>
        <ul className="list-disc space-y-1 pl-5">
          <li><strong>EC2:</strong> single instance (t3.medium sufficient). Docker Compose.</li>
          <li><strong>Volume:</strong> <code className="rounded bg-slate-100 px-1 text-xs">./data</code> mounted as bind volume for DB and parquet persistence.</li>
          <li><strong>Port:</strong> 8000 only. Frontend served by FastAPI. Reverse proxy (nginx/ALB) recommended for TLS.</li>
        </ul>
      </Section>

      {/* SECURITY */}
      <Section id="security" icon={Shield} title={t('docs.security')} open={openSections.has('security')} onToggle={toggle}>
        <div className="space-y-4">
          <div>
            <h4 className="font-semibold text-slate-900">Authentication</h4>
            <ul className="mt-1 list-disc space-y-1 pl-5">
              <li><strong>Google OAuth 2.0</strong> with OpenID Connect. Only <code className="rounded bg-slate-100 px-1 text-xs">@adkaora.com</code> emails.</li>
              <li>In-memory sessions (Python dict). Cookie <code className="rounded bg-slate-100 px-1 text-xs">session_id</code> with random token (32 bytes, urlsafe).</li>
              <li>Cookie flags: <code className="rounded bg-slate-100 px-1 text-xs">httponly=True</code>, <code className="rounded bg-slate-100 px-1 text-xs">samesite=lax</code>, <code className="rounded bg-slate-100 px-1 text-xs">secure=True</code> (prod only).</li>
              <li>Session TTL: 24 hours. After: session expires, cookie deleted, redirect to login.</li>
              <li><strong>Dev bypass:</strong> <code className="rounded bg-slate-100 px-1 text-xs">ENVIRONMENT=development</code> → no login, mock user <code className="text-xs">dev@localhost</code>.</li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold text-slate-900">Authorization</h4>
            <ul className="mt-1 list-disc space-y-1 pl-5">
              <li>Dependency <code className="rounded bg-slate-100 px-1 text-xs">require_auth</code> applied to all <code className="text-xs">/api/*</code> routes.</li>
              <li>Routes <code className="text-xs">/auth/*</code> excluded (required for login flow).</li>
              <li>No RBAC (all authenticated users have full access). Sufficient for teams &lt;20.</li>
              <li><code className="rounded bg-slate-100 px-1 text-xs">user_id</code> extracted from server-side session (<code className="text-xs">require_auth()</code>), never from request body.</li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold text-slate-900">CORS</h4>
            <ul className="mt-1 list-disc space-y-1 pl-5">
              <li><strong>Dev:</strong> <code className="rounded bg-slate-100 px-1 text-xs">allow_origins=["*"]</code> (Vite on a different port).</li>
              <li><strong>Prod:</strong> <code className="rounded bg-slate-100 px-1 text-xs">allow_origins=[FRONTEND_URL]</code> (same origin, but restricted for security).</li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold text-slate-900">Middleware</h4>
            <p>Stack (execution order): CORSMiddleware → SessionMiddleware → SlowAPI Rate Limiter → Route handlers.</p>
            <p className="mt-1">Rate limiting via SlowAPI: 5 backtests/hour, 10 admin/hour, 30 mutations/min, 60 GET/min.</p>
            <p className="mt-1">SessionMiddleware (Starlette) used for OAuth state during the redirect flow. Secret from env var.</p>
          </div>
        </div>

        <div className="mt-4 rounded-lg bg-amber-50 p-3">
          <p className="text-sm text-amber-800">
            <strong>Known limitations:</strong> in-memory sessions are lost on server restart (users must re-login).
            For high availability, migrate to Redis or cookie-based sessions. Not critical for a small team.
          </p>
        </div>
      </Section>

      {/* CONFIG */}
      <Section id="config" icon={Settings} title={t('docs.config')} open={openSections.has('config')} onToggle={toggle}>
        <p className="mb-4">File: <code className="rounded bg-slate-100 px-1 text-xs">config/alerting_rules.yaml</code> + <code className="rounded bg-slate-100 px-1 text-xs">config/revenue_share.yaml</code>. All system thresholds and parameters. <strong>v1.2</strong> adds 4 new sections (gross_margin, leading_indicator, cross_channel, revenue_share).</p>

        <h4 className="mb-3 mt-4 font-semibold text-slate-900">Core Sections (v1.0)</h4>
        <CodeBlock>{`revenue_anomaly:        # Rule A1 - drop thresholds
  P0: {drop_percent: -15, duration_hours: 2}
  P1: {drop_percent: -10, duration_hours: 2}
  P2: {drop_percent: -5,  duration_hours: 4}

drift_detection:        # Rule A2 - weekly drift (fallback)
  enabled: true
  window_days: 7
  threshold_percent: -8

near_zero:              # Rule A3 - near-zero
  revenue_threshold_eur: 100
  coverage_threshold: 0.05
  consecutive_periods: 3

data_gap:               # Rule A0 - missing data
  enabled: true
  max_gap_hours: 4
  severity: P1

triage:                 # Triage classification thresholds
  traffic_driven_threshold: -10   # ad requests drop %
  coverage_driven_threshold: -10  # coverage drop %

top_contributors:       # Contributor analysis
  top_n: 15
  min_quota_percent: 1

geo_clusters:           # Country → cluster mapping
  ITA: [IT]
  ES: [ES]
  LATAM: [BR, MX, AR, CO, CL, PE]
  PT: [PT]
  OTHER: [US, UK, FR, DE]

scheduling:
  interval_hours: 2               # A1+A3+A5+A6+A7 every 2h, A2 every 6h
  recheck_interval_minutes: 5     # Recheck queue every 5min
  channels: [GOOGLE_ADEX, OPEN_BIDDING, HB_MAGNITE, HB_PUBMATIC, TAM, DIRECT, DEAL]

data_sources:
  athena_timeout_seconds: 30
  athena_retry_count: 1          # 2 total attempts
  cache_ttl_hours: 24

top_publishers:         # 36 monitored publishers
  - vocento
  - prensaiberica
  - mondadori
  # ... (36 total)`}</CodeBlock>

        <h4 className="mb-3 mt-5 font-semibold text-slate-900">Phase 1: Drift Regression <Badge color="purple">New</Badge></h4>
        <CodeBlock>{`drift_regression:       # A2 drift with linear regression (runs before 7d fallback)
  enabled: true
  window_days_min: 14           # Minimum days for regression
  window_days_max: 30           # Maximum days for regression
  slope_threshold_percent_per_day: -2.0   # Trigger if slope ≤ -2%/day
  cumulative_drop_threshold_percent: -15.0  # AND cumulative drop ≥ -15%
  min_data_points: 10           # Minimum data points required`}</CodeBlock>
        <p className="mt-2 text-xs text-slate-600">
          <strong>Purpose:</strong> 14-30 day linear regression to detect gradual trends. Triggers only with a statistically significant fit (R² ≥ 0.5, p &lt; 0.05).
          Falls back to 7-day drift if regression does not trigger.
        </p>

        <h4 className="mb-3 mt-5 font-semibold text-slate-900">Phase 1: Comparative Alerting <Badge color="purple">New</Badge></h4>
        <CodeBlock>{`comparative_alerting:
  yesterday_comparison:
    enabled: true
    threshold_percent: -30        # Alert if -30% vs yesterday
    severity_mapping:
      below_minus_10: P2
      below_minus_20: P1
      below_minus_30: P0
  moving_average_14d:
    enabled: true
    divergence_threshold_percent: -25   # Alert if -25% vs MA 14d
    severity: P1
    sustained_hours: 3            # Must persist 3h`}</CodeBlock>
        <p className="mt-2 text-xs text-slate-600">
          <strong>Purpose:</strong> Yesterday comparison (same-hour) + 14-day moving average (same-weekday). Aligned with TAM&amp;Yield operational practices.
        </p>

        <h4 className="mb-3 mt-5 font-semibold text-slate-900">Phase 1: Weekend Schedule <Badge color="purple">New</Badge></h4>
        <CodeBlock>{`scheduling:
  weekend_schedule:
    enabled: true
    times_per_day: 2
    run_hours: [10, 18]           # CronTrigger Sat/Sun 10:00 and 18:00 UTC`}</CodeBlock>
        <p className="mt-2 text-xs text-slate-600">
          <strong>Purpose:</strong> Reduced weekend scheduling (2x/day instead of every 2h) to reduce ops load.
        </p>

        <h4 className="mb-3 mt-5 font-semibold text-slate-900">Phase 1: Dual Thresholds <Badge color="purple">New</Badge></h4>
        <CodeBlock>{`dual_thresholds:
  enabled: true
  attention_severity: P2-WATCH
  operational:                    # Operational thresholds (action required)
    revenue_drop_percent: -30
    yesterday_delta_percent: -30
    ma_14d_divergence_percent: -25
  attention:                      # Attention thresholds (monitoring)
    revenue_drop_percent: -15
    yesterday_delta_percent: -15
    ma_14d_divergence_percent: -12`}</CodeBlock>
        <p className="mt-2 text-xs text-slate-600">
          <strong>Purpose:</strong> Dual threshold system — operational (P0/P1/P2) vs attention (P2-WATCH). Separates urgent actions from monitoring signals.
        </p>

        <h4 className="mb-3 mt-5 font-semibold text-slate-900">Phase 2: Margin/eCPM Alert (A5) <Badge color="blue">New</Badge></h4>
        <CodeBlock>{`margin_alert:
  enabled: true
  ecpm_drop_thresholds:
    P1:
      drop_percent: -25           # P1 if eCPM ≤ -25%
      duration_hours: 3
    P2:
      drop_percent: -15           # P2 if eCPM ≤ -15%
      duration_hours: 4
  min_impressions: 1000           # Filters low-traffic hours
  baseline_weeks: 7`}</CodeBlock>
        <p className="mt-2 text-xs text-slate-600">
          <strong>Purpose:</strong> Detects pricing deterioration (eCPM drop). More lenient thresholds than revenue (-25%/-15%) for eCPM volatility.
        </p>

        <h4 className="mb-3 mt-5 font-semibold text-slate-900">Phase 2: Coverage Zero Alert (A6) <Badge color="blue">New</Badge></h4>
        <CodeBlock>{`coverage_zero_alert:
  enabled: true
  coverage_threshold: 0.001       # 0.1% - catches near-zero
  min_bacino: 100                 # Filters low-traffic
  consecutive_hours: 2
  baseline_weeks: 7
  severity: P1                    # Always P1 (complete coverage loss)`}</CodeBlock>
        <p className="mt-2 text-xs text-slate-600">
          <strong>Purpose:</strong> Detects zeroed/near-zero coverage. Always P1 (coverage loss = immediate revenue stop). Dedicated triage: GOOGLE_POLICY, MCM_CONFIG, ADS_TXT, TECHNICAL_ISSUE.
        </p>

        <h4 className="mb-3 mt-5 font-semibold text-slate-900">Phase 2: Pricing Rule Alert (A7) <Badge color="blue">New</Badge></h4>
        <CodeBlock>{`pricing_rule_alert:
  enabled: true
  correlation_strength: -0.7      # Trigger if correlation ≤ -0.7
  coverage_drop_threshold: -15
  cpm_spike_threshold: 20
  min_impressions: 500            # Lower than A5 (500 vs 1000)
  baseline_weeks: 7
  severity: P1                    # Always P1 (pricing error)`}</CodeBlock>
        <p className="mt-2 text-xs text-slate-600">
          <strong>Purpose:</strong> Detects pricing rule errors (coverage↓ + CPM↑ negatively correlated). Always P1 since it causes immediate revenue loss.
        </p>

        <h4 className="mb-3 mt-5 font-semibold text-slate-900">Phase 4: Slack Notifications <Badge color="green">New</Badge></h4>
        <CodeBlock>{`slack_notifications:
  webhook_url: "https://hooks.slack.com/services/..."  # Set via admin UI
  channel: "sentinel-alerts"
  immediate_severities: ["P0"]             # Immediate delivery
  digest_severities: ["P1", "P2"]          # Daily digest
  digest_time_utc: "08:00"                 # 08:00 UTC`}</CodeBlock>
        <p className="mt-2 text-xs text-slate-600">
          <strong>Purpose:</strong> Configures Slack webhook and notification routing. P0 immediate, P1/P2 in daily digest. Managed via <code className="rounded bg-slate-100 px-1 text-xs">PUT /api/admin/slack-config</code>.
        </p>

        <h4 className="mb-3 mt-5 font-semibold text-slate-900">v1.2: Gross Margin Alert (A8) <Badge color="red">New</Badge></h4>
        <CodeBlock>{`gross_margin_alert:
  enabled: true
  severity: P1                    # Always P1
  margin_deviation_threshold: 10  # Alert if gross_margin_pct deviates ≥ 10pp from expected
  min_revenue_eur: 50             # Filters publishers with negligible revenue
  baseline_weeks: 7`}</CodeBlock>
        <p className="mt-2 text-xs text-slate-600">
          <strong>Purpose:</strong> Monitors gross margin. Triggers when gross_margin_pct deviates significantly from the share_rate configured per publisher. Requires <code className="rounded bg-slate-100 px-1 text-xs">revenue_share.yaml</code>.
        </p>

        <h4 className="mb-3 mt-5 font-semibold text-slate-900">v1.2: Leading Indicator <Badge color="red">New</Badge></h4>
        <CodeBlock>{`leading_indicator:
  enabled: true
  metrics: [ctr, viewability]
  threshold_percent: -15          # P2-WATCH if ≤ -15% vs baseline
  severity: P2-WATCH
  baseline_weeks: 7
  min_impressions: 1000           # Filters low-traffic hours
  sustained_hours: 2              # Must persist for 2h`}</CodeBlock>
        <p className="mt-2 text-xs text-slate-600">
          <strong>Purpose:</strong> Detects CTR/Viewability deterioration as an early warning signal for revenue drops. Generates P2-WATCH for preventive monitoring.
        </p>

        <h4 className="mb-3 mt-5 font-semibold text-slate-900">v1.2: Cross-Channel Detection <Badge color="red">New</Badge></h4>
        <CodeBlock>{`cross_channel_detection:
  enabled: true
  direct_channel: DIRECT
  open_market_channels: [GOOGLE_ADEX, OPEN_BIDDING, HB_MAGNITE, HB_PUBMATIC]
  correlation_window_hours: 6
  direct_increase_threshold: 20   # DIRECT must grow ≥ 20%
  open_market_decrease_threshold: -10  # Open Market must drop ≤ -10%
  severity_downgrade: true        # Reduces Open Market alert severity`}</CodeBlock>
        <p className="mt-2 text-xs text-slate-600">
          <strong>Purpose:</strong> Detects DIRECT growing + Open Market declining pattern (active direct campaign). Annotates alerts and optionally reduces severity to avoid false positives.
        </p>

        <h4 className="mb-3 mt-5 font-semibold text-slate-900">v1.2: Revenue Share <Badge color="red">New</Badge></h4>
        <p className="mb-2 text-xs text-slate-600">Separate file: <code className="rounded bg-slate-100 px-1 text-xs">config/revenue_share.yaml</code></p>
        <CodeBlock>{`default_share_rate: 0.60          # 60% publisher, 40% Adkaora

publisher_overrides:
  mondadori: 0.65                 # Premium contract
  vocento: 0.55
  prensaiberica: 0.58
  # ... per-publisher share rates

gross_margin_expected:            # Expected gross margin (= 1 - share_rate)
  default: 40.0                   # 40% default margin
  tolerance_pp: 10                # Tolerance in percentage points`}</CodeBlock>
        <p className="mt-2 text-xs text-slate-600">
          <strong>Purpose:</strong> Configures per-publisher revenue share. Used by A8 to calculate expected gross_margin_pct and detect deviations. Default covers publishers without a specific override.
        </p>

        <div className="mt-4 rounded-lg bg-blue-50 p-3">
          <p className="text-sm text-blue-800">
            <strong>Hot reload:</strong> config is re-read on every alerting cycle. Edit the YAML and the next
            cycle will use the new values. No server restart needed (except slack_notifications which requires restart for webhook URL changes).
          </p>
        </div>
      </Section>

      {/* SCHEDULING */}
      <Section id="scheduling" icon={Clock} title={t('docs.scheduling')} open={openSections.has('scheduling')} onToggle={toggle}>
        <h4 className="mb-2 font-semibold text-slate-900">APScheduler (AsyncIO)</h4>
        <p className="mb-3">Four in-process scheduled jobs:</p>
        <table className="mb-4 w-full border-collapse text-xs">
          <thead><tr><Th>Job</Th><Th>Interval</Th><Th>Function</Th><Th>Description</Th></tr></thead>
          <tbody>
            <tr><Td className="font-mono">alerting_cycle</Td><Td>2h</Td><Td className="tabular-nums text-xs">run_alerting_cycle()</Td><Td>Runs A1+A3+A5+A6+A7+A8 pipeline for all 7 channels. GOOGLE_ADEX also has dedicated hourly scheduling.</Td></tr>
            <tr><Td className="font-mono">drift_cycle</Td><Td>6h</Td><Td className="tabular-nums text-xs">run_drift_cycle()</Td><Td>Runs A2 drift detection for all 7 channels</Td></tr>
            <tr><Td className="font-mono">recheck_queue</Td><Td>5 min</Td><Td className="tabular-nums text-xs">check_recheck_queue()</Td><Td>Processes queued rechecks (PENDING → COMPLETED/FAILED)</Td></tr>
            <tr><Td className="font-mono">daily_slack_digest</Td><Td>CronTrigger (08:00 UTC daily)</Td><Td className="tabular-nums text-xs">send_daily_digest()</Td><Td>Collects P1/P2/P2-WATCH alerts generated in the last 24h, sends a single Slack digest, marks pending_notifications as sent. Skips if no alerts. Manual endpoint: <code className="rounded bg-slate-100 px-1 text-xs">POST /api/admin/trigger-digest</code></Td></tr>
          </tbody>
        </table>

        <h4 className="mb-2 font-semibold text-slate-900">Health Check</h4>
        <p className="mb-3"><code className="rounded bg-slate-100 px-1 text-xs">GET /api/health</code> returns:</p>
        <CodeBlock>{`{
  "status": "healthy",     // "healthy" | "degraded"
  "version": "1.0.0",
  "db_ok": true,           // SQLite SELECT 1 check
  "scheduler_running": true,
  "timestamp": "2026-02-13T14:00:00Z"
}`}</CodeBlock>

        <h4 className="mb-2 font-semibold text-slate-900">Logging</h4>
        <ul className="list-disc space-y-1 pl-5">
          <li>Format: <code className="rounded bg-slate-100 px-1 text-xs">timestamp | level | module | message</code></li>
          <li>Each agent logs start/end with key metrics</li>
          <li>LLM errors logged as WARNING with automatic fallback</li>
          <li>Level configurable via <code className="rounded bg-slate-100 px-1 text-xs">LOG_LEVEL</code> env var (default: INFO)</li>
        </ul>

        <div className="mt-3 rounded-lg bg-green-50 p-3">
          <p className="text-sm text-green-800">
            <strong>Status:</strong> the scheduler invokes the LangGraph pipeline for A1+A3 every 2h and A2 every 6h.
            Graceful shutdown via SIGTERM handler (closes scheduler and DB cleanly).
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
          <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
          <p className="mt-1 text-slate-500">{subtitle}</p>
        </div>
        <div className="flex gap-2">
          <button onClick={expandAll} className="rounded border border-slate-200 px-3 py-1 text-xs text-slate-600 hover:bg-slate-50">Expand all</button>
          <button onClick={collapseAll} className="rounded border border-slate-200 px-3 py-1 text-xs text-slate-600 hover:bg-slate-50">Collapse all</button>
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        {children({ openSections, toggle })}
      </div>
    </div>
  )
}

export function OperationalDocsPage() {
  const { t } = useTranslation()
  return (
    <DocsPageShell
      title={t('docs.tab_operative_title')}
      subtitle={t('docs.tab_operative_subtitle')}
      sections={OP_SECTIONS}
      defaultOpen="alert-rules"
    >
      {({ openSections, toggle }) => <OperationalDocs openSections={openSections} toggle={toggle} t={t} />}
    </DocsPageShell>
  )
}

export function TechnicalDocsPage() {
  const { t } = useTranslation()
  return (
    <DocsPageShell
      title={t('docs.tab_technical_title')}
      subtitle={t('docs.tab_technical_subtitle')}
      sections={TECH_SECTIONS}
      defaultOpen="arch"
    >
      {({ openSections, toggle }) => <TechnicalDocs openSections={openSections} toggle={toggle} t={t} />}
    </DocsPageShell>
  )
}

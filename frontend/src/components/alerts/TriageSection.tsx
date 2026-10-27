import { ArrowDown, ArrowUp, Minus, GitBranch, AlertTriangle, TrendingUp } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { TriageBadge } from '../ui/Badge'
import { BASELINE_MISSING_COPY } from '../../lib/i18n-keys'
import { formatCurrency } from '../../lib/utils'
import type { Alert, Environment, EnvironmentMetrics } from '../../types/alert'
import { ScopeBadge } from '../ui/ScopeBadge'
import { ReferencePeriodFootnote } from '../ui/ReferencePeriodFootnote'
import { type GrossNetMode } from '../ui/GrossNetToggle'
import { GROSS_NET_LABELS, REV_SHARE_FACTOR } from '../../lib/i18n-keys'

interface TriageSectionProps {
  alert: Alert
  // B-1 iter-1: mode prop threaded from AlertDetailPage page-level state.
  // UI-SPEC §CORR-03 placement matrix line 404: TriageSection inherits mode
  // from AlertDetailPage; Revenue row multiplies by REV_SHARE_FACTOR when 'net'.
  // Bacino + Coverage rows are UNAFFECTED (impressions/ratios, not currency).
  mode: GrossNetMode
}

interface TriageRow {
  metric: string
  current: string
  baseline: string
  delta: string
  direction: 'up' | 'down' | 'flat'
}

export function TriageSection({ alert, mode }: TriageSectionProps) {
  // CORR-01 / RC-(e) closure: baseline_bacino + baseline_coverage are now
  // server-computed by Phase 11 API-03 (_compute_baseline_from_env_split in
  // backend/api/routes.py). The previous client-side heuristic
  // (revenue-ratio scale + flat coverage offset, capped at 0p95) is DELETED —
  // pattern intentionally rephrased to satisfy UI-SPEC AC #1 anti-creep grep.
  // Audit trail: .planning/intel/sentinel-2026-04-28/SYNTHESIS.md RC-(e),
  // .planning/STELLA-POLARE.md "anti-pattern PROIBITI" #5.

  // Compute current values for the table (these stay client-side — they
  // describe the alert FIRING state, not the baseline reference).
  //
  // Phase 17.2 HOTFIX-05 (B2 Marco 2026-05-19) — Path C root-cause fix:
  // the environment_splitter agent emits per-env keys with the `_current`
  // suffix (bacino_current, coverage_current, revenue_current, etc.), but
  // this consumer was reading m.bacino / m.coverage — undefined on every
  // payload → ?? 0 fallback → "Bacino + Coverage = 0" on all 238 snapshot
  // alerts. Fix: read the correct payload field names. The narrow Triage-
  // -specific shape (rather than a wholesale EnvironmentMetrics type
  // rename) keeps blast radius minimal; Tab 5 (EnvironmentSplitSection)
  // same-class drift is flagged in 17.2-05-DIAGNOSIS.md as Phase 17.3
  // candidate, NOT touched here.
  //
  // Defensive Path B layer: when env_split is genuinely empty (legacy
  // pre-Phase-11 alerts surfaced via ?include_deprecated=true, or future
  // splitter run failures emitting {}), substitute 'n/a' on the current
  // column instead of letting the empty-reduce produce a misleading "0".
  //
  // Note: `environment_split` carries sibling scalar keys like
  // `amp_drift_detected: true` alongside the per-env dicts. Filter to dict
  // entries before aggregating so the AMP drift flag is not counted as a
  // 4th environment (which would otherwise dilute avgCoverage by 1/4).
  const envEntriesRaw = alert.environment_split
    ? Object.entries(alert.environment_split)
    : []
  const envEntries = envEntriesRaw.filter(
    (entry): entry is [Environment, EnvironmentMetrics] =>
      typeof entry[1] === 'object' && entry[1] !== null,
  )
  const envSplitMissing = envEntries.length === 0
  // Phase 17.2 GAP-CLOSURE (2026-05-20): HOTFIX-05's defensive `?? m.bacino`
  // / `?? m.coverage` legacy fallbacks removed — the EnvironmentMetrics type
  // is now the canonical payload contract (bacino_current / coverage_current
  // are the only field names that ever existed in the wire payload), so the
  // narrow inline casts and dual-name fallbacks become dead code. Keep the
  // dict-only filter (envEntries above) so amp_drift_detected: bool sibling
  // scalars cannot poison the reduce.
  const totalBacino = envEntries.reduce((s, [, m]) => s + (m.bacino_current ?? 0), 0)
  const avgCoverage = envEntries.length > 0
    ? envEntries.reduce((s, [, m]) => s + (m.coverage_current ?? 0), 0) / envEntries.length
    : 0

  // Server-computed baselines (nullable per Phase 11 D-11.02-02 contract).
  const baselineBacino = alert.baseline_bacino
  const baselineCoverage = alert.baseline_coverage
  // WR-01 fix: treat literal 0 as missing for delta math. A baseline of 0
  // (freshly onboarded publisher, coverage-zero alert A6) would otherwise
  // produce `(current - 0) / 0` → Infinity, rendered raw as "Infinity%".
  // The dedicated A6 coverage-zero block below renders independently from
  // this guard (it gates on `alert.alert_rule === 'A6' && alert.coverage_zero_cause`),
  // so this widening does not regress the A6 path.
  const baselineMissing =
    baselineBacino == null ||
    baselineCoverage == null ||
    baselineBacino === 0 ||
    baselineCoverage === 0

  // CORR-03 / RC-(c): Revenue row is mode-aware per UI-SPEC §CORR-03
  // placement matrix line 404. Gross source uses ?? fallback matching
  // RevenueStatusSection D-14.04-D semantics. Delta % is mode-invariant.
  const revGrossCurrent = alert.revenue_gross ?? alert.revenue_current
  const revGrossBaseline = alert.revenue_baseline
  const revDisplayedCurrent = mode === 'net' ? revGrossCurrent * REV_SHARE_FACTOR : revGrossCurrent
  const revDisplayedBaseline = mode === 'net' ? revGrossBaseline * REV_SHARE_FACTOR : revGrossBaseline
  const revSuffix = mode === 'net' ? GROSS_NET_LABELS.netSuffix : GROSS_NET_LABELS.grossSuffix

  const rows: TriageRow[] = [
    {
      metric: `Revenue ${revSuffix}`,
      current: formatCurrency(revDisplayedCurrent),
      baseline: formatCurrency(revDisplayedBaseline),
      delta: `${alert.revenue_delta_pct > 0 ? '+' : ''}${alert.revenue_delta_pct.toFixed(1)}%`,
      direction: alert.revenue_delta_pct < 0 ? 'down' : alert.revenue_delta_pct > 0 ? 'up' : 'flat',
    },
    {
      metric: 'Bacino (Impressions)',
      // HOTFIX-05 Path B defensive: 'n/a' (not literal 0) when env_split missing
      current: envSplitMissing ? 'n/a' : totalBacino.toLocaleString(),
      baseline: baselineMissing ? '—' : (baselineBacino as number).toLocaleString(),
      delta: baselineMissing || envSplitMissing
        ? '—'
        : `${(((totalBacino - (baselineBacino as number)) / (baselineBacino as number)) * 100).toFixed(1)}%`,
      direction: baselineMissing || envSplitMissing
        ? 'flat'
        : totalBacino < (baselineBacino as number) ? 'down' : totalBacino > (baselineBacino as number) ? 'up' : 'flat',
    },
    {
      metric: 'Coverage',
      // HOTFIX-05 Path B defensive: 'n/a' (not '0.0%') when env_split missing
      current: envSplitMissing ? 'n/a' : `${(avgCoverage * 100).toFixed(1)}%`,
      baseline: baselineMissing ? '—' : `${((baselineCoverage as number) * 100).toFixed(1)}%`,
      delta: baselineMissing || envSplitMissing
        ? '—'
        : `${(((avgCoverage - (baselineCoverage as number)) / (baselineCoverage as number)) * 100).toFixed(1)}%`,
      direction: baselineMissing || envSplitMissing
        ? 'flat'
        : avgCoverage < (baselineCoverage as number) ? 'down' : avgCoverage > (baselineCoverage as number) ? 'up' : 'flat',
    },
  ]

  const DirectionIcon = ({ dir }: { dir: 'up' | 'down' | 'flat' }) => {
    if (dir === 'up') return <ArrowUp size={14} className="text-green-600" />
    if (dir === 'down') return <ArrowDown size={14} className="text-red-600" />
    return <Minus size={14} className="text-gray-400" />
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <GitBranch size={18} className="text-indigo-500" />
            Step 2: Triage
          </CardTitle>
          <div className="flex items-center gap-3">
            <ScopeBadge channel={alert.channel_group} />
            <TriageBadge triage={alert.triage_label} />
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="px-4 py-3 text-left font-medium text-gray-600">Metric</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">Current</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">Baseline</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">Delta</th>
                <th className="px-4 py-3 text-center font-medium text-gray-600">Direction</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.metric} className="border-b border-gray-100">
                  <td className="px-4 py-3 font-medium text-gray-900">{row.metric}</td>
                  <td className="px-4 py-3 text-right font-mono text-gray-700">{row.current}</td>
                  <td className={`px-4 py-3 text-right font-mono ${
                    row.baseline === '—' ? 'text-gray-400' : 'text-gray-500'
                  }`}>{row.baseline}</td>
                  <td
                    className={`px-4 py-3 text-right font-mono font-medium ${
                      row.delta === '—'
                        ? 'text-gray-400'
                        : row.direction === 'down' ? 'text-red-600' : row.direction === 'up' ? 'text-green-600' : 'text-gray-500'
                    }`}
                  >
                    {row.delta}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <DirectionIcon dir={row.direction} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <ReferencePeriodFootnote variant="inline" timestamp={alert.timestamp} className="mt-3 block" />
        {baselineMissing && (
          <p className="text-xs text-gray-500 mt-3">{BASELINE_MISSING_COPY}</p>
        )}
        {envSplitMissing && (
          <p className="text-xs text-gray-500 mt-1">
            Bacino + Coverage non disponibili per questo alert — environment_split mancante
            (alert pre-Phase 11 o splitter non eseguito).
          </p>
        )}
        {/* A6 Coverage-Zero Cause */}
        {alert.alert_rule === 'A6' && alert.coverage_zero_cause && (
          <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4">
            <div className="flex items-start gap-3">
              <AlertTriangle size={20} className="mt-0.5 text-amber-600" />
              <div className="flex-1">
                <h4 className="font-medium text-amber-900 mb-2">
                  Probable Cause: {getCoverageZeroCauseLabel(alert.coverage_zero_cause)}
                </h4>
                <p className="text-sm text-amber-800">
                  {getCoverageZeroCauseDescription(alert.coverage_zero_cause)}
                </p>
                {alert.coverage_zero_metrics && (
                  <div className="mt-3 grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-gray-600">Current Coverage:</span>
                      <span className="ml-2 font-semibold text-red-600">
                        {(alert.coverage_zero_metrics.current_coverage * 100).toFixed(2)}%
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-600">Baseline Coverage:</span>
                      <span className="ml-2 font-semibold">
                        {(alert.coverage_zero_metrics.baseline_coverage * 100).toFixed(2)}%
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* A7 Pricing Rule Correlation */}
        {alert.alert_rule === 'A7' && alert.pricing_rule_metrics && (
          <div className="mt-4 rounded-lg border border-purple-200 bg-purple-50 p-4">
            <div className="flex items-start gap-3">
              <TrendingUp size={20} className="mt-0.5 text-purple-600" />
              <div className="flex-1">
                <h4 className="font-medium text-purple-900 mb-2">
                  Pricing Rule Issue Detected
                </h4>
                <p className="text-sm text-purple-800 mb-3">
                  Coverage is dropping while CPM is spiking &mdash; indicates floor prices are too high and blocking valid demand.
                </p>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <div className="text-gray-600 mb-1">Coverage Change</div>
                    <div className="text-lg font-semibold text-red-600">
                      {alert.pricing_rule_metrics.coverage_delta_pct.toFixed(1)}%
                    </div>
                    <div className="text-xs text-gray-500">
                      {(alert.pricing_rule_metrics.baseline_coverage * 100).toFixed(1)}% &rarr; {(alert.pricing_rule_metrics.current_coverage * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-600 mb-1">CPM Change</div>
                    <div className="text-lg font-semibold text-green-600">
                      +{alert.pricing_rule_metrics.ecpm_delta_pct.toFixed(1)}%
                    </div>
                    <div className="text-xs text-gray-500">
                      &euro;{alert.pricing_rule_metrics.baseline_ecpm.toFixed(2)} &rarr; &euro;{alert.pricing_rule_metrics.current_ecpm.toFixed(2)}
                    </div>
                  </div>
                </div>
                <div className="mt-3 flex items-center justify-between border-t border-purple-200 pt-3 text-sm">
                  <span className="text-gray-600">Inverse Correlation Score:</span>
                  <span className="font-semibold">{alert.pricing_rule_metrics.correlation_score.toFixed(2)}</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function getCoverageZeroCauseLabel(cause: string): string {
  const labels: Record<string, string> = {
    GOOGLE_POLICY: 'Google Policy Violation',
    MCM_CONFIG: 'MCM Misconfiguration',
    ADS_TXT: 'Ads.txt Issue',
    TECHNICAL_ISSUE: 'Technical Issue',
  }
  return labels[cause] || cause
}

function getCoverageZeroCauseDescription(cause: string): string {
  const descriptions: Record<string, string> = {
    GOOGLE_POLICY: 'Sudden coverage drop to zero with stable bacino suggests a Google policy violation. Check Ad Manager for policy warnings or account suspensions.',
    MCM_CONFIG: 'Coverage at zero despite available bacino indicates MCM configuration issues. Verify publisher linking, revenue share settings, and inventory access.',
    ADS_TXT: 'Coverage zero with bacino changes suggests ads.txt validation failures. Check ads.txt file for missing or incorrect seller entries.',
    TECHNICAL_ISSUE: 'Coverage outage appears technical in nature. Check ad tag implementation, network connectivity, and integration logs.',
  }
  return descriptions[cause] || 'Unknown cause - manual investigation required.'
}

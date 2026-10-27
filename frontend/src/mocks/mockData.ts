import type {
  Alert,
  AlertSummary,
  MetricDataPoint,
  BacktestResult,
  HealthStatus,
} from '../types/alert'

// Helper to generate dates relative to now
function daysAgo(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() - days)
  return d.toISOString()
}

function hoursAgo(hours: number): string {
  const d = new Date()
  d.setHours(d.getHours() - hours)
  return d.toISOString()
}

// --- Alert Summaries (10 alerts) ---

export const mockAlertSummaries: AlertSummary[] = [
  {
    alert_id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    timestamp: hoursAgo(1),
    severity: 'P0',
    channel_group: 'GOOGLE',
    status: 'OPEN',
    alert_rule: 'A1',
    triage_label: 'TRAFFIC_DRIVEN',
    revenue_current: 85000,
    revenue_baseline: 104300,
    revenue_delta_pct: -18.5,
    created_at: hoursAgo(1),
  },
  {
    alert_id: 'b2c3d4e5-f6a7-8901-bcde-f12345678901',
    timestamp: hoursAgo(3),
    severity: 'P0',
    channel_group: 'OPEN_BIDDING',
    status: 'ACK',
    alert_rule: 'A1',
    triage_label: 'COVERAGE_DRIVEN',
    revenue_current: 41200,
    revenue_baseline: 53050,
    revenue_delta_pct: -22.3,
    created_at: hoursAgo(3),
  },
  {
    alert_id: 'c3d4e5f6-a7b8-9012-cdef-123456789012',
    timestamp: hoursAgo(6),
    severity: 'P1',
    channel_group: 'GOOGLE',
    status: 'OPEN',
    alert_rule: 'A2',
    triage_label: 'MIXED',
    revenue_current: 92300,
    revenue_baseline: 105730,
    revenue_delta_pct: -12.7,
    created_at: hoursAgo(6),
  },
  {
    alert_id: 'd4e5f6a7-b8c9-0123-defa-234567890123',
    timestamp: hoursAgo(8),
    severity: 'P1',
    channel_group: 'GOOGLE',
    status: 'RESOLVED',
    alert_rule: 'A1',
    triage_label: 'REVENUE_ONLY',
    revenue_current: 95400,
    revenue_baseline: 105800,
    revenue_delta_pct: -9.8,
    created_at: hoursAgo(8),
  },
  {
    alert_id: 'e5f6a7b8-c9d0-1234-efab-345678901234',
    timestamp: hoursAgo(12),
    severity: 'P2',
    channel_group: 'OPEN_BIDDING',
    status: 'OPEN',
    alert_rule: 'A0',
    triage_label: 'TRAFFIC_DRIVEN',
    revenue_current: 49200,
    revenue_baseline: 53030,
    revenue_delta_pct: -7.2,
    created_at: hoursAgo(12),
  },
  {
    alert_id: 'f6a7b8c9-d0e1-2345-fabc-456789012345',
    timestamp: daysAgo(1),
    severity: 'P0',
    channel_group: 'GOOGLE',
    status: 'RESOLVED',
    alert_rule: 'A3',
    triage_label: 'COVERAGE_DRIVEN',
    revenue_current: 78900,
    revenue_baseline: 105340,
    revenue_delta_pct: -25.1,
    created_at: daysAgo(1),
  },
  {
    alert_id: 'a7b8c9d0-e1f2-3456-abcd-567890123456',
    timestamp: daysAgo(1),
    severity: 'P1',
    channel_group: 'OPEN_BIDDING',
    status: 'ACK',
    alert_rule: 'A1',
    triage_label: 'MIXED',
    revenue_current: 45500,
    revenue_baseline: 53100,
    revenue_delta_pct: -14.3,
    created_at: daysAgo(1),
  },
  {
    alert_id: 'b8c9d0e1-f2a3-4567-bcde-678901234567',
    timestamp: daysAgo(2),
    severity: 'P2',
    channel_group: 'GOOGLE',
    status: 'RESOLVED',
    alert_rule: 'A2',
    triage_label: 'REVENUE_ONLY',
    revenue_current: 99700,
    revenue_baseline: 105600,
    revenue_delta_pct: -5.6,
    created_at: daysAgo(2),
  },
  {
    alert_id: 'c9d0e1f2-a3b4-5678-cdef-789012345678',
    timestamp: daysAgo(2),
    severity: 'P1',
    channel_group: 'GOOGLE',
    status: 'SNOOZED',
    alert_rule: 'A1',
    triage_label: 'TRAFFIC_DRIVEN',
    revenue_current: 94100,
    revenue_baseline: 105730,
    revenue_delta_pct: -11.0,
    created_at: daysAgo(2),
  },
  {
    alert_id: 'd0e1f2a3-b4c5-6789-defa-890123456789',
    timestamp: daysAgo(3),
    severity: 'P2',
    channel_group: 'OPEN_BIDDING',
    status: 'RESOLVED',
    alert_rule: 'A0',
    triage_label: 'COVERAGE_DRIVEN',
    revenue_current: 49700,
    revenue_baseline: 53100,
    revenue_delta_pct: -6.4,
    created_at: daysAgo(3),
  },
]

// --- Full Alert Details (3 detailed alerts) ---

export const mockAlertDetails: Record<string, Alert> = {
  'a1b2c3d4-e5f6-7890-abcd-ef1234567890': {
    alert_id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    timestamp: hoursAgo(1),
    severity: 'P0',
    channel_group: 'GOOGLE',
    status: 'OPEN',
    alert_rule: 'A1',
    revenue_current: 85200,
    revenue_baseline: 104500,
    revenue_delta_pct: -18.5,
    triage_label: 'TRAFFIC_DRIVEN',
    contributors: [
      {
        publisher_id: 'pub-001',
        publisher_name: 'Corriere della Sera',
        current_revenue: 12500,
        baseline_revenue: 18200,
        delta_absolute: -5700,
        delta_percent: -31.3,
        quota_of_drop: 0.295,
      },
      {
        publisher_id: 'pub-002',
        publisher_name: 'La Repubblica',
        current_revenue: 9800,
        baseline_revenue: 14100,
        delta_absolute: -4300,
        delta_percent: -30.5,
        quota_of_drop: 0.223,
      },
      {
        publisher_id: 'pub-003',
        publisher_name: 'Il Sole 24 Ore',
        current_revenue: 7200,
        baseline_revenue: 10500,
        delta_absolute: -3300,
        delta_percent: -31.4,
        quota_of_drop: 0.171,
      },
      {
        publisher_id: 'pub-004',
        publisher_name: 'Gazzetta dello Sport',
        current_revenue: 5400,
        baseline_revenue: 7100,
        delta_absolute: -1700,
        delta_percent: -23.9,
        quota_of_drop: 0.088,
      },
      {
        publisher_id: 'pub-005',
        publisher_name: 'ANSA',
        current_revenue: 4100,
        baseline_revenue: 5600,
        delta_absolute: -1500,
        delta_percent: -26.8,
        quota_of_drop: 0.078,
      },
      {
        publisher_id: 'pub-006',
        publisher_name: 'Fanpage.it',
        current_revenue: 3800,
        baseline_revenue: 4900,
        delta_absolute: -1100,
        delta_percent: -22.4,
        quota_of_drop: 0.057,
      },
      {
        publisher_id: 'pub-007',
        publisher_name: 'HuffPost Italia',
        current_revenue: 2900,
        baseline_revenue: 3700,
        delta_absolute: -800,
        delta_percent: -21.6,
        quota_of_drop: 0.041,
      },
    ],
    geo_breakdown: [
      {
        geo_cluster: 'ITA',
        current_revenue: 62100,
        baseline_revenue: 78500,
        delta_absolute: -16400,
        delta_percent: -20.9,
        contribution: 0.85,
      },
      {
        geo_cluster: 'ES',
        current_revenue: 15200,
        baseline_revenue: 17800,
        delta_absolute: -2600,
        delta_percent: -14.6,
        contribution: 0.13,
      },
      {
        geo_cluster: 'OTHER',
        current_revenue: 7900,
        baseline_revenue: 8200,
        delta_absolute: -300,
        delta_percent: -3.7,
        contribution: 0.02,
      },
    ],
    environment_split: {
      WEB: {
        revenue: 51100,
        baseline_revenue: 62700,
        delta_absolute: -11600,
        delta_percent: -18.5,
        bacino: 1250000,
        coverage: 0.82,
      },
      AMP: {
        revenue: 22400,
        baseline_revenue: 28600,
        delta_absolute: -6200,
        delta_percent: -21.7,
        bacino: 580000,
        coverage: 0.71,
      },
      APP: {
        revenue: 11700,
        baseline_revenue: 13200,
        delta_absolute: -1500,
        delta_percent: -11.4,
        bacino: 320000,
        coverage: 0.88,
      },
      UNKNOWN: {
        revenue: 0,
        baseline_revenue: 0,
        delta_absolute: 0,
        delta_percent: 0,
        bacino: 0,
        coverage: 0,
      },
    },
    insights: {
      summary:
        'Significant revenue drop of -18.5% driven primarily by traffic decline in Italian publishers. The drop is concentrated in the WEB and AMP environments, with top 3 publishers accounting for 69% of the total revenue loss.',
      insights: [
        'Traffic-driven pattern detected: bacino (impressions) dropped by ~20% across WEB and AMP environments',
        'Top 3 publishers (Corriere, Repubblica, Il Sole) contribute 69% of the total revenue drop',
        'AMP environment shows the steepest decline at -21.7%, suggesting potential AMP-specific issues',
        'Coverage remains relatively stable (71-88%), ruling out coverage-driven causes',
        'Geographic concentration: ITA accounts for 85% of the revenue impact',
      ],
      next_steps: [
        'Investigate traffic source changes for top 3 publishers in the last 24 hours',
        'Check for Google algorithm updates or Search Console warnings',
        'Review AMP validation status for affected publishers',
        'Monitor for recovery in the next 2-4 hours before escalating',
        'Consider reaching out to publisher partners if decline persists beyond 6 hours',
      ],
      cache_warning:
        'Data from the last 2 hours may reflect cached/delayed values. The Athena data pipeline has a ~90 minute lag for real-time metrics. Verify trends after the next data refresh cycle.',
    },
    execution_time_sec: 4.23,
    data_source: 'athena_realtime',
    created_at: hoursAgo(1),
    updated_at: hoursAgo(0.5),
    events: [
      {
        event_id: 1,
        alert_id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
        event_type: 'COMMENT',
        user_id: 'system',
        comment: 'Alert generated by automated monitoring pipeline',
        timestamp: hoursAgo(1),
      },
    ],
  },
  'b2c3d4e5-f6a7-8901-bcde-f12345678901': {
    alert_id: 'b2c3d4e5-f6a7-8901-bcde-f12345678901',
    timestamp: hoursAgo(3),
    severity: 'P0',
    channel_group: 'OPEN_BIDDING',
    status: 'ACK',
    alert_rule: 'A1',
    revenue_current: 42300,
    revenue_baseline: 54400,
    revenue_delta_pct: -22.3,
    triage_label: 'COVERAGE_DRIVEN',
    contributors: [
      {
        publisher_id: 'pub-010',
        publisher_name: 'El Pais Digital',
        current_revenue: 8200,
        baseline_revenue: 12400,
        delta_absolute: -4200,
        delta_percent: -33.9,
        quota_of_drop: 0.347,
      },
      {
        publisher_id: 'pub-011',
        publisher_name: 'Marca.com',
        current_revenue: 5600,
        baseline_revenue: 8100,
        delta_absolute: -2500,
        delta_percent: -30.9,
        quota_of_drop: 0.207,
      },
      {
        publisher_id: 'pub-012',
        publisher_name: 'ABC.es',
        current_revenue: 4300,
        baseline_revenue: 6200,
        delta_absolute: -1900,
        delta_percent: -30.6,
        quota_of_drop: 0.157,
      },
      {
        publisher_id: 'pub-013',
        publisher_name: 'LaVanguardia.com',
        current_revenue: 3100,
        baseline_revenue: 4000,
        delta_absolute: -900,
        delta_percent: -22.5,
        quota_of_drop: 0.074,
      },
      {
        publisher_id: 'pub-014',
        publisher_name: '20Minutos.es',
        current_revenue: 2800,
        baseline_revenue: 3500,
        delta_absolute: -700,
        delta_percent: -20.0,
        quota_of_drop: 0.058,
      },
    ],
    geo_breakdown: [
      {
        geo_cluster: 'ITA',
        current_revenue: 8500,
        baseline_revenue: 10200,
        delta_absolute: -1700,
        delta_percent: -16.7,
        contribution: 0.14,
      },
      {
        geo_cluster: 'ES',
        current_revenue: 28700,
        baseline_revenue: 37800,
        delta_absolute: -9100,
        delta_percent: -24.1,
        contribution: 0.75,
      },
      {
        geo_cluster: 'OTHER',
        current_revenue: 5100,
        baseline_revenue: 6400,
        delta_absolute: -1300,
        delta_percent: -20.3,
        contribution: 0.11,
      },
    ],
    environment_split: {
      WEB: {
        revenue: 24800,
        baseline_revenue: 30900,
        delta_absolute: -6100,
        delta_percent: -19.7,
        bacino: 890000,
        coverage: 0.65,
      },
      AMP: {
        revenue: 12100,
        baseline_revenue: 16500,
        delta_absolute: -4400,
        delta_percent: -26.7,
        bacino: 410000,
        coverage: 0.58,
      },
      APP: {
        revenue: 5400,
        baseline_revenue: 7000,
        delta_absolute: -1600,
        delta_percent: -22.9,
        bacino: 180000,
        coverage: 0.72,
      },
      UNKNOWN: {
        revenue: 0,
        baseline_revenue: 0,
        delta_absolute: 0,
        delta_percent: 0,
        bacino: 0,
        coverage: 0,
      },
    },
    insights: {
      summary:
        'Coverage-driven revenue decline of -22.3% in Open Bidding channel. Ad coverage has dropped significantly in AMP (58%) and WEB (65%), well below the 75% healthy threshold. Spanish publishers are most affected.',
      insights: [
        'Coverage-driven pattern: ad fill rates below healthy threshold across all environments',
        'AMP coverage at 58% is critically low, suggesting demand-side partner issues',
        'Open Bidding demand may be affected by DSP budget changes or bid adjustments',
        'Spanish market (ES) accounts for 75% of the revenue impact at -24.1%',
        'Top 2 publishers (El Pais, Marca) contribute 55% of total drop',
      ],
      next_steps: [
        'Review Open Bidding partner dashboard for bid/budget changes',
        'Check DSP-level fill rate reports for the last 6 hours',
        'Contact top demand partners if fill rate drop exceeds 6 hours',
        'Consider enabling backup demand sources for AMP inventory',
        'Schedule follow-up review in 4 hours',
      ],
      cache_warning: '',
    },
    execution_time_sec: 3.87,
    data_source: 'athena_realtime',
    created_at: hoursAgo(3),
    updated_at: hoursAgo(1),
    events: [
      {
        event_id: 1,
        alert_id: 'b2c3d4e5-f6a7-8901-bcde-f12345678901',
        event_type: 'COMMENT',
        user_id: 'system',
        comment: 'Alert generated by automated monitoring pipeline',
        timestamp: hoursAgo(3),
      },
      {
        event_id: 2,
        alert_id: 'b2c3d4e5-f6a7-8901-bcde-f12345678901',
        event_type: 'ACK',
        user_id: 'maria.rossi',
        comment: 'Investigating demand-side issues with OB partners',
        timestamp: hoursAgo(2),
      },
      {
        event_id: 3,
        alert_id: 'b2c3d4e5-f6a7-8901-bcde-f12345678901',
        event_type: 'COMMENT',
        user_id: 'maria.rossi',
        comment: 'Confirmed: DSP partner XYZ reduced bid floor by 40%. Reaching out to account team.',
        timestamp: hoursAgo(1.5),
      },
    ],
  },
  'c3d4e5f6-a7b8-9012-cdef-123456789012': {
    alert_id: 'c3d4e5f6-a7b8-9012-cdef-123456789012',
    timestamp: hoursAgo(6),
    severity: 'P1',
    channel_group: 'GOOGLE',
    status: 'OPEN',
    alert_rule: 'A2',
    revenue_current: 95400,
    revenue_baseline: 109300,
    revenue_delta_pct: -12.7,
    triage_label: 'MIXED',
    contributors: [
      {
        publisher_id: 'pub-020',
        publisher_name: 'Corriere della Sera',
        current_revenue: 14800,
        baseline_revenue: 18500,
        delta_absolute: -3700,
        delta_percent: -20.0,
        quota_of_drop: 0.266,
      },
      {
        publisher_id: 'pub-021',
        publisher_name: 'La Stampa',
        current_revenue: 6400,
        baseline_revenue: 8900,
        delta_absolute: -2500,
        delta_percent: -28.1,
        quota_of_drop: 0.180,
      },
      {
        publisher_id: 'pub-022',
        publisher_name: 'Sky TG24',
        current_revenue: 5100,
        baseline_revenue: 6800,
        delta_absolute: -1700,
        delta_percent: -25.0,
        quota_of_drop: 0.122,
      },
      {
        publisher_id: 'pub-023',
        publisher_name: 'Il Messaggero',
        current_revenue: 4200,
        baseline_revenue: 5400,
        delta_absolute: -1200,
        delta_percent: -22.2,
        quota_of_drop: 0.086,
      },
    ],
    geo_breakdown: [
      {
        geo_cluster: 'ITA',
        current_revenue: 72800,
        baseline_revenue: 83200,
        delta_absolute: -10400,
        delta_percent: -12.5,
        contribution: 0.75,
      },
      {
        geo_cluster: 'ES',
        current_revenue: 16100,
        baseline_revenue: 18500,
        delta_absolute: -2400,
        delta_percent: -13.0,
        contribution: 0.17,
      },
      {
        geo_cluster: 'OTHER',
        current_revenue: 6500,
        baseline_revenue: 7600,
        delta_absolute: -1100,
        delta_percent: -14.5,
        contribution: 0.08,
      },
    ],
    environment_split: {
      WEB: {
        revenue: 58200,
        baseline_revenue: 65800,
        delta_absolute: -7600,
        delta_percent: -11.6,
        bacino: 1480000,
        coverage: 0.79,
      },
      AMP: {
        revenue: 25800,
        baseline_revenue: 30100,
        delta_absolute: -4300,
        delta_percent: -14.3,
        bacino: 620000,
        coverage: 0.74,
      },
      APP: {
        revenue: 11400,
        baseline_revenue: 13400,
        delta_absolute: -2000,
        delta_percent: -14.9,
        bacino: 350000,
        coverage: 0.85,
      },
      UNKNOWN: {
        revenue: 0,
        baseline_revenue: 0,
        delta_absolute: 0,
        delta_percent: 0,
        bacino: 0,
        coverage: 0,
      },
    },
    insights: {
      summary:
        'Mixed-driver revenue decline of -12.7% in Google channel detected by drift rule A2. Both traffic and coverage show moderate declines, suggesting a broader market shift rather than a single root cause.',
      insights: [
        'Mixed pattern: both bacino and coverage show moderate declines across environments',
        'Drift detected by A2 rule (sustained decline over 4+ hours)',
        'ITA market is the primary contributor at 75% of total impact',
        'AMP coverage at 74% is approaching the warning threshold',
        'No single publisher accounts for more than 27% of the drop',
      ],
      next_steps: [
        'Monitor trend over next 2 hours for signs of recovery or acceleration',
        'Cross-reference with market-wide data from Google Ad Manager reports',
        'Check for seasonal or day-of-week patterns in historical data',
        'Review AMP coverage trend specifically',
      ],
      cache_warning:
        'Some metrics reflect cached values from the previous data refresh cycle (~45 min ago).',
    },
    execution_time_sec: 5.12,
    data_source: 'athena_historical',
    created_at: hoursAgo(6),
    updated_at: hoursAgo(4),
    events: [],
  },
}

// --- Revenue trend data points (7 days) ---

export function generateTrendData(baselineCenter: number): MetricDataPoint[] {
  const points: MetricDataPoint[] = []
  const now = Date.now()
  const dayMs = 24 * 60 * 60 * 1000

  for (let i = 7; i >= 0; i--) {
    const ts = new Date(now - i * dayMs)
    // Baseline is fairly stable with small variation
    const baseline = baselineCenter * (0.95 + Math.random() * 0.1)
    // Revenue tracks baseline but dips in recent days
    const dropFactor = i <= 1 ? 0.78 + Math.random() * 0.05 : 0.95 + Math.random() * 0.08
    const revenue = baseline * dropFactor

    points.push({
      timestamp: ts.toISOString(),
      revenue: Math.round(revenue),
      baseline_revenue: Math.round(baseline),
      bacino: Math.round(1200000 + Math.random() * 200000 - (i <= 1 ? 250000 : 0)),
      coverage: Number((0.78 + Math.random() * 0.1 - (i <= 1 ? 0.08 : 0)).toFixed(3)),
    })
  }
  return points
}

export const mockTrendData = generateTrendData(105000)

// --- Backtest Results ---

export const mockBacktestResults: BacktestResult[] = [
  {
    backtest_id: 'bt-001',
    date_range: { start: daysAgo(14), end: daysAgo(7), step_hours: 6 },
    total_checks: 28,
    alerts_generated: 5,
    alerts: mockAlertSummaries.slice(0, 5),
    status: 'COMPLETED',
  },
  {
    backtest_id: 'bt-002',
    date_range: { start: daysAgo(30), end: daysAgo(14), step_hours: 12 },
    total_checks: 32,
    alerts_generated: 8,
    alerts: mockAlertSummaries.slice(2, 10),
    status: 'COMPLETED',
  },
]

// --- Health Status ---

export const mockHealthStatus: HealthStatus = {
  status: 'healthy',
  version: '1.0.0',
  db_ok: true,
  scheduler_running: true,
  timestamp: hoursAgo(0.1),
  pipeline_metrics: { last_24h_runs: 12, last_24h_failure_rate: 0.0 },
}

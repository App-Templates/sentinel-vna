export type Severity = 'P0' | 'P1' | 'P2';
export type AlertStatus = 'OPEN' | 'ACK' | 'RESOLVED' | 'SNOOZED';
export type AlertRule = 'A0' | 'A1' | 'A2' | 'A3' | 'A5' | 'A6' | 'A7';
export type ChannelGroup = 'GOOGLE' | 'OPEN_BIDDING';
export type TriageLabel = 'TRAFFIC_DRIVEN' | 'COVERAGE_DRIVEN' | 'MIXED' | 'REVENUE_ONLY';
export type Environment = 'WEB' | 'AMP' | 'APP';
export type GeoCluster = 'ITA' | 'ES' | 'OTHER';
export type EventType = 'ACK' | 'RESOLVE' | 'RECHECK' | 'COMMENT';

export type FeedbackType =
  | 'REAL'
  | 'FALSE_POSITIVE_MANUAL_INTERVENTION'
  | 'FALSE_POSITIVE_SEASONALITY'
  | 'FALSE_POSITIVE_TECHNICAL'
  | 'FALSE_POSITIVE_PUBLISHER_CAMPAIGN'
  | 'FALSE_POSITIVE_MARKET_NOISE';

export interface Feedback {
  feedback_id: number;
  alert_id: string;
  user_id: string;
  feedback_type: FeedbackType;
  comment?: string;
  timestamp: string;
}

export interface Assignment {
  assignment_id: number;
  alert_id: string;
  assigned_to: string;
  assigned_by: string;
  assigned_at: string;
}

export type InterventionType =
  | 'PRICING_RULE'
  | 'FLOOR_CPM'
  | 'DEMAND_PARTNER_CONFIG'
  | 'AD_UNIT_SETUP'
  | 'POLICY_CHANGE'
  | 'OTHER';

export interface Intervention {
  intervention_id: number;
  timestamp: string;
  publisher_id: string;
  intervention_type: InterventionType;
  description: string;
  value_before?: string;
  value_after?: string;
  user_id: string;
  created_at: string;
}

export interface Alert {
  alert_id: string;
  timestamp: string;
  severity: Severity;
  channel_group: ChannelGroup;
  status: AlertStatus;
  alert_rule: AlertRule;
  revenue_current: number;
  revenue_baseline: number;
  revenue_delta_pct: number;
  triage_label: TriageLabel;
  contributors: Contributor[];
  geo_breakdown: GeoBreakdown[];
  environment_split: Record<Environment, EnvironmentMetrics>;
  insights: AlertInsights;
  execution_time_sec: number;
  data_source: string;
  config_version?: string;
  created_at: string;
  updated_at: string;
  events: AlertEvent[];
  drift_regression?: DriftRegression;
  yesterday_comparison?: YesterdayComparison;
  moving_average_14d?: MovingAverage14d;

  // Phase 2 fields (new alert types)
  margin_metrics?: MarginMetrics;
  coverage_zero_metrics?: CoverageZeroMetrics;
  coverage_zero_cause?: CoverageZeroCause;
  pricing_rule_metrics?: PricingRuleMetrics;

  // Phase 3 fields (operator workflow)
  feedbacks?: Feedback[];
  assignment?: Assignment;
  interventions?: Intervention[];
}

export type CoverageZeroCause = 'GOOGLE_POLICY' | 'MCM_CONFIG' | 'ADS_TXT' | 'TECHNICAL_ISSUE';

export interface MarginMetrics {
  current_ecpm: number;
  baseline_ecpm: number;
  ecpm_delta_pct: number;
  current_impressions: number;
  baseline_impressions: number;
  severity: string;
}

export interface CoverageZeroMetrics {
  current_coverage: number;
  baseline_coverage: number;
  current_impressions: number;
  current_bacino: number;
  baseline_impressions: number;
  baseline_bacino: number;
  severity: string;
}

export interface PricingRuleMetrics {
  current_coverage: number;
  baseline_coverage: number;
  coverage_delta_pct: number;
  current_ecpm: number;
  baseline_ecpm: number;
  ecpm_delta_pct: number;
  correlation_score: number;
  current_impressions: number;
  baseline_impressions: number;
  severity: string;
}

export interface AlertSummary {
  alert_id: string;
  timestamp: string;
  severity: Severity;
  channel_group: ChannelGroup;
  status: AlertStatus;
  alert_rule: AlertRule;
  triage_label: TriageLabel;
  revenue_current: number;
  revenue_baseline: number;
  revenue_delta_pct: number;
  created_at: string;
  assignment?: Assignment;
}

export interface Contributor {
  publisher_id: string;
  publisher_name: string;
  current_revenue: number;
  baseline_revenue: number;
  delta_absolute: number;
  delta_percent: number;
  quota_of_drop: number;
}

export interface GeoBreakdown {
  geo_cluster: GeoCluster;
  current_revenue: number;
  baseline_revenue: number;
  delta_absolute: number;
  delta_percent: number;
  contribution: number;
}

export interface EnvironmentMetrics {
  revenue: number;
  baseline_revenue: number;
  delta_absolute: number;
  delta_percent: number;
  bacino: number;
  coverage: number;
}

export interface AlertInsights {
  summary: string;
  insights: string[];
  next_steps: string[];
  cache_warning: string;
}

export interface DriftRegression {
  slope_pct_per_day: number;
  cumulative_drop_pct: number;
  r_squared: number;
  days_analyzed: number;
  projection_7d_pct: number;
}

export interface YesterdayComparison {
  same_hours_revenue_yesterday: number;
  current_hour_revenue: number;
  delta_pct: number;
  triggered: boolean;
  severity: string;
}

export interface MovingAverage14d {
  avg_revenue_14d: number;
  current_revenue: number;
  delta_pct: number;
  divergence_hours: number;
  triggered: boolean;
  severity: string;
}

export interface AlertEvent {
  event_id: number;
  alert_id: string;
  event_type: EventType;
  user_id: string;
  comment: string | null;
  timestamp: string;
}

export interface MetricDataPoint {
  timestamp: string;
  revenue: number;
  bacino: number;
  coverage: number;
  baseline_revenue?: number;
}

export interface BacktestResult {
  backtest_id: string;
  date_range: { start: string; end: string; step_hours: number };
  total_checks: number;
  alerts_generated: number;
  alerts: AlertSummary[];
  status: string;
  error?: string;
}

export interface HealthStatus {
  status: string;
  version: string;
  db_ok: boolean;
  scheduler_running: boolean;
  timestamp: string;
  pipeline_metrics?: {
    last_24h_runs: number;
    last_24h_failure_rate: number;
  };
}

export type Severity = 'P0' | 'P1' | 'P2';
export type AlertStatus = 'OPEN' | 'ACK' | 'RESOLVED' | 'SNOOZED';
export type AlertRule = 'A0' | 'A1' | 'A2' | 'A3';
export type ChannelGroup = 'GOOGLE' | 'OPEN_BIDDING';
export type TriageLabel = 'TRAFFIC_DRIVEN' | 'COVERAGE_DRIVEN' | 'MIXED' | 'REVENUE_ONLY';
export type Environment = 'WEB' | 'AMP' | 'APP';
export type GeoCluster = 'ITA' | 'ES' | 'OTHER';
export type EventType = 'ACK' | 'RESOLVE' | 'RECHECK' | 'COMMENT';

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

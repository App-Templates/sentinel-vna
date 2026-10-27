export interface PublisherSummary {
  publisher_id: string
  country: string
  dominant_geo: string
  total_revenue: number
  revenue_share_pct: number
  ecpm: number
  total_impressions: number
  total_bacino: number
  avg_coverage: number
  avg_marginality: number
  fill_rate: number
  google_pct: number
  trend_4w: number | null
}

export interface WeeklyKpi {
  week: number
  week_start: string
  week_end: string
  seasonal_period: string | null
  revenue: number
  revenue_gross?: number
  impressions: number
  bacino: number
  coverage: number
  ecpm: number
  clicks?: number
  viewable_impressions?: number
  ctr?: number
  viewability?: number
  rpm?: number
  gross_margin_pct?: number
  floor_cpm?: number
  revenue_by_channel?: Record<string, number>
  // YoY (present only when compare_prev_year=true and publisher is top 35)
  prev_revenue?: number
  prev_impressions?: number
  prev_bacino?: number
  prev_coverage?: number
  prev_ecpm?: number
  delta_revenue_pct?: number | null
  delta_ecpm_pct?: number | null
  delta_bacino_pct?: number | null
  delta_coverage_pct?: number | null
}

export interface GeoShare {
  geo_cluster: string
  revenue: number
  share_pct: number
}

export interface EnvShare {
  environment: string
  revenue: number
  share_pct: number
}

export interface YoYSummary {
  prev_year: number
  total_revenue_delta_pct: number | null
  ecpm_delta_pct: number | null
  weeks_with_data: number
}

export interface PublisherDetail {
  publisher_id: string
  year: number
  has_recurring_patterns?: boolean
  weekly_kpis: WeeklyKpi[]
  geo_breakdown: GeoShare[]
  environment_breakdown: EnvShare[]
  yoy_summary?: YoYSummary
}

export interface EcpmOptimizationWindow {
  period_id: string
  period_label: string
  weeks: number[]
  date_range: string
  signal: 'RAISE' | 'LOWER' | 'NEUTRAL'
  avg_ecpm: number
  delta_pct: number
  rationale: string
  driver?: DriverType
  bacino_delta_pct?: number
  coverage_delta_pct?: number
  impressions_delta_pct?: number
  revenue_delta_pct?: number
  driver_explanation?: string
  prev_year_driver?: DriverType
  consistency_score?: number | null
}

export interface EcpmWeeklyDetail {
  week: number
  week_start: string
  week_end: string
  ecpm: number
  delta_pct: number
  signal: string
  period: string | null
}

export interface EcpmAnalysis {
  publisher_id: string
  year: number
  yearly_avg_ecpm: number
  optimization_windows: EcpmOptimizationWindow[]
  weekly_ecpm_detail: EcpmWeeklyDetail[]
}

export type DriverType =
  | 'DEMAND_DRIVEN'
  | 'SUPPLY_SQUEEZE'
  | 'FILL_EFFECT'
  | 'VOLUME_DRIVEN'
  | 'SEASONAL_DEMAND'
  | 'MIXED'

export interface RecurringPattern {
  id: string
  label: string
  weeks: number[]
  week_range_label: string
  signal: 'RAISE' | 'LOWER' | 'NEUTRAL'
  avg_ecpm_2024: number
  avg_ecpm_2025: number
  avg_delta_pct_2024: number
  avg_delta_pct_2025: number
  consistency_score: number
  rationale: string
  driver?: DriverType
  bacino_delta_pct_avg?: number
  coverage_delta_pct_avg?: number
  impressions_delta_pct_avg?: number
  revenue_delta_pct_avg?: number
  driver_explanation?: string
}

export interface HiddenPattern {
  id: string
  label: string
  weeks: number[]
  week_range_label: string
  metric: string
  signal: 'UP' | 'DOWN'
  avg_delta_pct_2024: number
  avg_delta_pct_2025: number
  consistency_score: number
  ecpm_during_period: 'FLAT' | 'UP' | 'DOWN'
  business_impact: string
  weekly_revenue_impact_eur?: number
  reliability_score?: number
}

export interface DangerZone {
  id: string
  label: string
  weeks: number[]
  week_range_label: string
  ecpm_delta_pct: number
  coverage_delta_pct: number
  bacino_delta_pct?: number
  severity: 'HIGH' | 'MEDIUM'
  explanation: string
  reliability_score?: number
}

export interface YearlyAvg {
  ecpm_2024: number | null
  ecpm_2025: number | null
  bacino_2024?: number | null
  bacino_2025?: number | null
  coverage_2024?: number | null
  coverage_2025?: number | null
  impressions_2024?: number | null
  impressions_2025?: number | null
  revenue_2024?: number | null
  revenue_2025?: number | null
}

export interface RecurringPatternsResponse {
  publisher_id: string
  ecpm_patterns: RecurringPattern[]
  hidden_patterns: HiddenPattern[]
  danger_zones: DangerZone[]
  yearly_avg: YearlyAvg | null
}

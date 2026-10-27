import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { Alert, AlertSummary, MetricDataPoint, HealthStatus, BacktestResult, FeedbackType, InterventionType } from '../types/alert'
import type { PublisherSummary, PublisherDetail, EcpmAnalysis, RecurringPatternsResponse } from '../types/publisher'

const BASE_URL = '/api'

async function fetchJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    ...init,
  })
  if (res.status === 401) {
    window.location.reload()
    throw new Error('Session expired')
  }
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`)
  }
  return res.json()
}

// --- Auth Hook ---

export interface AuthUser {
  email: string
  name: string
  picture: string
}

export function useAuth() {
  return useQuery<AuthUser>({
    queryKey: ['auth'],
    queryFn: async () => {
      const res = await fetch('/auth/me', { credentials: 'include' })
      if (!res.ok) throw new Error('Not authenticated')
      return res.json()
    },
    retry: false,
    staleTime: 5 * 60_000,
  })
}

// --- Query Hooks ---

export interface AlertFilters {
  severity?: string
  status?: string
  channel_group?: string
  triage_label?: string
  from_date?: string
  to_date?: string
  assigned_to?: string
}

interface AlertsResponse {
  alerts: AlertSummary[]
  total: number
  limit: number
  offset: number
}

// Map frontend filter keys to backend query parameter names
const FILTER_KEY_MAP: Record<string, string> = {
  channel_group: 'channel',
  from_date: 'date_from',
  to_date: 'date_to',
}

export function useAlerts(filters?: AlertFilters) {
  const params = new URLSearchParams()
  if (filters) {
    Object.entries(filters).forEach(([key, value]) => {
      if (value) params.set(FILTER_KEY_MAP[key] ?? key, value)
    })
  }
  const query = params.toString()
  const url = `/alerts${query ? `?${query}` : ''}`

  return useQuery<AlertSummary[]>({
    queryKey: ['alerts', filters],
    queryFn: async () => {
      const resp = await fetchJSON<AlertsResponse>(url)
      return resp.alerts
    },
    refetchInterval: 30_000,
  })
}

interface AlertDetailResponse {
  alert: Alert
}

export function useAlert(alertId: string | undefined) {
  return useQuery<Alert>({
    queryKey: ['alert', alertId],
    queryFn: async () => {
      const resp = await fetchJSON<AlertDetailResponse>(`/alerts/${alertId}`)
      return resp.alert
    },
    enabled: !!alertId,
  })
}

export function useAlertTrend(alertId: string | undefined) {
  return useQuery<MetricDataPoint[]>({
    queryKey: ['alertTrend', alertId],
    queryFn: async () => {
      const resp = await fetchJSON<{ trend: MetricDataPoint[] }>(`/alerts/${alertId}/trend`)
      return resp.trend
    },
    enabled: !!alertId,
  })
}

export function useHealth() {
  return useQuery<HealthStatus>({
    queryKey: ['health'],
    queryFn: () => fetchJSON<HealthStatus>('/health'),
    refetchInterval: 60_000,
  })
}

export function useBacktestResults() {
  return useQuery<BacktestResult[]>({
    queryKey: ['backtest'],
    queryFn: async () => {
      const resp = await fetchJSON<{ results: BacktestResult[] }>('/backtest')
      return resp.results
    },
  })
}

// --- Admin Hooks ---

export function useDataSources() {
  return useQuery({ queryKey: ['datasources'], queryFn: () => fetchJSON('/admin/datasources') })
}

export function useUpdateDataSources() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (config: Record<string, unknown>) => fetchJSON('/admin/datasources', { method: 'POST', body: JSON.stringify(config) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['datasources'] })
  })
}

export function useTestDataSource() {
  return useMutation({
    mutationFn: (params: { source: string }) =>
      fetchJSON('/admin/datasources/test', { method: 'POST', body: JSON.stringify(params) })
  })
}

// --- Mutation Hooks ---

export function useAckAlert() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (alertId: string) =>
      fetchJSON(`/alerts/${alertId}/ack`, {
        method: 'POST',
        body: JSON.stringify({}),
      }),
    onSuccess: (_data, alertId) => {
      queryClient.invalidateQueries({ queryKey: ['alert', alertId] })
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
    },
  })
}

export function useResolveAlert() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (alertId: string) =>
      fetchJSON(`/alerts/${alertId}/resolve`, {
        method: 'POST',
        body: JSON.stringify({}),
      }),
    onSuccess: (_data, alertId) => {
      queryClient.invalidateQueries({ queryKey: ['alert', alertId] })
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
    },
  })
}

export function useRecheckAlert() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (alertId: string) =>
      fetchJSON(`/alerts/${alertId}/recheck`, {
        method: 'POST',
        body: JSON.stringify({}),
      }),
    onSuccess: (_data, alertId) => {
      queryClient.invalidateQueries({ queryKey: ['alert', alertId] })
    },
  })
}

export function useAddComment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ alertId, comment }: { alertId: string; comment: string }) =>
      fetchJSON(`/alerts/${alertId}/comment`, {
        method: 'POST',
        body: JSON.stringify({ comment }),
      }),
    onSuccess: (_data, { alertId }) => {
      queryClient.invalidateQueries({ queryKey: ['alert', alertId] })
    },
  })
}

export function useRunBacktest() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (params: { start_date: string; end_date: string; step_hours: number }) =>
      fetchJSON<BacktestResult>('/backtest', {
        method: 'POST',
        body: JSON.stringify(params),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backtest'] })
    },
  })
}

// --- Publisher Hooks ---

export function useTopPublishers(year = 2026, month?: number, limit = 50) {
  const file = month ? `top_${year}_${String(month).padStart(2, '0')}` : `top_${year}`
  return useQuery({
    queryKey: ['publishers', year, month, limit],
    queryFn: () =>
      fetchJSON<{ publishers: PublisherSummary[] }>(
        `/publishers/${file}`
      ).then((r) => r.publishers),
  })
}

export function usePublisherWeeklyKpis(
  publisherId: string | undefined,
  year = 2025,
  comparePrevYear = false,
) {
  return useQuery({
    queryKey: ['publisher-kpis', publisherId, year, comparePrevYear],
    queryFn: () =>
      fetchJSON<PublisherDetail>(
        `/publishers/${publisherId}/weekly-kpis?year=${year}&compare_prev_year=${comparePrevYear}`
      ),
    enabled: !!publisherId,
  })
}

export function usePublisherEcpmAnalysis(publisherId: string | undefined, year = 2025) {
  return useQuery({
    queryKey: ['publisher-ecpm', publisherId, year],
    queryFn: () =>
      fetchJSON<EcpmAnalysis>(`/publishers/${publisherId}/ecpm-analysis?year=${year}`),
    enabled: !!publisherId,
  })
}

export function usePublisherRecurringPatterns(publisherId: string | undefined) {
  return useQuery({
    queryKey: ['publisher-recurring-patterns', publisherId],
    queryFn: async () => {
      const resp = await fetchJSON<RecurringPatternsResponse>(`/publishers/${publisherId}/recurring-patterns`)
      // Normalize: backend may return legacy "patterns" key instead of "ecpm_patterns"
      const raw = resp as unknown as Record<string, unknown>
      if (!resp.ecpm_patterns && raw.patterns) {
        resp.ecpm_patterns = raw.patterns as RecurringPatternsResponse['ecpm_patterns']
      }
      if (!resp.hidden_patterns) resp.hidden_patterns = []
      if (!resp.danger_zones) resp.danger_zones = []
      return resp
    },
    enabled: !!publisherId,
  })
}

// --- Revenue Status 24h Hook ---

export interface RevenueHourData {
  hour: number
  revenue: number
  baseline: number
  delta_pct: number | null
}

export interface PrevYearData {
  date: string
  day_of_week: string
  total_revenue: number
  delta_pct: number
  hours?: number[]
}

export interface RevenueStatus24hResponse {
  date: string
  day_of_week: string
  hours: RevenueHourData[]
  total_revenue: number
  total_baseline: number
  total_delta_pct: number | null
  prev_year: PrevYearData | null
  available_dates?: string[]
}

export function useRevenueStatus24h(date?: string) {
  const path = date
    ? `/metrics/revenue-status-24h/${date}`
    : '/metrics/revenue-status-24h'
  return useQuery<RevenueStatus24hResponse>({
    queryKey: ['revenue-status-24h', date],
    queryFn: () => fetchJSON<RevenueStatus24hResponse>(path),
    staleTime: 5 * 60_000,
  })
}

// --- Alerting Rules Hooks ---

export function useAlertingRules() {
  return useQuery({
    queryKey: ['alerting-rules'],
    queryFn: () => fetchJSON<Record<string, unknown>>('/admin/alerting-rules'),
  })
}

export function useUpdateAlertingRules() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (rules: Record<string, unknown>) =>
      fetchJSON('/admin/alerting-rules', { method: 'PUT', body: JSON.stringify(rules) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['alerting-rules'] }),
  })
}

// --- Slack Configuration Hooks ---

export interface SlackConfig {
  webhook_url: string
  channel: string
  immediate_severities: string[]
  digest_severities: string[]
  digest_time_utc: string
}

export function useSlackConfig() {
  return useQuery<SlackConfig>({
    queryKey: ['slack-config'],
    queryFn: () => fetchJSON<SlackConfig>('/admin/slack-config'),
  })
}

export function useUpdateSlackConfig() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (config: Partial<SlackConfig>) =>
      fetchJSON('/admin/slack-config', { method: 'PUT', body: JSON.stringify(config) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['slack-config'] }),
  })
}

export function useTestSlackWebhook() {
  return useMutation({
    mutationFn: (params: { webhook_url: string }) =>
      fetchJSON<{ success: boolean; message: string }>('/admin/test-slack', { method: 'POST', body: JSON.stringify(params) }),
  })
}

// --- Operator Workflow Hooks (Phase 3) ---

export function useSubmitFeedback() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ alertId, feedbackType, comment }: { alertId: string; feedbackType: FeedbackType; comment?: string }) => {
      const res = await fetch(`${BASE_URL}/alerts/${alertId}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ feedback_type: feedbackType, comment }),
      })
      if (!res.ok) throw new Error('Failed to submit feedback')
      return res.json()
    },
    onSuccess: (_data, { alertId }) => {
      queryClient.invalidateQueries({ queryKey: ['alert', alertId] })
    },
  })
}

export function useAssignAlert() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ alertId, assignedTo }: { alertId: string; assignedTo: string }) => {
      const res = await fetch(`${BASE_URL}/alerts/${alertId}/assign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ assigned_to: assignedTo }),
      })
      if (!res.ok) throw new Error('Failed to assign alert')
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alert'] })
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
    },
  })
}

export function useUnassignAlert() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (alertId: string) => {
      const res = await fetch(`${BASE_URL}/alerts/${alertId}/assign`, {
        method: 'DELETE',
        credentials: 'include',
      })
      if (!res.ok) throw new Error('Failed to unassign')
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alert'] })
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
    },
  })
}

export function useCreateIntervention() {
  return useMutation({
    mutationFn: async (data: { timestamp: string; publisher_id: string; intervention_type: InterventionType; description: string; value_before?: string; value_after?: string }) => {
      const res = await fetch(`${BASE_URL}/interventions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(data),
      })
      if (!res.ok) throw new Error('Failed to create intervention')
      return res.json()
    },
  })
}

export function useLinkIntervention() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ alertId, interventionId }: { alertId: string; interventionId: number }) => {
      const res = await fetch(`${BASE_URL}/alerts/${alertId}/link-intervention`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ intervention_id: interventionId }),
      })
      if (!res.ok) throw new Error('Failed to link intervention')
      return res.json()
    },
    onSuccess: (_data, { alertId }) => {
      queryClient.invalidateQueries({ queryKey: ['alert', alertId] })
    },
  })
}

export function usePublisherFeedbackHistory(publisherId?: string) {
  return useQuery({
    queryKey: ['publisher-feedback', publisherId],
    queryFn: async () => {
      if (!publisherId) return { feedbacks: [], total: 0 }
      const res = await fetch(`${BASE_URL}/publishers/${publisherId}/feedback-history?limit=50`, {
        credentials: 'include',
      })
      if (!res.ok) throw new Error('Failed to load feedback history')
      return res.json()
    },
    enabled: !!publisherId,
  })
}

import { useState, useEffect } from 'react'
import { Database, Cloud, Monitor, CheckCircle, XCircle, Loader2, SlidersHorizontal, Save } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Skeleton } from '../components/ui/Skeleton'
import {
  useDataSources,
  useUpdateDataSources,
  useTestDataSource,
  useAlertingRules,
  useUpdateAlertingRules,
  useSlackConfig,
  useUpdateSlackConfig,
  useTestSlackWebhook,
} from '../api/client'

interface ParquetInfo {
  hourly_path: string
  hourly_status: string
  hourly_rows: number
  hourly_date_range: string[]
  daily_channel_path: string
  daily_channel_status: string
  daily_channel_rows: number
  daily_channel_date_range: string[]
  daily_adrequests_path: string
  daily_adrequests_status: string
  daily_adrequests_rows: number
  daily_adrequests_date_range: string[]
}

interface AthenaConfig {
  region: string
  database: string
  workgroup: string
  s3_output: string
  enabled?: boolean
  status?: string
}

interface GamConfig {
  network_code: string
  credentials_path: string
  enabled?: boolean
  status?: string
}

interface DataSourcesConfig {
  active_source: string
  parquet?: ParquetInfo
  athena?: AthenaConfig
  gam?: GamConfig
  scheduler?: {
    running: boolean
    interval_hours: number
    recheck_interval_minutes: number
  }
}

/* ============================================================
   Data Sources Page
   ============================================================ */

export function DataSourcesPage() {
  const { data, isLoading, error } = useDataSources()
  const updateMutation = useUpdateDataSources()
  const testMutation = useTestDataSource()

  const config = data as DataSourcesConfig | undefined

  const [activeSource, setActiveSource] = useState<string>('')
  const [athenaConfig, setAthenaConfig] = useState<AthenaConfig>({
    region: '',
    database: '',
    workgroup: '',
    s3_output: '',
  })
  const [gamConfig, setGamConfig] = useState<GamConfig>({
    network_code: '',
    credentials_path: '',
  })
  const [initialized, setInitialized] = useState(false)

  // Sync remote state into local state once loaded
  if (config && !initialized) {
    setActiveSource(config.active_source ?? 'parquet')
    if (config.athena) {
      setAthenaConfig(config.athena)
    }
    if (config.gam) {
      setGamConfig(config.gam)
    }
    setInitialized(true)
  }

  function handleSave() {
    updateMutation.mutate({
      active_source: activeSource,
      athena: athenaConfig,
      gam: gamConfig,
    })
  }

  function handleTestAthena() {
    testMutation.mutate({ source: 'athena' })
  }

  function handleTestGam() {
    testMutation.mutate({ source: 'gam' })
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-64" />
        <Skeleton className="h-48" />
      </div>
    )
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-red-500">Failed to load data source configuration.</p>
          <p className="mt-2 text-sm text-slate-400">Make sure the backend is running and the admin endpoints are available.</p>
        </CardContent>
      </Card>
    )
  }

  const parquet = config?.parquet
  const scheduler = config?.scheduler

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
        <Database size={24} />
        Data Sources
      </h1>

      {/* Data Sources */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database size={18} />
            Data Sources
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Active Source Selector */}
          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-slate-700">Active Source:</label>
            <select
              value={activeSource}
              onChange={(e) => setActiveSource(e.target.value)}
              className="cursor-pointer rounded-md border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:bg-slate-100 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="parquet">Parquet</option>
              <option value="athena">AWS Athena</option>
              <option value="gam">Google Ad Manager</option>
            </select>
          </div>

          {/* Parquet Files */}
          <div className="rounded-lg border border-slate-200 p-4">
            <h4 className="mb-3 text-sm font-semibold text-slate-700">Parquet Files</h4>
            {parquet ? (
              <div className="space-y-2">
                {([
                  { label: 'Hourly', path: parquet.hourly_path, status: parquet.hourly_status, rows: parquet.hourly_rows, dateRange: parquet.hourly_date_range },
                  { label: 'Daily Channel', path: parquet.daily_channel_path, status: parquet.daily_channel_status, rows: parquet.daily_channel_rows, dateRange: parquet.daily_channel_date_range },
                  { label: 'Daily AdRequests', path: parquet.daily_adrequests_path, status: parquet.daily_adrequests_status, rows: parquet.daily_adrequests_rows, dateRange: parquet.daily_adrequests_date_range },
                ] as const).map((file) => (
                  <div key={file.label} className="flex items-center gap-2 text-sm">
                    {file.status === 'loaded' ? (
                      <CheckCircle size={16} className="shrink-0 text-green-500" />
                    ) : (
                      <XCircle size={16} className="shrink-0 text-red-500" />
                    )}
                    <span className="font-semibold text-slate-700">{file.label}</span>
                    <span className="font-mono text-slate-600">{file.path}</span>
                    {file.status === 'loaded' && (
                      <span className="text-slate-400">
                        {file.rows?.toLocaleString()} rows{file.dateRange?.length === 2 ? `, ${file.dateRange[0]} - ${file.dateRange[1]}` : ''}
                      </span>
                    )}
                    {file.status !== 'loaded' && (
                      <span className="text-red-400">{file.status}</span>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-400">No parquet file information available.</p>
            )}
          </div>

          {/* AWS Athena */}
          <div className="rounded-lg border border-slate-200 p-4">
            <div className="mb-3 flex items-center justify-between">
              <h4 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                <Cloud size={16} />
                AWS Athena
              </h4>
              {activeSource !== 'athena' && (
                <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-500">Not Active</span>
              )}
            </div>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <InputField
                label="Region"
                value={athenaConfig.region}
                onChange={(v) => setAthenaConfig({ ...athenaConfig, region: v })}
                placeholder="eu-west-1"
              />
              <InputField
                label="Database"
                value={athenaConfig.database}
                onChange={(v) => setAthenaConfig({ ...athenaConfig, database: v })}
                placeholder="revenue_db"
              />
              <InputField
                label="Workgroup"
                value={athenaConfig.workgroup}
                onChange={(v) => setAthenaConfig({ ...athenaConfig, workgroup: v })}
                placeholder="primary"
              />
              <InputField
                label="S3 Output"
                value={athenaConfig.s3_output}
                onChange={(v) => setAthenaConfig({ ...athenaConfig, s3_output: v })}
                placeholder="s3://bucket/athena-results/"
              />
            </div>
            <div className="mt-3">
              <Button
                variant="outline"
                size="sm"
                onClick={handleTestAthena}
                disabled={testMutation.isPending}
              >
                {testMutation.isPending ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : null}
                Test Connection
              </Button>
              {testMutation.isSuccess && testMutation.variables?.source === 'athena' && (
                <span className="ml-2 text-sm text-green-600">Connection successful</span>
              )}
              {testMutation.isError && testMutation.variables?.source === 'athena' && (
                <span className="ml-2 text-sm text-red-600">Connection failed</span>
              )}
            </div>
          </div>

          {/* Google Ad Manager */}
          <div className="rounded-lg border border-slate-200 p-4">
            <div className="mb-3 flex items-center justify-between">
              <h4 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                <Monitor size={16} />
                Google Ad Manager
              </h4>
              {activeSource !== 'gam' && (
                <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-500">Not Active</span>
              )}
            </div>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <InputField
                label="Network Code"
                value={gamConfig.network_code}
                onChange={(v) => setGamConfig({ ...gamConfig, network_code: v })}
                placeholder="12345678"
              />
              <InputField
                label="Credentials Path"
                value={gamConfig.credentials_path}
                onChange={(v) => setGamConfig({ ...gamConfig, credentials_path: v })}
                placeholder="/path/to/credentials.json"
              />
            </div>
            <div className="mt-3">
              <Button
                variant="outline"
                size="sm"
                onClick={handleTestGam}
                disabled={testMutation.isPending}
              >
                {testMutation.isPending ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : null}
                Test Connection
              </Button>
              {testMutation.isSuccess && testMutation.variables?.source === 'gam' && (
                <span className="ml-2 text-sm text-green-600">Connection successful</span>
              )}
              {testMutation.isError && testMutation.variables?.source === 'gam' && (
                <span className="ml-2 text-sm text-red-600">Connection failed</span>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Scheduler */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Monitor size={18} />
            Scheduler
          </CardTitle>
        </CardHeader>
        <CardContent>
          {scheduler ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm">
                <span className="font-medium text-slate-700">Status:</span>
                <span className="flex items-center gap-1">
                  {scheduler.running ? (
                    <CheckCircle size={14} className="text-green-500" />
                  ) : (
                    <XCircle size={14} className="text-red-500" />
                  )}
                  <span>{scheduler.running ? 'Running' : 'Stopped'}</span>
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <span className="font-medium text-slate-700">A1+A3 (Revenue Anomaly + Near-Zero):</span>
                <span className="text-slate-600">Every 2 hours</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <span className="font-medium text-slate-700">A2 (Drift Detection):</span>
                <span className="text-slate-600">Every 6 hours</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <span className="font-medium text-slate-700">Recheck (open alerts):</span>
                <span className="text-slate-600">Every 5 minutes</span>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-400">Scheduler information not available.</p>
          )}
        </CardContent>
      </Card>

      {/* Save Button */}
      <div className="flex items-center gap-3">
        <Button onClick={handleSave} disabled={updateMutation.isPending}>
          {updateMutation.isPending ? (
            <Loader2 size={14} className="animate-spin" />
          ) : null}
          Save Configuration
        </Button>
        {updateMutation.isSuccess && (
          <span className="text-sm text-green-600">Configuration saved successfully.</span>
        )}
        {updateMutation.isError && (
          <span className="text-sm text-red-600">Failed to save configuration.</span>
        )}
      </div>
    </div>
  )
}

/* ============================================================
   Alerting Rules Page
   ============================================================ */

interface A1Level {
  drop_percent: number
  duration_hours: number
}

interface RulesFormState {
  // A1
  p0: A1Level
  p1: A1Level
  p2: A1Level
  // A2
  a2_enabled: boolean
  a2_window_days: number
  a2_threshold_percent: number
  // A3
  a3_revenue_threshold_eur: number
  a3_coverage_threshold: number
  a3_consecutive_periods: number
  // Triage
  triage_traffic_driven: number
  triage_coverage_driven: number
  // Top Contributors
  top_n: number
  min_quota_percent: number
}

function parseRules(data: Record<string, unknown>): RulesFormState {
  // Backend returns flat structure: { revenue_anomaly: { P0: {...}, P1: {...} }, drift_detection: {...}, ... }
  const a1 = (data.revenue_anomaly ?? {}) as Record<string, Record<string, number>>
  const a2 = (data.drift_detection ?? {}) as Record<string, unknown>
  const a3 = (data.near_zero ?? {}) as Record<string, unknown>
  const triage = (data.triage ?? {}) as Record<string, unknown>
  const contributors = (data.top_contributors ?? {}) as Record<string, unknown>

  return {
    p0: {
      drop_percent: a1.P0?.drop_percent ?? -15,
      duration_hours: a1.P0?.duration_hours ?? 2,
    },
    p1: {
      drop_percent: a1.P1?.drop_percent ?? -10,
      duration_hours: a1.P1?.duration_hours ?? 2,
    },
    p2: {
      drop_percent: a1.P2?.drop_percent ?? -5,
      duration_hours: a1.P2?.duration_hours ?? 4,
    },
    a2_enabled: (a2.enabled as boolean) ?? true,
    a2_window_days: (a2.window_days as number) ?? 7,
    a2_threshold_percent: (a2.threshold_percent as number) ?? -8,
    a3_revenue_threshold_eur: (a3.revenue_threshold_eur as number) ?? 100,
    a3_coverage_threshold: (a3.coverage_threshold as number) ?? 0.05,
    a3_consecutive_periods: (a3.consecutive_periods as number) ?? 3,
    triage_traffic_driven: (triage.traffic_driven_threshold as number) ?? -10,
    triage_coverage_driven: (triage.coverage_driven_threshold as number) ?? -10,
    top_n: (contributors.top_n as number) ?? 15,
    min_quota_percent: (contributors.min_quota_percent as number) ?? 1,
  }
}

function buildPayload(form: RulesFormState): Record<string, unknown> {
  // Backend expects flat structure at top level (no "rules" wrapper, no "levels" nesting)
  return {
    revenue_anomaly: {
      P0: { drop_percent: form.p0.drop_percent, duration_hours: form.p0.duration_hours },
      P1: { drop_percent: form.p1.drop_percent, duration_hours: form.p1.duration_hours },
      P2: { drop_percent: form.p2.drop_percent, duration_hours: form.p2.duration_hours },
    },
    drift_detection: {
      enabled: form.a2_enabled,
      window_days: form.a2_window_days,
      threshold_percent: form.a2_threshold_percent,
    },
    near_zero: {
      revenue_threshold_eur: form.a3_revenue_threshold_eur,
      coverage_threshold: form.a3_coverage_threshold,
      consecutive_periods: form.a3_consecutive_periods,
    },
    triage: {
      traffic_driven_threshold: form.triage_traffic_driven,
      coverage_driven_threshold: form.triage_coverage_driven,
    },
    top_contributors: {
      top_n: form.top_n,
      min_quota_percent: form.min_quota_percent,
    },
  }
}

export function AlertingRulesPage() {
  const { data, isLoading, error } = useAlertingRules()
  const saveMutation = useUpdateAlertingRules()

  const [form, setForm] = useState<RulesFormState | null>(null)
  const [initialized, setInitialized] = useState(false)

  useEffect(() => {
    if (data && !initialized) {
      setForm(parseRules(data))
      setInitialized(true)
    }
  }, [data, initialized])

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-20" />
        <Skeleton className="h-48" />
        <Skeleton className="h-32" />
      </div>
    )
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-red-500">Failed to load alerting rules.</p>
          <p className="mt-2 text-sm text-slate-400">Make sure the backend is running and the admin endpoints are available.</p>
        </CardContent>
      </Card>
    )
  }

  if (!form) return null

  const update = (patch: Partial<RulesFormState>) => setForm((prev) => prev ? { ...prev, ...patch } : prev)

  function handleSave() {
    if (!form) return
    saveMutation.mutate(buildPayload(form))
  }

  const version = (data as Record<string, unknown>)?.version as string | undefined
  const lastUpdated = (data as Record<string, unknown>)?.last_updated as string | undefined

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
        <SlidersHorizontal size={24} />
        Alerting Rules
      </h1>

      {/* Info */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-4">
            {version && (
              <span className="rounded bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                Version: {version}
              </span>
            )}
            {lastUpdated && (
              <span className="rounded bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                Last Updated: {lastUpdated}
              </span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Revenue Anomaly (A1) */}
      <Card>
        <CardHeader>
          <CardTitle>Revenue Anomaly (A1)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <SeverityRow
            label="P0"
            color="bg-red-100 text-red-700"
            dropPercent={form.p0.drop_percent}
            durationHours={form.p0.duration_hours}
            onDropChange={(v) => update({ p0: { ...form.p0, drop_percent: v } })}
            onDurationChange={(v) => update({ p0: { ...form.p0, duration_hours: v } })}
          />
          <SeverityRow
            label="P1"
            color="bg-orange-100 text-orange-700"
            dropPercent={form.p1.drop_percent}
            durationHours={form.p1.duration_hours}
            onDropChange={(v) => update({ p1: { ...form.p1, drop_percent: v } })}
            onDurationChange={(v) => update({ p1: { ...form.p1, duration_hours: v } })}
          />
          <SeverityRow
            label="P2"
            color="bg-yellow-100 text-yellow-700"
            dropPercent={form.p2.drop_percent}
            durationHours={form.p2.duration_hours}
            onDropChange={(v) => update({ p2: { ...form.p2, drop_percent: v } })}
            onDurationChange={(v) => update({ p2: { ...form.p2, duration_hours: v } })}
          />
        </CardContent>
      </Card>

      {/* Drift Detection (A2) */}
      <Card>
        <CardHeader>
          <CardTitle>Drift Detection (A2)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="a2-enabled"
                checked={form.a2_enabled}
                onChange={(e) => update({ a2_enabled: e.target.checked })}
                className="h-4 w-4 rounded border-slate-200 text-blue-600 focus:ring-blue-500"
              />
              <label htmlFor="a2-enabled" className="text-sm font-medium text-slate-700">
                Enabled
              </label>
            </div>
            <NumericField
              label="Window days"
              value={form.a2_window_days}
              step={1}
              onChange={(v) => update({ a2_window_days: v })}
            />
            <NumericField
              label="Threshold %"
              value={form.a2_threshold_percent}
              step={0.5}
              onChange={(v) => update({ a2_threshold_percent: v })}
            />
          </div>
        </CardContent>
      </Card>

      {/* Near Zero (A3) */}
      <Card>
        <CardHeader>
          <CardTitle>Near Zero (A3)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <NumericField
              label="Revenue threshold EUR"
              value={form.a3_revenue_threshold_eur}
              step={10}
              onChange={(v) => update({ a3_revenue_threshold_eur: v })}
            />
            <NumericField
              label="Coverage threshold"
              value={form.a3_coverage_threshold}
              step={0.01}
              onChange={(v) => update({ a3_coverage_threshold: v })}
            />
            <NumericField
              label="Consecutive periods"
              value={form.a3_consecutive_periods}
              step={1}
              onChange={(v) => update({ a3_consecutive_periods: v })}
            />
          </div>
        </CardContent>
      </Card>

      {/* Triage */}
      <Card>
        <CardHeader>
          <CardTitle>Triage</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <NumericField
              label="Traffic driven threshold %"
              value={form.triage_traffic_driven}
              step={0.5}
              onChange={(v) => update({ triage_traffic_driven: v })}
            />
            <NumericField
              label="Coverage driven threshold %"
              value={form.triage_coverage_driven}
              step={0.5}
              onChange={(v) => update({ triage_coverage_driven: v })}
            />
          </div>
        </CardContent>
      </Card>

      {/* Top Contributors */}
      <Card>
        <CardHeader>
          <CardTitle>Top Contributors</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <NumericField
              label="Top N"
              value={form.top_n}
              step={1}
              onChange={(v) => update({ top_n: v })}
            />
            <NumericField
              label="Min quota %"
              value={form.min_quota_percent}
              step={0.5}
              onChange={(v) => update({ min_quota_percent: v })}
            />
          </div>
        </CardContent>
      </Card>

      {/* Save Button */}
      <div className="flex items-center gap-3">
        <Button onClick={handleSave} disabled={saveMutation.isPending}>
          {saveMutation.isPending ? (
            <Loader2 size={14} className="animate-spin" />
          ) : (
            <Save size={14} />
          )}
          Save Configuration
        </Button>
        {saveMutation.isSuccess && (
          <span className="text-sm text-green-600">Configuration saved successfully.</span>
        )}
        {saveMutation.isError && (
          <span className="text-sm text-red-600">Error saving configuration.</span>
        )}
      </div>
    </div>
  )
}

/* ============================================================
   Shared sub-components
   ============================================================ */

function SeverityRow({
  label,
  color,
  dropPercent,
  durationHours,
  onDropChange,
  onDurationChange,
}: {
  label: string
  color: string
  dropPercent: number
  durationHours: number
  onDropChange: (v: number) => void
  onDurationChange: (v: number) => void
}) {
  return (
    <div className="flex items-center gap-4">
      <span className={`inline-block w-10 rounded px-2 py-0.5 text-center text-xs font-bold ${color}`}>
        {label}
      </span>
      <NumericField
        label="Drop %"
        value={dropPercent}
        step={0.5}
        onChange={onDropChange}
      />
      <NumericField
        label="Duration hours"
        value={durationHours}
        step={1}
        onChange={onDurationChange}
      />
    </div>
  )
}

function NumericField({
  label,
  value,
  step,
  onChange,
}: {
  label: string
  value: number
  step: number
  onChange: (value: number) => void
}) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-slate-500">{label}</label>
      <input
        type="number"
        value={value}
        step={step}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
        className="w-full rounded-md border border-slate-200 px-3 py-1.5 text-sm transition-colors duration-150 hover:border-slate-300 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
      />
    </div>
  )
}

function InputField({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
}) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-slate-500">{label}</label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-md border border-slate-200 px-3 py-1.5 text-sm transition-colors duration-150 hover:border-slate-300 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
      />
    </div>
  )
}

/* ============================================================
   Slack Configuration Page
   ============================================================ */

export function SlackConfigPage() {
  const { data, isLoading, error } = useSlackConfig()
  const updateMutation = useUpdateSlackConfig()
  const testMutation = useTestSlackWebhook()

  const [webhookUrl, setWebhookUrl] = useState('')
  const [channel, setChannel] = useState('')
  const [immediateSeverities, setImmediateSeverities] = useState<string[]>([])
  const [digestSeverities, setDigestSeverities] = useState<string[]>([])
  const [digestTime, setDigestTime] = useState('')
  const [initialized, setInitialized] = useState(false)

  // Sync remote state into local state once loaded
  useEffect(() => {
    if (data && !initialized) {
      setWebhookUrl(data.webhook_url ?? '')
      setChannel(data.channel ?? 'sentinel-alerts')
      setImmediateSeverities(data.immediate_severities ?? ['P0'])
      setDigestSeverities(data.digest_severities ?? ['P1', 'P2'])
      setDigestTime(data.digest_time_utc ?? '08:00')
      setInitialized(true)
    }
  }, [data, initialized])

  function handleSave() {
    updateMutation.mutate({
      webhook_url: webhookUrl,
      channel,
      immediate_severities: immediateSeverities,
      digest_severities: digestSeverities,
      digest_time_utc: digestTime,
    })
  }

  function handleTest() {
    if (!webhookUrl) {
      return
    }
    testMutation.mutate({ webhook_url: webhookUrl })
  }

  function toggleSeverity(severity: string, list: string[], setter: (val: string[]) => void) {
    if (list.includes(severity)) {
      setter(list.filter((s) => s !== severity))
    } else {
      setter([...list, severity])
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-64" />
      </div>
    )
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-red-500">Failed to load Slack configuration.</p>
          <p className="mt-2 text-sm text-slate-400">Make sure the backend is running and the admin endpoints are available.</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
        <Monitor size={24} />
        Slack Notifications
      </h1>

      <Card>
        <CardHeader>
          <CardTitle>Slack Configuration</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Webhook URL */}
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Webhook URL</label>
            <input
              type="text"
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
              placeholder="https://hooks.slack.com/services/..."
              className="w-full rounded-md border border-slate-200 px-3 py-1.5 text-sm transition-colors duration-150 hover:border-slate-300 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
            />
          </div>

          {/* Channel */}
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Channel</label>
            <input
              type="text"
              value={channel}
              onChange={(e) => setChannel(e.target.value)}
              placeholder="sentinel-alerts"
              className="w-full rounded-md border border-slate-200 px-3 py-1.5 text-sm transition-colors duration-150 hover:border-slate-300 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
            />
          </div>

          {/* Immediate Severities */}
          <div>
            <label className="mb-2 block text-xs font-medium text-slate-500">Immediate Notification (sent as soon as detected)</label>
            <div className="flex gap-3">
              {(['P0', 'P1', 'P2'] as const).map((sev) => (
                <label key={sev} className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={immediateSeverities.includes(sev)}
                    onChange={() => toggleSeverity(sev, immediateSeverities, setImmediateSeverities)}
                    className="h-4 w-4 rounded border-slate-200 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-sm text-slate-700">{sev}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Digest Severities */}
          <div>
            <label className="mb-2 block text-xs font-medium text-slate-500">Daily Digest (grouped in daily summary)</label>
            <div className="flex gap-3">
              {(['P0', 'P1', 'P2'] as const).map((sev) => (
                <label key={sev} className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={digestSeverities.includes(sev)}
                    onChange={() => toggleSeverity(sev, digestSeverities, setDigestSeverities)}
                    className="h-4 w-4 rounded border-slate-200 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-sm text-slate-700">{sev}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Digest Time */}
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Digest Time (UTC)</label>
            <input
              type="time"
              value={digestTime}
              onChange={(e) => setDigestTime(e.target.value)}
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* Test Connection */}
          <div className="border-t border-slate-200 pt-4">
            <Button
              variant="outline"
              size="sm"
              onClick={handleTest}
              disabled={testMutation.isPending || !webhookUrl}
            >
              {testMutation.isPending ? (
                <Loader2 size={14} className="animate-spin" />
              ) : null}
              Test Connection
            </Button>
            {testMutation.isSuccess && testMutation.data?.success && (
              <span className="ml-2 text-sm text-green-600">{testMutation.data.message}</span>
            )}
            {testMutation.isSuccess && !testMutation.data?.success && (
              <span className="ml-2 text-sm text-red-600">{testMutation.data?.message || 'Test failed'}</span>
            )}
            {testMutation.isError && (
              <span className="ml-2 text-sm text-red-600">Connection error</span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Save Button */}
      <div className="flex items-center gap-3">
        <Button onClick={handleSave} disabled={updateMutation.isPending}>
          {updateMutation.isPending ? (
            <Loader2 size={14} className="animate-spin" />
          ) : (
            <Save size={14} />
          )}
          Save Configuration
        </Button>
        {updateMutation.isSuccess && (
          <span className="text-sm text-green-600">Configuration saved successfully.</span>
        )}
        {updateMutation.isError && (
          <span className="text-sm text-red-600">Failed to save configuration.</span>
        )}
      </div>
    </div>
  )
}

import { useParams, useNavigate, Link } from 'react-router-dom'
import { ArrowLeft, Clock } from 'lucide-react'
import { useState, useMemo } from 'react'
import {
  useAlert,
  useAlertTrend,
  useAckAlert,
  useResolveAlert,
  useRecheckAlert,
  useAddComment,
} from '../api/client'
import { SeverityBadge, StatusBadge, TriageBadge, ChannelBadge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Skeleton } from '../components/ui/Skeleton'
import { RevenueStatusSection } from '../components/alerts/RevenueStatusSection'
import { DriftRegressionSection } from '../components/alerts/DriftRegressionSection'
import { ComparativeMetricsSection } from '../components/alerts/ComparativeMetricsSection'
import { TriageSection } from '../components/alerts/TriageSection'
import { ContributorsSection } from '../components/alerts/ContributorsSection'
import { GeoBreakdownSection } from '../components/alerts/GeoBreakdownSection'
import { EnvironmentSplitSection } from '../components/alerts/EnvironmentSplitSection'
import { InsightsSection } from '../components/alerts/InsightsSection'
import { CacheWarningSection } from '../components/alerts/CacheWarningSection'
import { formatTimestamp } from '../lib/utils'
import type { Alert } from '../types/alert'

type StepId = 'revenue' | 'drift' | 'comparative' | 'triage' | 'contributors' | 'geo' | 'environment' | 'insights' | 'cache';

interface Step {
  id: StepId;
  label: string;
  condition?: (alert: Alert) => boolean;
}

const STEPS: Step[] = [
  { id: 'revenue', label: 'Revenue Impact' },
  { id: 'drift', label: 'Drift Analysis', condition: (alert: Alert) => !!alert.drift_regression },
  { id: 'comparative', label: 'Comparisons', condition: (alert: Alert) => !!(alert.yesterday_comparison || alert.moving_average_14d) },
  { id: 'triage', label: 'Triage Classification' },
  { id: 'contributors', label: 'Top Contributors' },
  { id: 'geo', label: 'Geo Breakdown' },
  { id: 'environment', label: 'Environment Split' },
  { id: 'insights', label: 'Insights & Actions' },
  { id: 'cache', label: 'Cache Warning', condition: (alert: Alert) => alert.data_source === 'parquet_cache' },
];

export function AlertDetailPage() {
  const { alertId } = useParams<{ alertId: string }>()
  const navigate = useNavigate()
  const [currentStep, setCurrentStep] = useState<StepId>('revenue')

  const { data: alert, isLoading, error } = useAlert(alertId)
  const { data: trendData } = useAlertTrend(alertId)
  const ackMutation = useAckAlert()
  const resolveMutation = useResolveAlert()
  const recheckMutation = useRecheckAlert()
  const commentMutation = useAddComment()

  const visibleSteps = useMemo(() => {
    if (!alert) return STEPS;
    return STEPS.filter(step => {
      if (step.condition) {
        return step.condition(alert);
      }
      return true;
    });
  }, [alert])

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
        <Skeleton className="h-80" />
        <Skeleton className="h-48" />
        <Skeleton className="h-64" />
        <Skeleton className="h-64" />
        <Skeleton className="h-64" />
      </div>
    )
  }

  if (error || !alert) {
    return (
      <div className="py-12 text-center">
        <p className="text-red-500">Failed to load alert details.</p>
        <Button variant="outline" className="mt-4" onClick={() => navigate('/dashboard')}>
          Back to Dashboard
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-1 text-sm text-gray-500">
        <Link to="/dashboard" className="hover:text-gray-900">
          Dashboard
        </Link>
        <span className="mx-1">/</span>
        <span className="text-gray-900">Alert {alert.alert_id.slice(0, 8)}</span>
      </nav>

      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/dashboard')}>
            <ArrowLeft size={20} />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-gray-900">
                Alert {alert.alert_id.slice(0, 8)}
              </h1>
              <SeverityBadge severity={alert.severity} />
              <StatusBadge status={alert.status} />
            </div>
            <div className="mt-1 flex items-center gap-3 text-sm text-gray-500">
              <span className="flex items-center gap-1">
                <Clock size={14} />
                {formatTimestamp(alert.timestamp)}
              </span>
              <ChannelBadge channel={alert.channel_group} />
              <TriageBadge triage={alert.triage_label} />
              <span className="rounded bg-gray-100 px-2 py-0.5 text-xs font-medium">
                Rule: {alert.alert_rule}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Step Navigation */}
      <div className="flex items-center gap-2 border-b border-gray-200 pb-2 overflow-x-auto">
        {visibleSteps.map((step, index) => (
          <button
            key={step.id}
            onClick={() => setCurrentStep(step.id)}
            className={`px-4 py-2 text-sm font-medium whitespace-nowrap rounded-t-lg transition-colors ${
              currentStep === step.id
                ? 'bg-blue-50 text-blue-700 border-b-2 border-blue-700'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
            }`}
          >
            {index + 1}. {step.label}
          </button>
        ))}
      </div>

      {/* Step Content */}
      <div>
        {currentStep === 'revenue' && <RevenueStatusSection alert={alert} trendData={trendData} />}

        {currentStep === 'drift' && alert.drift_regression && (
          <DriftRegressionSection drift={alert.drift_regression} />
        )}

        {currentStep === 'comparative' && (
          <ComparativeMetricsSection
            yesterdayComparison={alert.yesterday_comparison}
            movingAverage14d={alert.moving_average_14d}
          />
        )}

        {currentStep === 'triage' && <TriageSection alert={alert} />}

        {currentStep === 'contributors' && <ContributorsSection contributors={alert.contributors} />}

        {currentStep === 'geo' && <GeoBreakdownSection geoBreakdown={alert.geo_breakdown} />}

        {currentStep === 'environment' && alert.environment_split && Object.keys(alert.environment_split).length > 0 && (
          <EnvironmentSplitSection environmentSplit={alert.environment_split} />
        )}

        {currentStep === 'insights' && (
          <InsightsSection
            insights={alert.insights ?? { summary: '', insights: [], next_steps: [], cache_warning: '' }}
            events={alert.events ?? []}
            alertId={alert.alert_id}
            status={alert.status}
            onAcknowledge={() => alertId && ackMutation.mutate(alertId)}
            onResolve={() => alertId && resolveMutation.mutate(alertId)}
            onRecheck={() => alertId && recheckMutation.mutate(alertId)}
            onComment={(comment) =>
              alertId && commentMutation.mutate({ alertId, comment })
            }
            isAckPending={ackMutation.isPending}
            isResolvePending={resolveMutation.isPending}
            isRecheckPending={recheckMutation.isPending}
            isCommentPending={commentMutation.isPending}
          />
        )}

        {currentStep === 'cache' && <CacheWarningSection warning={alert.insights?.cache_warning ?? ''} />}
      </div>

      {/* Execution Metadata */}
      <div className="flex items-center gap-4 text-xs text-gray-400">
        <span>Execution time: {(alert.execution_time_sec ?? 0).toFixed(2)}s</span>
        <span>Source: {alert.data_source ?? 'unknown'}</span>
        <span>Created: {formatTimestamp(alert.created_at)}</span>
        <span>Updated: {formatTimestamp(alert.updated_at)}</span>
      </div>
    </div>
  )
}

import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '../../lib/utils'
import type { Severity, AlertStatus, TriageLabel, DemandLayer } from '../../types/alert'
import { DEMAND_LAYER_LABELS } from '../../lib/demand-layers'

const badgeVariants = cva(
  'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors',
  {
    variants: {
      variant: {
        default: 'bg-gray-100 text-gray-800',
        // Severity
        P0: 'bg-red-100 text-red-800 border border-red-200',
        P1: 'bg-orange-100 text-orange-800 border border-orange-200',
        P2: 'bg-yellow-100 text-yellow-800 border border-yellow-200',
        // Status
        OPEN: 'bg-blue-100 text-blue-800 border border-blue-200',
        ACK: 'bg-purple-100 text-purple-800 border border-purple-200',
        RESOLVED: 'bg-green-100 text-green-800 border border-green-200',
        SNOOZED: 'bg-gray-100 text-gray-600 border border-gray-200',
        // Triage
        TRAFFIC_DRIVEN: 'bg-indigo-100 text-indigo-800 border border-indigo-200',
        COVERAGE_DRIVEN: 'bg-amber-100 text-amber-800 border border-amber-200',
        MIXED: 'bg-rose-100 text-rose-800 border border-rose-200',
        REVENUE_ONLY: 'bg-slate-100 text-slate-800 border border-slate-200',
        // Channel
        GOOGLE: 'bg-blue-50 text-blue-700 border border-blue-200',
        OPEN_BIDDING: 'bg-teal-50 text-teal-700 border border-teal-200',
        GOOGLE_ADEX: 'bg-blue-50 text-blue-700 border border-blue-200',
        HEADER_BIDDING_MAGNITE: 'bg-orange-50 text-orange-700 border border-orange-200',
        HEADER_BIDDING_PUBMATIC: 'bg-purple-50 text-purple-700 border border-purple-200',
        TAM: 'bg-cyan-50 text-cyan-700 border border-cyan-200',
        DIRECT: 'bg-red-50 text-red-700 border border-red-200',
        DEAL: 'bg-amber-50 text-amber-700 border border-amber-200',
        // Phase 19 V1 — Demand layers (Marco 2026-05-19)
        DIRETTA: 'bg-red-50 text-red-700 border border-red-200',
        OPEN_MARKET: 'bg-blue-50 text-blue-700 border border-blue-200',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
)

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  return <Badge variant={severity}>{severity}</Badge>
}

export function StatusBadge({ status }: { status: AlertStatus }) {
  return <Badge variant={status}>{status}</Badge>
}

export function TriageBadge({ triage }: { triage: TriageLabel }) {
  const labels: Record<TriageLabel, string> = {
    TRAFFIC_DRIVEN: 'Traffic',
    COVERAGE_DRIVEN: 'Coverage',
    MIXED: 'Mixed',
    REVENUE_ONLY: 'Revenue',
    MARGIN_DRIVEN: 'Margin',
  }
  return <Badge variant={triage as any}>{labels[triage]}</Badge>
}

const CHANNEL_LABELS: Record<string, string> = {
  GOOGLE: 'Google',
  OPEN_BIDDING: 'Open Bidding',
  GOOGLE_ADEX: 'Google AdX',
  HEADER_BIDDING_MAGNITE: 'HB Magnite',
  HEADER_BIDDING_PUBMATIC: 'HB PubMatic',
  TAM: 'TAM',
  DIRECT: 'Direct',
  DEAL: 'Deal',
}

export function ChannelBadge({ channel }: { channel: string }) {
  const label = CHANNEL_LABELS[channel] ?? channel
  return <Badge variant={channel as keyof typeof badgeVariants}>{label}</Badge>
}

// Phase 19 V1 — Demand-layer badge (Marco feedback 2026-05-19).
// Rendered alongside ChannelBadge in AlertDetailPage + on each AlertsListPage row
// so operators can read both granularities at a glance.
export function DemandLayerBadge({ layer }: { layer: DemandLayer }) {
  return <Badge variant={layer as keyof typeof badgeVariants}>{DEMAND_LAYER_LABELS[layer]}</Badge>
}

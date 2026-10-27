import { useState } from 'react'
import {
  Lightbulb,
  Check,
  RefreshCw,
  Clock,
  MessageSquare,
  Send,
} from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { Button } from '../ui/Button'
import { formatTimestamp } from '../../lib/utils'
import type { AlertInsights, AlertEvent } from '../../types/alert'

interface InsightsSectionProps {
  insights: AlertInsights
  events: AlertEvent[]
  alertId: string
  status: string
  onAcknowledge: () => void
  onResolve: () => void
  onRecheck: () => void
  onComment: (comment: string) => void
  isAckPending?: boolean
  isResolvePending?: boolean
  isRecheckPending?: boolean
  isCommentPending?: boolean
}

const eventTypeStyles: Record<string, { bg: string; text: string; label: string }> = {
  ACK: { bg: 'bg-purple-100', text: 'text-purple-700', label: 'Acknowledged' },
  RESOLVE: { bg: 'bg-green-100', text: 'text-green-700', label: 'Resolved' },
  RECHECK: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Re-checked' },
  COMMENT: { bg: 'bg-slate-100', text: 'text-slate-700', label: 'Comment' },
}

export function InsightsSection({
  insights,
  events,
  status,
  onAcknowledge,
  onResolve,
  onRecheck,
  onComment,
  isAckPending,
  isResolvePending,
  isRecheckPending,
  isCommentPending,
}: InsightsSectionProps) {
  const [comment, setComment] = useState('')

  const handleSubmitComment = () => {
    if (!comment.trim()) return
    onComment(comment.trim())
    setComment('')
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Lightbulb size={18} className="text-amber-500" />
          Step 6: AI Insights & Actions
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Summary */}
        {insights.summary && (
          <p className="text-sm font-semibold text-slate-900">{insights.summary}</p>
        )}

        {/* Key Findings */}
        {(insights.insights?.length ?? 0) > 0 && (
          <div>
            <h4 className="mb-2 text-sm font-semibold text-slate-700">Key Findings</h4>
            <ul className="space-y-1.5">
              {(insights.insights ?? []).map((insight, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500" />
                  {insight}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Next Steps */}
        {(insights.next_steps?.length ?? 0) > 0 && (
          <div>
            <h4 className="mb-2 text-sm font-semibold text-slate-700">Recommended Actions</h4>
            <ol className="space-y-1.5">
              {(insights.next_steps ?? []).map((step, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
                  <span className="mt-0.5 w-5 shrink-0 text-right font-mono text-xs font-medium text-slate-400">
                    {i + 1}.
                  </span>
                  {step}
                </li>
              ))}
            </ol>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-2 border-t border-slate-200 pt-4">
          {status === 'OPEN' && (
            <Button
              variant="primary"
              size="sm"
              onClick={onAcknowledge}
              disabled={isAckPending}
            >
              <Check size={14} />
              Acknowledge
            </Button>
          )}
          {status !== 'RESOLVED' && (
            <Button
              variant="primary"
              size="sm"
              onClick={onResolve}
              disabled={isResolvePending}
              className="bg-green-600 hover:bg-green-700"
            >
              <Check size={14} />
              Mark Resolved
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={onRecheck}
            disabled={isRecheckPending}
            className="border-orange-300 text-orange-600 hover:bg-orange-50"
          >
            <RefreshCw size={14} className={isRecheckPending ? 'animate-spin' : ''} />
            Re-check (5min)
          </Button>
        </div>

        {/* Comment Form */}
        <div className="border-t border-slate-200 pt-4">
          <h4 className="mb-2 text-sm font-semibold text-slate-700">Add Comment</h4>
          <div className="flex gap-2">
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleSubmitComment()
                }
              }}
              placeholder="Type a comment..."
              rows={2}
              className="flex-1 resize-none rounded-md border border-slate-200 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100 transition-colors duration-150 hover:border-slate-300"
            />
            <Button
              variant="primary"
              size="sm"
              onClick={handleSubmitComment}
              disabled={!comment.trim() || isCommentPending}
              className="self-end"
            >
              <Send size={14} />
            </Button>
          </div>
        </div>

        {/* Audit Log Timeline */}
        <div className="border-t border-slate-200 pt-4">
          <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700">
            <MessageSquare size={14} />
            Activity Log
          </h4>
          {events.length === 0 ? (
            <p className="py-4 text-center text-sm text-slate-400">No activity yet.</p>
          ) : (
            <div className="space-y-3">
              {events.map((event) => {
                const style = eventTypeStyles[event.event_type] ?? eventTypeStyles.COMMENT
                return (
                  <div
                    key={event.event_id}
                    className="flex items-start gap-3 rounded-lg border border-slate-100 p-3"
                  >
                    <div className="flex shrink-0 flex-col items-center gap-1">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${style.bg} ${style.text}`}
                      >
                        {style.label}
                      </span>
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 text-xs text-slate-400">
                        <span className="font-medium text-slate-700">{event.user_id}</span>
                        <Clock size={10} />
                        <span>{formatTimestamp(event.timestamp)}</span>
                      </div>
                      {event.comment && (
                        <p className="mt-1 text-sm text-slate-600">{event.comment}</p>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

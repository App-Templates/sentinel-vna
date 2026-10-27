import { useState } from 'react'
import { MessageSquare } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { Button } from '../ui/Button'
import { useSubmitFeedback, usePublisherFeedbackHistory } from '../../api/client'
import { formatTimestamp } from '../../lib/utils'
import type { Alert, FeedbackType } from '../../types/alert'

interface FeedbackPanelProps {
  alert: Alert
  publisherId: string
}

const FEEDBACK_OPTIONS: Array<{ value: FeedbackType; label: string; description: string }> = [
  {
    value: 'REAL',
    label: 'Confirm as Real Alert',
    description: 'This alert correctly identified a genuine revenue issue',
  },
  {
    value: 'FALSE_POSITIVE_MANUAL_INTERVENTION',
    label: 'False Positive - Manual Intervention',
    description: 'We changed pricing, floor CPM, or configuration that caused this drop',
  },
  {
    value: 'FALSE_POSITIVE_SEASONALITY',
    label: 'False Positive - Seasonal Pattern',
    description: 'Expected seasonal behavior (holidays, weekly patterns, etc.)',
  },
  {
    value: 'FALSE_POSITIVE_TECHNICAL',
    label: 'False Positive - Technical Issue',
    description: 'Data quality problem, system outage, or technical anomaly',
  },
  {
    value: 'FALSE_POSITIVE_PUBLISHER_CAMPAIGN',
    label: 'False Positive - Publisher Campaign',
    description: 'Publisher ran a direct campaign that reduced programmatic traffic',
  },
  {
    value: 'FALSE_POSITIVE_MARKET_NOISE',
    label: 'False Positive - Market Noise',
    description: 'Normal market volatility or temporary fluctuation',
  },
]

export function FeedbackPanel({ alert, publisherId }: FeedbackPanelProps) {
  const [selectedFeedback, setSelectedFeedback] = useState<FeedbackType | null>(null)
  const [comment, setComment] = useState('')
  const submitFeedbackMutation = useSubmitFeedback()
  const { data: historyData, isLoading: historyLoading } = usePublisherFeedbackHistory(publisherId)

  const handleSubmit = async () => {
    if (!selectedFeedback) return

    try {
      await submitFeedbackMutation.mutateAsync({
        alertId: alert.alert_id,
        feedbackType: selectedFeedback,
        comment: comment.trim() || undefined,
      })
      // Clear form on success
      setSelectedFeedback(null)
      setComment('')
    } catch (err) {
      console.error('Failed to submit feedback:', err)
    }
  }

  const feedbacks = historyData?.feedbacks || []

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageSquare size={20} />
          Operator Feedback
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Feedback Form */}
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="block text-sm font-medium text-slate-700">
              Alert Classification
            </label>
            <div className="space-y-2">
              {FEEDBACK_OPTIONS.map((option) => (
                <label
                  key={option.value}
                  className={`flex items-start gap-3 rounded-lg border p-3 cursor-pointer transition-colors ${
                    selectedFeedback === option.value
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                  }`}
                >
                  <input
                    type="radio"
                    name="feedback"
                    value={option.value}
                    checked={selectedFeedback === option.value}
                    onChange={() => setSelectedFeedback(option.value)}
                    className="mt-1"
                  />
                  <div className="flex-1">
                    <div className="font-medium text-slate-900">{option.label}</div>
                    <div className="text-sm text-slate-500">{option.description}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label htmlFor="feedback-comment" className="block text-sm font-medium text-slate-700 mb-2">
              Additional Context (Optional)
            </label>
            <textarea
              id="feedback-comment"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Add context or details..."
              rows={3}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm resize-none focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100 transition-colors duration-150 hover:border-slate-300"
              maxLength={500}
            />
            <div className="mt-1 text-xs text-slate-400 text-right">
              {comment.length}/500
            </div>
          </div>

          <Button
            onClick={handleSubmit}
            disabled={!selectedFeedback || submitFeedbackMutation.isPending}
            className="w-full"
          >
            {submitFeedbackMutation.isPending ? 'Submitting...' : 'Submit Feedback'}
          </Button>

          {submitFeedbackMutation.isSuccess && (
            <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700">
              Feedback submitted successfully!
            </div>
          )}

          {submitFeedbackMutation.isError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              Failed to submit feedback. Please try again.
            </div>
          )}
        </div>

        {/* Feedback History */}
        <div className="border-t pt-6">
          <h3 className="text-sm font-semibold text-slate-900 mb-3">
            Feedback History for this Publisher
          </h3>
          {historyLoading ? (
            <div className="text-sm text-slate-500">Loading history...</div>
          ) : feedbacks.length === 0 ? (
            <div className="text-sm text-slate-500">No previous feedback for this publisher</div>
          ) : (
            <div className="space-y-3">
              {feedbacks.slice(0, 10).map((feedback: any) => {
                const feedbackOption = FEEDBACK_OPTIONS.find((opt) => opt.value === feedback.feedback_type)
                const isReal = feedback.feedback_type === 'REAL'

                return (
                  <div
                    key={feedback.feedback_id}
                    className="border border-slate-200 rounded-lg p-3 space-y-2"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1">
                        <span
                          className={`inline-block rounded-md px-2 py-0.5 text-xs font-medium ${
                            isReal
                              ? 'bg-green-100 text-green-800'
                              : 'bg-orange-100 text-orange-800'
                          }`}
                        >
                          {feedbackOption?.label || feedback.feedback_type}
                        </span>
                      </div>
                      <span className="text-xs text-slate-500">
                        {formatTimestamp(feedback.timestamp)}
                      </span>
                    </div>

                    {feedback.comment && (
                      <div className="text-sm text-slate-700 italic">
                        "{feedback.comment}"
                      </div>
                    )}

                    <div className="flex items-center gap-2 text-xs text-slate-500">
                      <span>Alert: {feedback.alert_id?.slice(0, 8) || 'N/A'}</span>
                      <span>•</span>
                      <span>By: {feedback.user_id || 'Unknown'}</span>
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

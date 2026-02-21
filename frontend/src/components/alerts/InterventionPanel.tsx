import { useState } from 'react'
import { Wrench } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { Button } from '../ui/Button'
import { useCreateIntervention, useLinkIntervention } from '../../api/client'
import { formatTimestamp } from '../../lib/utils'
import type { Alert, InterventionType } from '../../types/alert'

interface InterventionPanelProps {
  alert: Alert
  publisherId: string
}

const INTERVENTION_TYPES: Array<{ value: InterventionType; label: string }> = [
  { value: 'PRICING_RULE', label: 'Pricing Rule' },
  { value: 'FLOOR_CPM', label: 'Floor CPM' },
  { value: 'DEMAND_PARTNER_CONFIG', label: 'Demand Partner Config' },
  { value: 'AD_UNIT_SETUP', label: 'Ad Unit Setup' },
  { value: 'POLICY_CHANGE', label: 'Policy Change' },
  { value: 'OTHER', label: 'Other' },
]

const TOP_PUBLISHERS = [
  'vocento',
  'prensaiberica',
  'mondadori',
  'elespanol',
  'dorvan',
  'unidadeditorial',
  'thecore',
  'alayansmedia',
  'grupogodo',
  'piemme',
  'rcs',
  'gedi',
  'citynews',
  'gruppo24ore',
  'italiaonline',
  'athesigroup',
  'seseitalia',
  'caltagirone',
  'classeditori',
  'angelinigruppo',
  'iubenda',
  'edizioniminerva',
  'netweek',
  'cairorcs',
  'primapagina',
  'publitalia',
  'sportnetwork',
  'ansa',
  'lifegate',
  'adnkronos',
  'rainews',
  'editorialedomani',
  'ilsole24ore',
  'mediakey',
  'emmetv',
]

export function InterventionPanel({ alert, publisherId }: InterventionPanelProps) {
  const getCurrentTimestamp = () => {
    const now = new Date()
    // Format as YYYY-MM-DDTHH:MM (local time for datetime-local input)
    const year = now.getFullYear()
    const month = String(now.getMonth() + 1).padStart(2, '0')
    const day = String(now.getDate()).padStart(2, '0')
    const hours = String(now.getHours()).padStart(2, '0')
    const minutes = String(now.getMinutes()).padStart(2, '0')
    return `${year}-${month}-${day}T${hours}:${minutes}`
  }

  const [timestamp, setTimestamp] = useState(getCurrentTimestamp())
  const [selectedPublisher, setSelectedPublisher] = useState(publisherId || '')
  const [interventionType, setInterventionType] = useState<InterventionType>('PRICING_RULE')
  const [description, setDescription] = useState('')
  const [valueBefore, setValueBefore] = useState('')
  const [valueAfter, setValueAfter] = useState('')

  const createMutation = useCreateIntervention()
  const linkMutation = useLinkIntervention()

  const clearForm = () => {
    setTimestamp(getCurrentTimestamp())
    setSelectedPublisher(publisherId || '')
    setInterventionType('PRICING_RULE')
    setDescription('')
    setValueBefore('')
    setValueAfter('')
  }

  const handleSaveOnly = async () => {
    if (!validateForm()) return

    try {
      const result = await createMutation.mutateAsync({
        timestamp: new Date(timestamp).toISOString(),
        publisher_id: selectedPublisher,
        intervention_type: interventionType,
        description: description.trim(),
        value_before: valueBefore.trim() || undefined,
        value_after: valueAfter.trim() || undefined,
      })
      clearForm()
      alert('Intervention saved with ID: ' + result.intervention_id)
    } catch (err) {
      console.error('Failed to create intervention:', err)
    }
  }

  const handleSaveAndLink = async () => {
    if (!validateForm()) return

    try {
      const result = await createMutation.mutateAsync({
        timestamp: new Date(timestamp).toISOString(),
        publisher_id: selectedPublisher,
        intervention_type: interventionType,
        description: description.trim(),
        value_before: valueBefore.trim() || undefined,
        value_after: valueAfter.trim() || undefined,
      })

      await linkMutation.mutateAsync({
        alertId: alert.alert_id,
        interventionId: result.intervention_id,
      })

      clearForm()
    } catch (err) {
      console.error('Failed to create and link intervention:', err)
    }
  }

  const validateForm = () => {
    if (!timestamp || !selectedPublisher || !interventionType || !description.trim()) {
      alert('Please fill in all required fields (timestamp, publisher, type, description)')
      return false
    }
    return true
  }

  const linkedInterventions = alert.interventions || []

  const selectClass =
    'rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 w-full'

  const inputClass =
    'rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 w-full'

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Wrench size={20} />
          Manual Interventions
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Intervention Form */}
        <div className="space-y-4 border border-gray-200 rounded-lg p-4 bg-gray-50">
          <h3 className="text-sm font-semibold text-gray-900">Record Intervention</h3>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="intervention-timestamp" className="block text-sm font-medium text-gray-700 mb-1">
                Timestamp <span className="text-red-500">*</span>
              </label>
              <input
                type="datetime-local"
                id="intervention-timestamp"
                value={timestamp}
                onChange={(e) => setTimestamp(e.target.value)}
                className={inputClass}
                required
              />
            </div>

            <div>
              <label htmlFor="intervention-publisher" className="block text-sm font-medium text-gray-700 mb-1">
                Publisher <span className="text-red-500">*</span>
              </label>
              <select
                id="intervention-publisher"
                value={selectedPublisher}
                onChange={(e) => setSelectedPublisher(e.target.value)}
                className={selectClass}
                required
              >
                <option value="">Select publisher...</option>
                {TOP_PUBLISHERS.map((pub) => (
                  <option key={pub} value={pub}>
                    {pub}
                  </option>
                ))}
              </select>
            </div>

            <div className="col-span-2">
              <label htmlFor="intervention-type" className="block text-sm font-medium text-gray-700 mb-1">
                Intervention Type <span className="text-red-500">*</span>
              </label>
              <select
                id="intervention-type"
                value={interventionType}
                onChange={(e) => setInterventionType(e.target.value as InterventionType)}
                className={selectClass}
                required
              >
                {INTERVENTION_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="col-span-2">
              <label htmlFor="intervention-description" className="block text-sm font-medium text-gray-700 mb-1">
                Description <span className="text-red-500">*</span>
              </label>
              <textarea
                id="intervention-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Brief reason: e.g., 'Increased floor from 2.5 to 3.0 EUR due to low fill rate'"
                rows={3}
                maxLength={500}
                className={inputClass + ' resize-none'}
                required
              />
              <div className="mt-1 text-xs text-gray-400 text-right">
                {description.length}/500
              </div>
            </div>

            <div>
              <label htmlFor="intervention-before" className="block text-sm font-medium text-gray-700 mb-1">
                Value Before (Optional)
              </label>
              <input
                type="text"
                id="intervention-before"
                value={valueBefore}
                onChange={(e) => setValueBefore(e.target.value)}
                placeholder="e.g., floor 2.5 EUR"
                className={inputClass}
              />
            </div>

            <div>
              <label htmlFor="intervention-after" className="block text-sm font-medium text-gray-700 mb-1">
                Value After (Optional)
              </label>
              <input
                type="text"
                id="intervention-after"
                value={valueAfter}
                onChange={(e) => setValueAfter(e.target.value)}
                placeholder="e.g., floor 3.0 EUR"
                className={inputClass}
              />
            </div>
          </div>

          <div className="flex gap-3 pt-2">
            <Button
              onClick={handleSaveOnly}
              disabled={createMutation.isPending || linkMutation.isPending}
              variant="outline"
              className="flex-1"
            >
              {createMutation.isPending ? 'Saving...' : 'Save Intervention'}
            </Button>
            <Button
              onClick={handleSaveAndLink}
              disabled={createMutation.isPending || linkMutation.isPending}
              className="flex-1"
            >
              {linkMutation.isPending ? 'Linking...' : 'Save & Link to This Alert'}
            </Button>
          </div>

          {(createMutation.isSuccess || linkMutation.isSuccess) && (
            <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700">
              Intervention {linkMutation.isSuccess ? 'saved and linked' : 'saved'} successfully!
            </div>
          )}

          {(createMutation.isError || linkMutation.isError) && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              Failed to save intervention. Please try again.
            </div>
          )}
        </div>

        {/* Linked Interventions List */}
        <div className="border-t pt-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">
            Interventions Linked to This Alert
          </h3>
          {linkedInterventions.length === 0 ? (
            <div className="text-sm text-gray-500">No interventions linked yet</div>
          ) : (
            <div className="space-y-3">
              {linkedInterventions.map((intervention) => {
                const typeLabel =
                  INTERVENTION_TYPES.find((t) => t.value === intervention.intervention_type)?.label ||
                  intervention.intervention_type

                return (
                  <div
                    key={intervention.intervention_id}
                    className="border border-gray-200 rounded-lg p-4 space-y-2"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                          {typeLabel}
                        </span>
                        <div className="mt-1 text-sm font-medium text-gray-900">
                          {intervention.publisher_id}
                        </div>
                      </div>
                      <span className="text-xs text-gray-500">
                        {formatTimestamp(intervention.timestamp)}
                      </span>
                    </div>

                    <div className="text-sm text-gray-700">{intervention.description}</div>

                    {(intervention.value_before || intervention.value_after) && (
                      <div className="flex items-center gap-2 text-sm">
                        {intervention.value_before && (
                          <span className="text-gray-600">
                            <span className="font-medium">Before:</span> {intervention.value_before}
                          </span>
                        )}
                        {intervention.value_before && intervention.value_after && (
                          <span className="text-gray-400">→</span>
                        )}
                        {intervention.value_after && (
                          <span className="text-gray-600">
                            <span className="font-medium">After:</span> {intervention.value_after}
                          </span>
                        )}
                      </div>
                    )}

                    <div className="flex items-center gap-2 text-xs text-gray-500">
                      <span>By: {intervention.user_id || 'Unknown'}</span>
                      <span>•</span>
                      <span>Created: {formatTimestamp(intervention.created_at)}</span>
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

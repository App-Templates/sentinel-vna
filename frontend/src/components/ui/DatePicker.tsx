import { useState, useEffect, useRef } from 'react'

interface DatePickerProps {
  value: string
  availableDates: string[]
  onChange: (date: string) => void
  className?: string
}

/**
 * Date picker that only commits the selected date on blur or Enter,
 * preventing intermediate API calls when navigating months in the
 * native calendar popup.
 */
export function DatePicker({ value, availableDates, onChange, className }: DatePickerProps) {
  const [localValue, setLocalValue] = useState(value)
  const commitRef = useRef(value)

  useEffect(() => {
    setLocalValue(value)
    commitRef.current = value
  }, [value])

  function commit(date: string) {
    if (date && date !== commitRef.current) {
      commitRef.current = date
      onChange(date)
    }
  }

  return (
    <input
      type="date"
      value={localValue}
      min={availableDates.length > 0 ? availableDates[availableDates.length - 1] : undefined}
      max={availableDates.length > 0 ? availableDates[0] : undefined}
      onChange={(e) => setLocalValue(e.target.value)}
      onBlur={() => commit(localValue)}
      onKeyDown={(e) => {
        if (e.key === 'Enter') commit(localValue)
      }}
      className={className}
    />
  )
}

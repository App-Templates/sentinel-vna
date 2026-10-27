import { useState, useRef, useEffect } from 'react'
import { ChevronDown, X } from 'lucide-react'
import { ALL_CHANNELS, CHANNEL_LABELS, CHANNEL_COLORS } from '../../lib/channels'

interface ChannelFilterProps {
  selected: string[]
  onChange: (channels: string[]) => void
}

export function ChannelFilter({ selected, onChange }: ChannelFilterProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const toggle = (ch: string) => {
    if (selected.includes(ch)) {
      onChange(selected.filter((c) => c !== ch))
    } else {
      onChange([...selected, ch])
    }
  }

  const label = selected.length === 0
    ? 'All Channels'
    : selected.length === 1
      ? CHANNEL_LABELS[selected[0]] ?? selected[0]
      : `${selected.length} channels`

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
      >
        <span>{label}</span>
        <ChevronDown size={14} className={`transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {selected.length > 0 && (
        <button
          onClick={() => onChange([])}
          className="ml-1 inline-flex items-center rounded p-1 text-gray-400 hover:text-gray-600"
          title="Clear channel filter"
        >
          <X size={14} />
        </button>
      )}
      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 w-56 rounded-lg border border-gray-200 bg-white py-1 shadow-lg">
          {ALL_CHANNELS.map((ch) => (
            <label
              key={ch}
              className="flex cursor-pointer items-center gap-2.5 px-3 py-1.5 text-sm hover:bg-gray-50"
            >
              <input
                type="checkbox"
                checked={selected.includes(ch)}
                onChange={() => toggle(ch)}
                className="h-3.5 w-3.5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: CHANNEL_COLORS[ch] }}
              />
              <span className="text-gray-700">{CHANNEL_LABELS[ch]}</span>
            </label>
          ))}
        </div>
      )}
    </div>
  )
}

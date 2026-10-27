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
        className="flex cursor-pointer items-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm transition-colors duration-150 hover:bg-slate-100 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
      >
        <span>{label}</span>
        <ChevronDown size={14} className={`transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {selected.length > 0 && (
        <button
          onClick={() => onChange([])}
          className="ml-1 inline-flex items-center rounded p-1 text-slate-400 hover:text-slate-600 transition-colors duration-150"
          title="Clear channel filter"
        >
          <X size={14} />
        </button>
      )}
      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 w-56 rounded-lg border border-slate-200 bg-white py-1 shadow-md">
          {ALL_CHANNELS.map((ch) => (
            <label
              key={ch}
              className="flex cursor-pointer items-center gap-2.5 px-3 py-1.5 text-sm hover:bg-slate-50 transition-colors duration-150"
            >
              <input
                type="checkbox"
                checked={selected.includes(ch)}
                onChange={() => toggle(ch)}
                className="h-3.5 w-3.5 rounded border-slate-300 text-blue-600 focus:ring-blue-400"
              />
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: CHANNEL_COLORS[ch] }}
              />
              <span className="text-slate-700">{CHANNEL_LABELS[ch]}</span>
            </label>
          ))}
        </div>
      )}
    </div>
  )
}

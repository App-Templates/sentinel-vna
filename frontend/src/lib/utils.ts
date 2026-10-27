import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatCurrency(value: number): string {
  // Magnitude-aware precision: small per-mille metrics (RPM, eCPM, marginality)
  // need 2 decimals so €0.36 doesn't render as €0. Large totals (revenue,
  // baseline, YoY) stay integers to keep the display compact. Threshold 10 €
  // covers all per-mille rates safely while leaving currency totals untouched.
  const decimals = Math.abs(value) < 10 ? 2 : 0
  return new Intl.NumberFormat('it-IT', {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value)
}

export function formatPercent(value: number): string {
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(1)}%`
}

export function formatTimestamp(ts: string): string {
  return new Date(ts).toLocaleString('it-IT', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatTimestampUtc(iso: string): string {
  const d = new Date(iso);
  const date = d.toLocaleDateString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
    timeZone: 'UTC',
  });
  const time = d.toLocaleTimeString('en-GB', {
    hour: '2-digit', minute: '2-digit',
    hour12: false,
    timeZone: 'UTC',
  });
  return `${date} ${time} UTC`;
}

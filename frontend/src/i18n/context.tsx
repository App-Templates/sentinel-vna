import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'
import en from './en'
import it from './it'

type Locale = 'en' | 'it'

const translations: Record<Locale, Record<string, string>> = { en, it }

interface I18nContextValue {
  locale: Locale
  setLocale: (locale: Locale) => void
  t: (key: string, ...args: string[]) => string
}

const I18nContext = createContext<I18nContextValue | null>(null)

function getStoredLocale(): Locale {
  try {
    const stored = localStorage.getItem('sentinel-locale')
    if (stored === 'en' || stored === 'it') return stored
  } catch {
    // ignore
  }
  return 'it'
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(getStoredLocale)

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next)
    try {
      localStorage.setItem('sentinel-locale', next)
    } catch {
      // ignore
    }
  }, [])

  const t = useCallback(
    (key: string, ...args: string[]): string => {
      const dict = translations[locale]
      const fallback = translations['en']
      let value = dict[key] ?? fallback[key] ?? key
      // Replace positional placeholders {0}, {1}, ...
      args.forEach((arg, i) => {
        value = value.replace(`{${i}}`, arg)
      })
      return value
    },
    [locale]
  )

  return <I18nContext.Provider value={{ locale, setLocale, t }}>{children}</I18nContext.Provider>
}

export function useTranslation() {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useTranslation must be used within LanguageProvider')
  return ctx
}

import { useTranslation } from '../../i18n/context'

const flags: Record<string, string> = {
  en: '🇬🇧',
  it: '🇮🇹',
}

export function LanguageSwitcher({ collapsed = false }: { collapsed?: boolean }) {
  const { locale, setLocale } = useTranslation()

  const next = locale === 'it' ? 'en' : 'it'

  return (
    <button
      onClick={() => setLocale(next)}
      title={locale === 'it' ? 'Switch to English' : 'Passa all\'italiano'}
      className="flex w-full items-center justify-center gap-1.5 rounded-md px-2 py-1.5 text-xs font-medium text-slate-400 transition-all duration-150 hover:bg-slate-800 hover:text-slate-100"
    >
      <span className="text-sm leading-none">{flags[locale]}</span>
      {!collapsed && <span className="uppercase tracking-wide">{locale}</span>}
    </button>
  )
}

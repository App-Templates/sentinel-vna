import { useState, createContext, useContext, useCallback, type ReactNode } from 'react'

export interface AuthUser {
  email: string
  name: string
  picture: string
}

interface AuthContextType {
  user: AuthUser | null
  logout: () => void
}

const STORAGE_KEY = 'sentinel_user'
const ALLOWED_DOMAIN = '@adkaora.com'

function loadUser(): AuthUser | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const u = JSON.parse(raw) as AuthUser
    if (u.email?.endsWith(ALLOWED_DOMAIN)) return u
    localStorage.removeItem(STORAGE_KEY)
    return null
  } catch {
    return null
  }
}

const AuthContext = createContext<AuthContextType>({ user: null, logout: () => {} })

export function useAuthContext() {
  return useContext(AuthContext)
}

export function AuthGuard({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(loadUser)
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY)
    setUser(null)
    setEmail('')
  }, [])

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = email.trim().toLowerCase()

    if (!trimmed) {
      setError('Inserisci la tua email')
      return
    }

    if (!trimmed.endsWith(ALLOWED_DOMAIN)) {
      setError('Accesso consentito solo per email @adkaora.com')
      return
    }

    const name = trimmed.split('@')[0]
      .split('.')
      .map(p => p.charAt(0).toUpperCase() + p.slice(1))
      .join(' ')

    const newUser: AuthUser = { email: trimmed, name, picture: '' }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(newUser))
    setUser(newUser)
    setError('')
  }

  if (!user) {
    return (
      <div className="flex h-screen flex-col items-center justify-center bg-gray-900">
        <div className="w-full max-w-sm rounded-2xl bg-gray-800 p-8 shadow-2xl">
          {/* Logo */}
          <div className="mb-8 text-center">
            <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-xl bg-blue-600">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
              </svg>
            </div>
            <h1 className="text-xl font-bold text-white">Sentinel</h1>
            <p className="mt-1 text-sm text-gray-400">Value Network Alerting</p>
          </div>

          {/* Email login form */}
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label htmlFor="email" className="mb-1.5 block text-sm font-medium text-gray-300">
                Email aziendale
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => { setEmail(e.target.value); setError('') }}
                placeholder="nome.cognome@adkaora.com"
                autoFocus
                autoComplete="email"
                className="w-full rounded-lg border border-gray-600 bg-gray-700 px-4 py-3 text-sm text-white placeholder-gray-400 outline-none transition-colors focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              />
            </div>

            {error && (
              <p className="text-sm text-red-400">{error}</p>
            )}

            <button
              type="submit"
              className="w-full rounded-lg bg-blue-600 px-4 py-3 text-sm font-medium text-white transition-colors hover:bg-blue-500"
            >
              Accedi
            </button>
          </form>

          {/* Footer */}
          <p className="mt-6 text-center text-xs text-gray-500">
            Accesso riservato al team Adkaora
          </p>
        </div>
      </div>
    )
  }

  return (
    <AuthContext.Provider value={{ user, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

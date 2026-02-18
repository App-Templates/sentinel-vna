import { useState, useEffect, createContext, useContext, useCallback, type ReactNode } from 'react'

export interface AuthUser {
  email: string
  name: string
  picture: string
}

interface AuthContextType {
  user: AuthUser | null
  logout: () => void
}

const AuthContext = createContext<AuthContextType>({ user: null, logout: () => {} })

export function useAuthContext() {
  return useContext(AuthContext)
}

async function checkAuth(): Promise<AuthUser> {
  const res = await fetch('/auth/me', { credentials: 'include' })
  if (!res.ok) throw new Error(`Auth check failed: ${res.status}`)
  return res.json()
}

export function AuthGuard({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)
  const [needsLogin, setNeedsLogin] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    checkAuth()
      .then((data) => {
        if (!cancelled) {
          setUser(data)
          setLoading(false)
        }
      })
      .catch(() => {
        // Retry once after a short delay (handles race with backend startup)
        setTimeout(() => {
          if (cancelled) return
          checkAuth()
            .then((data) => {
              if (!cancelled) {
                setUser(data)
                setLoading(false)
              }
            })
            .catch((retryErr) => {
              if (!cancelled) {
                setNeedsLogin(true)
                setError(retryErr.message)
                setLoading(false)
              }
            })
        }, 1000)
      })
    return () => { cancelled = true }
  }, [])

  const logout = useCallback(async () => {
    await fetch('/auth/logout', { method: 'POST', credentials: 'include' })
    setUser(null)
    setNeedsLogin(true)
  }, [])

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-900">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-gray-700 border-t-blue-500" />
          <span className="text-sm text-gray-400">Loading Sentinel...</span>
        </div>
      </div>
    )
  }

  if (needsLogin) {
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

          {/* Login button */}
          <a
            href="/auth/login"
            className="flex w-full items-center justify-center gap-3 rounded-lg bg-white px-4 py-3 text-sm font-medium text-gray-800 shadow transition-colors hover:bg-gray-100"
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
            Sign in with Google
          </a>

          {/* Footer */}
          <p className="mt-6 text-center text-xs text-gray-500">
            Accesso riservato al team Adkaora
          </p>
          {error && (
            <p className="mt-2 text-center text-xs text-red-400/70">{error}</p>
          )}
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

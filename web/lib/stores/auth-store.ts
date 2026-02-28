import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface AuthUser {
  username: string
  role: 'analyst' | 'admin'
  email?: string
}

interface AuthState {
  token: string | null
  user: AuthUser | null
  setAuth: (token: string, user: AuthUser) => void
  logout: () => void
}

const AUTH_COOKIE = 'auth-token'
const COOKIE_MAX_AGE = 60 * 60 * 24 // 24h in seconds

function setCookie(value: string) {
  if (typeof document === 'undefined') return
  document.cookie = `${AUTH_COOKIE}=${value}; path=/; SameSite=Strict; max-age=${COOKIE_MAX_AGE}`
}

function clearCookie() {
  if (typeof document === 'undefined') return
  document.cookie = `${AUTH_COOKIE}=; path=/; SameSite=Strict; max-age=0`
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,

      setAuth: (token, user) => {
        setCookie(token)
        set({ token, user })
      },

      logout: () => {
        clearCookie()
        set({ token: null, user: null })
      },
    }),
    {
      name: 'forensicstack-auth',
      partialize: (state) => ({ token: state.token, user: state.user }),
      onRehydrateStorage: () => (state) => {
        // Sync cookie on rehydration (e.g. page refresh)
        if (state?.token) setCookie(state.token)
      },
    }
  )
)

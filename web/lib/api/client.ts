import axios from 'axios'
import { useAuthStore } from '@/lib/stores/auth-store'

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8001'

export const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
})

// Inject JWT on every request
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Endpoints where a 401 means "these credentials are wrong", not "your session expired".
const AUTH_ENDPOINTS = ['/auth/login', '/auth/register']

function isAuthEndpoint(url: string | undefined): boolean {
  if (!url) return false
  return AUTH_ENDPOINTS.some((path) => url.includes(path))
}

// On 401 — clear auth and redirect to login.
// Note: 403 (forbidden) is intentionally NOT handled here — the user is authenticated
// but lacks access to that resource (e.g. another owner's case), so logging them out is wrong.
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Skip the redirect for login/register: a 401 there is a bad-credentials response the
    // form needs to display. Redirecting would unmount the page before setError() renders,
    // so the user would see a silent bounce back to /login with no explanation.
    if (error.response?.status === 401 && !isAuthEndpoint(error.config?.url)) {
      useAuthStore.getState().logout()
      if (typeof window !== 'undefined') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

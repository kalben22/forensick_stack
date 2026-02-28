'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { authApi } from '@/lib/api/auth'
import { useAuthStore } from '@/lib/stores/auth-store'

export function useLoginMutation() {
  const router = useRouter()
  const { setAuth } = useAuthStore()
  const qc = useQueryClient()

  return useMutation({
    mutationFn: authApi.login,
    onSuccess: (data, _vars, _ctx) => {
      setAuth(data.access_token, {
        username: data.username,
        role: data.role as 'analyst' | 'admin',
      })
      qc.invalidateQueries({ queryKey: ['me'] })
    },
    onError: () => {
      // Errors surfaced in the component via mutation.error
    },
  })
}

export function useLogout() {
  const router = useRouter()
  const { logout } = useAuthStore()
  const qc = useQueryClient()

  return () => {
    logout()
    qc.clear()
    router.push('/login')
  }
}

export function useMe() {
  const token = useAuthStore((s) => s.token)

  return useQuery({
    queryKey: ['me'],
    queryFn: authApi.getMe,
    enabled: !!token,
    staleTime: Infinity,
    retry: false,
  })
}

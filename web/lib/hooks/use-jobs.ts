'use client'

import { useEffect, useRef } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { io, type Socket } from 'socket.io-client'
import { jobsApi, type JobSubmitRequest, type JobStatusResponse } from '@/lib/api/jobs'
import { useAuthStore } from '@/lib/stores/auth-store'

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://127.0.0.1:8001'

export function useListTools() {
  return useQuery({
    queryKey: ['tools'],
    queryFn: jobsApi.listTools,
    staleTime: 5 * 60_000,
  })
}

export function useJob(jobId: string | undefined) {
  return useQuery({
    queryKey: ['job', jobId],
    queryFn: () => jobsApi.getStatus(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'queued' || status === 'running' || status === 'normalizing'
        ? 3_000
        : false
    },
  })
}

export function useSubmitJob() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: JobSubmitRequest) => jobsApi.submit(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['job'] })
    },
  })
}

interface DirectAnalyzeArgs {
  file: File
  tool: string
  feature?: string
  onProgress?: (pct: number) => void
}

export function useDirectAnalyze() {
  return useMutation({
    mutationFn: ({ file, tool, feature, onProgress }: DirectAnalyzeArgs) =>
      jobsApi.directAnalyze(file, tool, feature, onProgress),
  })
}

/** Live job updates via Socket.io. Merges into React Query cache. */
export function useJobSocket(jobId: string | undefined) {
  const socketRef = useRef<Socket | null>(null)
  const qc = useQueryClient()
  const token = useAuthStore((s) => s.token)

  useEffect(() => {
    if (!jobId || !token) return

    const socket = io(WS_URL, {
      auth: { token },
      transports: ['websocket'],
      reconnectionAttempts: 5,
    })
    socketRef.current = socket

    socket.on(`job:${jobId}`, (data: JobStatusResponse) => {
      qc.setQueryData(['job', jobId], data)
    })

    return () => {
      socket.disconnect()
      socketRef.current = null
    }
  }, [jobId, token, qc])
}

'use client'

import { useMutation, useQuery } from '@tanstack/react-query'
import {
  analyzeApi,
  type IdentifyResponse,
  type AnalyzeResponse,
  type PlanStatusResponse,
} from '@/lib/api/analyze'

interface FileArg {
  file: File
  onProgress?: (pct: number) => void
}

/** Dry run: identify + plan without spending container time. */
export function useIdentify() {
  return useMutation<IdentifyResponse, Error, FileArg>({
    mutationFn: ({ file, onProgress }) => analyzeApi.identify(file, onProgress),
  })
}

interface AnalyzeArg extends FileArg {
  caseId?: number
  maxSteps?: number
}

/** Upload → identify → plan → queue the whole plan autonomously. */
export function useAutoAnalyze() {
  return useMutation<AnalyzeResponse, Error, AnalyzeArg>({
    mutationFn: ({ file, caseId, maxSteps, onProgress }) =>
      analyzeApi.analyze(file, { caseId, maxSteps }, onProgress),
  })
}

/**
 * Live aggregate status of a queued plan. Polls every 2s until every job has
 * finished, then stops. Returns null-ish while no plan is active.
 */
export function usePlanStatus(planId: string | undefined) {
  return useQuery<PlanStatusResponse>({
    queryKey: ['plan', planId],
    queryFn: () => analyzeApi.planStatus(planId!),
    enabled: !!planId,
    refetchInterval: (query) => {
      const data = query.state.data
      if (!data) return 2_000
      // Keep polling until every queued job is terminal.
      return data.total > 0 && data.finished >= data.total ? false : 2_000
    },
  })
}

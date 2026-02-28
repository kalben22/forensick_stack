'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { casesApi, type CasesParams, type CaseCreate, type CaseUpdate } from '@/lib/api/cases'

export function useCases(params?: CasesParams) {
  return useQuery({
    queryKey: ['cases', params],
    queryFn: () => casesApi.list(params),
    staleTime: 30_000,
  })
}

export function useCase(id: number | undefined) {
  return useQuery({
    queryKey: ['case', id],
    queryFn: () => casesApi.get(id!),
    enabled: !!id,
    staleTime: 30_000,
  })
}

export function useCreateCase() {
  const qc = useQueryClient()

  return useMutation({
    mutationFn: (payload: CaseCreate) => casesApi.create(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cases'] })
    },
  })
}

export function useUpdateCase() {
  const qc = useQueryClient()

  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: CaseUpdate }) =>
      casesApi.update(id, payload),
    onSuccess: (_data, { id }) => {
      qc.invalidateQueries({ queryKey: ['cases'] })
      qc.invalidateQueries({ queryKey: ['case', id] })
    },
  })
}

export function useDeleteCase() {
  const qc = useQueryClient()

  return useMutation({
    mutationFn: (id: number) => casesApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cases'] })
    },
  })
}

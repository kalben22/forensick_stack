'use client'

import { useMutation, useQuery } from '@tanstack/react-query'
import { searchApi, type SemanticSearchRequest } from '@/lib/api/search'

export function useSemanticSearch() {
  return useMutation({
    mutationFn: (payload: SemanticSearchRequest) => searchApi.semantic(payload),
  })
}

export function useSearchStats() {
  return useQuery({
    queryKey: ['searchStats'],
    queryFn: searchApi.stats,
    staleTime: 60_000,
  })
}

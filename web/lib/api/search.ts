import { apiClient } from './client'

export interface SemanticSearchRequest {
  query: string
  top_k?: number
  case_id?: number
  tool?: string
}

export interface SearchResult {
  score: number
  tool: string
  artifact_type: string
  artifact_id: number
  case_id: number
  data: Record<string, unknown>
}

export interface SearchResponse {
  query: string
  total: number
  results: SearchResult[]
}

export interface SearchStatsResponse {
  collection: string
  total_findings: number
}

export const searchApi = {
  semantic: async (payload: SemanticSearchRequest): Promise<SearchResponse> => {
    const { data } = await apiClient.post<SearchResponse>('/api/v1/search/semantic', payload)
    return data
  },

  stats: async (): Promise<SearchStatsResponse> => {
    const { data } = await apiClient.get<SearchStatsResponse>('/api/v1/search/stats')
    return data
  },
}

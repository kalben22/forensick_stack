import { apiClient } from './client'

export interface CaseCreate {
  title: string
  description?: string
}

export interface CaseUpdate {
  title?: string
  description?: string
  status?: 'open' | 'closed' | 'archived'
}

export interface CaseResponse {
  id: number
  case_number: string
  title: string
  description: string | null
  status: 'open' | 'closed' | 'archived'
  created_at: string
  updated_at: string | null
}

export interface CaseListResponse {
  cases: CaseResponse[]
  total: number
  page: number
  page_size: number
}

export interface CasesParams {
  skip?: number
  limit?: number
  status?: string
}

export const casesApi = {
  list: async (params?: CasesParams): Promise<CaseListResponse> => {
    const { data } = await apiClient.get<CaseListResponse>('/api/v1/cases/', { params })
    return data
  },

  get: async (id: number): Promise<CaseResponse> => {
    const { data } = await apiClient.get<CaseResponse>(`/api/v1/cases/${id}`)
    return data
  },

  create: async (payload: CaseCreate): Promise<CaseResponse> => {
    const { data } = await apiClient.post<CaseResponse>('/api/v1/cases/', payload)
    return data
  },

  update: async (id: number, payload: CaseUpdate): Promise<CaseResponse> => {
    const { data } = await apiClient.patch<CaseResponse>(`/api/v1/cases/${id}`, payload)
    return data
  },

  remove: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/v1/cases/${id}`)
  },
}

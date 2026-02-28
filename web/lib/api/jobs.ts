import { apiClient } from './client'

export interface ToolInfo {
  name: string
  category: string
  memory: string
  cpus: number
  timeout: number
  description?: string
  image?: string
}

export interface JobSubmitRequest {
  tool: string
  artifact_id: number
  input_type?: string
}

export interface JobSubmitResponse {
  job_id: string
  status: 'queued'
  tool: string
  artifact_id: number
}

export interface JobStatusResponse {
  job_id: string
  status: 'queued' | 'running' | 'normalizing' | 'done' | 'failed'
  tool?: string
  artifact_id?: number
  progress?: number
  findings?: unknown[]
  output_prefix?: string
  error?: string
  created_at?: string
  updated_at?: string
}

export const jobsApi = {
  listTools: async (): Promise<{ tools: ToolInfo[] }> => {
    const { data } = await apiClient.get<{ tools: ToolInfo[] }>('/api/v1/jobs/tools')
    return data
  },

  submit: async (payload: JobSubmitRequest): Promise<JobSubmitResponse> => {
    const { data } = await apiClient.post<JobSubmitResponse>('/api/v1/jobs/submit', payload)
    return data
  },

  getStatus: async (jobId: string): Promise<JobStatusResponse> => {
    const { data } = await apiClient.get<JobStatusResponse>(`/api/v1/jobs/${jobId}`)
    return data
  },
}

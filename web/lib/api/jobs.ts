import { apiClient } from './client'

export interface ToolFeature {
  id: string
  label: string
  description: string
  accepted_extensions: string[]
}

export interface ToolInfo {
  name: string
  category: string
  memory: string
  cpus: number
  timeout: number
  description?: string
  image?: string
  features?: ToolFeature[]
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

export interface DirectAnalyzeResponse {
  job_id: string
  filename: string
  size_bytes: number
  tool: string
  feature: string | null
}

export interface JobStatusResponse {
  job_id: string
  status: 'queued' | 'running' | 'normalizing' | 'completed' | 'done' | 'failed'
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

  directAnalyze: async (
    file: File,
    tool: string,
    feature: string | undefined,
    onProgress?: (pct: number) => void,
  ): Promise<DirectAnalyzeResponse> => {
    const form = new FormData()
    form.append('file', file)
    form.append('tool', tool)
    if (feature) form.append('feature', feature)
    const { data } = await apiClient.post<DirectAnalyzeResponse>(
      '/api/v1/jobs/direct',
      form,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) =>
          onProgress?.(Math.round((e.loaded * 100) / (e.total ?? 1))),
      },
    )
    return data
  },

  getStatus: async (jobId: string): Promise<JobStatusResponse> => {
    const { data } = await apiClient.get<JobStatusResponse>(`/api/v1/jobs/${jobId}`)
    return data
  },
}

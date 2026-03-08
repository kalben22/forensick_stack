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
  upload_token: string       // reuse token — pass to reanalyze() instead of re-uploading
}

export interface ReanalyzeResponse {
  job_id: string
  tool: string
  feature: string | null
  upload_token: string
}

export interface JobStatusResponse {
  job_id: string
  status: 'queued' | 'running' | 'normalizing' | 'completed' | 'done' | 'failed' | 'cancelled'
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
        timeout: 10 * 60 * 1000, // 10 min — memory dumps can be several GB
        // Remove the default 'application/json' Content-Type so the browser
        // can set 'multipart/form-data; boundary=...' automatically from FormData
        transformRequest: [
          (reqData: FormData, headers: Record<string, string>) => {
            delete headers['Content-Type']
            return reqData
          },
        ],
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

  cancelJob: async (jobId: string): Promise<{ cancelled: boolean; reason?: string }> => {
    const { data } = await apiClient.delete(`/api/v1/jobs/${jobId}`)
    return data
  },

  /** Submit a new analysis without re-uploading — reuses the on-disk file via token. */
  reanalyze: async (
    uploadToken: string,
    tool: string,
    feature: string | undefined,
  ): Promise<ReanalyzeResponse> => {
    const form = new FormData()
    form.append('upload_token', uploadToken)
    form.append('tool', tool)
    if (feature) form.append('feature', feature)
    const { data } = await apiClient.post<ReanalyzeResponse>(
      '/api/v1/jobs/reanalyze',
      form,
      {
        transformRequest: [
          (reqData: FormData, headers: Record<string, string>) => {
            delete headers['Content-Type']
            return reqData
          },
        ],
      },
    )
    return data
  },

  /** Explicitly delete a cached upload (called when user changes the file). */
  deleteUpload: async (token: string): Promise<void> => {
    await apiClient.delete(`/api/v1/jobs/upload/${token}`)
  },
}

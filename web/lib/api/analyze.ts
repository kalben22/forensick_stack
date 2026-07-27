import type { AxiosRequestConfig } from 'axios'
import { apiClient } from './client'

// ---------------------------------------------------------------------------
// Types mirror the backend contract in
//   backend/forensicstack/api/routes/analyze.py
//   backend/forensicstack/core/triage/{identify,router}.py
// Keep them in sync when the manifests or identity fields change.
// ---------------------------------------------------------------------------

export interface ArtifactIdentity {
  kind: string
  family: string
  confidence: number
  os_hint: string | null
  label: string
  mime: string | null
  size: number
  sha256: string
  md5: string
  entropy: number
  printable_ratio: number
  page_aligned: boolean
  evidence: string[]
  alternatives: { kind: string; confidence: number }[]
  details: Record<string, unknown>
}

export interface PlanStep {
  tool: string
  feature: string
  priority: number
  stage: number
  reason: string
}

export interface SkippedTool {
  target: string
  reason: string
}

export interface AnalysisPlan {
  identity: ArtifactIdentity
  steps: PlanStep[]
  skipped: SkippedTool[]
  notes: string[]
}

export interface ToolSuggestion {
  tool: string
  tool_name: string
  feature: string
  label: string
  description: string
  auto: boolean
  recommended: boolean
  generic: boolean
}

/** Response of the dry-run POST /analyze/identify — queues nothing. */
export interface IdentifyResponse {
  identity: ArtifactIdentity
  plan: AnalysisPlan
  suggestions: ToolSuggestion[]
  advice: string
}

export interface QueuedJob {
  job_id: string
  tool: string
  feature: string
  priority: number
}

/** Response of POST /analyze — the plan has been queued. */
export interface AnalyzeResponse {
  plan_id: string
  filename: string
  identity: ArtifactIdentity
  plan: AnalysisPlan
  queued_jobs: QueuedJob[]
  suggestions: ToolSuggestion[]
  advice: string
}

export interface PlanJobStatus {
  job_id: string
  status: string
  tool?: string
  feature?: string
  findings?: string
  error?: string
  error_kind?: string
  started_at?: string
  duration_s?: string
  [k: string]: unknown
}

export interface PlanStatusResponse {
  plan_id: string
  jobs: PlanJobStatus[]
  total: number
  finished: number
  progress: number
}

// Evidence files reach several GB; never let the client's 30s default abort the
// upload. Strip the JSON Content-Type so the browser sets the multipart boundary.
const UPLOAD_CFG: AxiosRequestConfig = {
  timeout: 0,
  transformRequest: [
    (reqData: FormData, headers: Record<string, string>) => {
      delete headers['Content-Type']
      return reqData
    },
  ],
}

export const analyzeApi = {
  /** Dry run: identify + plan, queue nothing. Cheap "what would you do with this?". */
  identify: async (
    file: File,
    onProgress?: (pct: number) => void,
  ): Promise<IdentifyResponse> => {
    const form = new FormData()
    form.append('file', file)
    const { data } = await apiClient.post<IdentifyResponse>('/api/v1/analyze/identify', form, {
      ...UPLOAD_CFG,
      onUploadProgress: (e) => onProgress?.(Math.round((e.loaded * 100) / (e.total ?? 1))),
    })
    return data
  },

  /** Upload → identify → plan → queue the whole plan. Returns immediately (202). */
  analyze: async (
    file: File,
    opts: { caseId?: number; maxSteps?: number } = {},
    onProgress?: (pct: number) => void,
  ): Promise<AnalyzeResponse> => {
    const form = new FormData()
    form.append('file', file)
    if (opts.caseId != null) form.append('case_id', String(opts.caseId))
    if (opts.maxSteps != null) form.append('max_steps', String(opts.maxSteps))
    const { data } = await apiClient.post<AnalyzeResponse>('/api/v1/analyze', form, {
      ...UPLOAD_CFG,
      onUploadProgress: (e) => onProgress?.(Math.round((e.loaded * 100) / (e.total ?? 1))),
    })
    return data
  },

  /** Aggregate live status of every job queued under one plan. */
  planStatus: async (planId: string): Promise<PlanStatusResponse> => {
    const { data } = await apiClient.get<PlanStatusResponse>(`/api/v1/analyze/plan/${planId}`)
    return data
  },
}

import { apiClient } from './client'

export type ArtifactType =
  | 'memory_dump'
  | 'disk_image'
  | 'mobile_backup'
  | 'pcap'
  | 'evtx'
  | 'registry'
  | 'document'
  | 'malware_sample'
  | 'other'

export interface ArtifactResponse {
  id: number
  case_id: number
  filename: string
  artifact_type: ArtifactType
  file_path: string
  file_size: number
  file_hash_md5: string
  file_hash_sha256: string
  uploaded_at: string
  download_url: string | null
}

export interface ArtifactListResponse {
  artifacts: ArtifactResponse[]
  total: number
}

export const ARTIFACT_MAX_SIZE = 2 * 1024 * 1024 * 1024 // 2 GB

export const ALLOWED_EXTENSIONS: Record<ArtifactType, string[]> = {
  memory_dump: ['.dmp', '.raw', '.img', '.vmem', '.mem', '.lime'],
  disk_image: ['.dd', '.img', '.e01', '.vmdk', '.vhd', '.raw', '.iso'],
  mobile_backup: ['.tar', '.tar.gz', '.tar.bz2', '.tar.xz', '.tar.zst', '.zip', '.ab', '.ipa', '.apk'],
  pcap: ['.pcap', '.pcapng', '.cap'],
  evtx: ['.evtx'],
  registry: ['.reg', '.hive', '.dat'],
  document: ['.pdf', '.docx', '.xlsx', '.csv', '.txt', '.log', '.json', '.xml'],
  malware_sample: ['.exe', '.dll', '.bin', '.elf', '.macho', '.dmp', '.raw'],
  other: ['*'],
}

/**
 * Compound extensions that must be matched as a whole. Splitting on the last dot alone
 * turns `backup.tar.gz` into `.gz`, which is in no allowlist — that silently rejected
 * every gzipped iOS/Android backup, the primary iLEAPP/aLEAPP input.
 */
const COMPOUND_EXTENSIONS = ['.tar.gz', '.tar.bz2', '.tar.xz', '.tar.zst']

/**
 * Extract a normalized (lowercased) extension from a filename.
 * Lowercasing matters because real evidence files ship as `disk.E01` and `NTUSER.DAT`
 * as often as lowercase, and a case-sensitive compare rejects half of them.
 */
export function getFileExtension(filename: string): string {
  const lower = filename.toLowerCase()
  const compound = COMPOUND_EXTENSIONS.find((ext) => lower.endsWith(ext))
  if (compound) return compound
  const dot = lower.lastIndexOf('.')
  return dot === -1 ? '' : lower.slice(dot)
}

export function validateArtifactFile(
  file: File,
  artifactType: ArtifactType
): { valid: boolean; error?: string } {
  if (file.size > ARTIFACT_MAX_SIZE) {
    return { valid: false, error: `File exceeds 2 GB limit (${(file.size / 1e9).toFixed(1)} GB)` }
  }

  const allowed = ALLOWED_EXTENSIONS[artifactType]
  if (allowed[0] === '*') return { valid: true }

  const ext = getFileExtension(file.name)
  if (!allowed.includes(ext)) {
    return {
      valid: false,
      error: `Extension "${ext}" not allowed for ${artifactType}. Allowed: ${allowed.join(', ')}`,
    }
  }

  return { valid: true }
}

export const artifactsApi = {
  list: async (caseId: number): Promise<ArtifactListResponse> => {
    const { data } = await apiClient.get<ArtifactListResponse>(
      `/api/v1/cases/${caseId}/artifacts/`
    )
    return data
  },

  get: async (caseId: number, artifactId: number): Promise<ArtifactResponse> => {
    const { data } = await apiClient.get<ArtifactResponse>(
      `/api/v1/cases/${caseId}/artifacts/${artifactId}`
    )
    return data
  },

  upload: async (
    caseId: number,
    file: File,
    artifactType: ArtifactType,
    onProgress?: (percent: number) => void
  ): Promise<ArtifactResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('artifact_type', artifactType)

    const { data } = await apiClient.post<ArtifactResponse>(
      `/api/v1/cases/${caseId}/artifacts/`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        // Override the client's 30s default: artifacts run to 2 GB, so any upload taking
        // longer than half a minute would be aborted mid-transfer by the global timeout.
        timeout: 0,
        onUploadProgress: (e) => {
          if (e.total && onProgress) {
            onProgress(Math.round((e.loaded * 100) / e.total))
          }
        },
      }
    )
    return data
  },

  remove: async (caseId: number, artifactId: number): Promise<void> => {
    await apiClient.delete(`/api/v1/cases/${caseId}/artifacts/${artifactId}`)
  },
}

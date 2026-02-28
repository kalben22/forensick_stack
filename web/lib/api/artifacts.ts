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
  mobile_backup: ['.tar', '.zip', '.ab', '.ipa', '.apk'],
  pcap: ['.pcap', '.pcapng', '.cap'],
  evtx: ['.evtx'],
  registry: ['.reg', '.hive', '.dat'],
  document: ['.pdf', '.docx', '.xlsx', '.csv', '.txt', '.log', '.json', '.xml'],
  malware_sample: ['.exe', '.dll', '.bin', '.elf', '.macho', '.dmp', '.raw'],
  other: ['*'],
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

  const ext = '.' + file.name.split('.').pop()?.toLowerCase()
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

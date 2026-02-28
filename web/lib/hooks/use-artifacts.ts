'use client'

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { artifactsApi, type ArtifactType, validateArtifactFile } from '@/lib/api/artifacts'

export function useArtifacts(caseId: number | undefined) {
  return useQuery({
    queryKey: ['artifacts', caseId],
    queryFn: () => artifactsApi.list(caseId!),
    enabled: !!caseId,
    staleTime: 30_000,
  })
}

export function useArtifact(caseId: number | undefined, artifactId: number | undefined) {
  return useQuery({
    queryKey: ['artifact', caseId, artifactId],
    queryFn: () => artifactsApi.get(caseId!, artifactId!),
    enabled: !!caseId && !!artifactId,
  })
}

export function useUploadArtifact(caseId: number | undefined) {
  const qc = useQueryClient()
  const [progress, setProgress] = useState(0)

  const mutation = useMutation({
    mutationFn: ({ file, artifactType }: { file: File; artifactType: ArtifactType }) => {
      const validation = validateArtifactFile(file, artifactType)
      if (!validation.valid) throw new Error(validation.error)
      setProgress(0)
      return artifactsApi.upload(caseId!, file, artifactType, setProgress)
    },
    onSuccess: () => {
      setProgress(0)
      qc.invalidateQueries({ queryKey: ['artifacts', caseId] })
    },
    onError: () => setProgress(0),
  })

  return { ...mutation, progress }
}

export function useDeleteArtifact(caseId: number | undefined) {
  const qc = useQueryClient()

  return useMutation({
    mutationFn: (artifactId: number) => artifactsApi.remove(caseId!, artifactId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['artifacts', caseId] })
    },
  })
}

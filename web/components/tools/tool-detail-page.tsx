'use client'

import { useState, useRef, useCallback } from 'react'
import Link from 'next/link'
import {
  ArrowLeft,
  Brain,
  FileSearch,
  Smartphone,
  Cpu,
  Upload,
  Play,
  Download,
  CheckCircle2,
  XCircle,
  Clock,
  Activity,
  ChevronRight,
  FileWarning,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import { useListTools } from '@/lib/hooks/use-jobs'
import { useDirectAnalyze } from '@/lib/hooks/use-jobs'
import { useJob } from '@/lib/hooks/use-jobs'
import type { ToolFeature } from '@/lib/api/jobs'

// ── Metadata ──────────────────────────────────────────────────────────────────

const CATEGORY_ICON: Record<string, React.ElementType> = {
  memory:         Brain,
  metadata:       FileSearch,
  mobile_ios:     Smartphone,
  mobile_android: Smartphone,
}
const CATEGORY_COLOR: Record<string, string> = {
  memory:         'text-forensic-cyan',
  metadata:       'text-forensic-amber',
  mobile_ios:     'text-forensic-green',
  mobile_android: 'text-emerald-400',
}
const CATEGORY_BG: Record<string, string> = {
  memory:         'bg-forensic-cyan/10',
  metadata:       'bg-forensic-amber/10',
  mobile_ios:     'bg-forensic-green/10',
  mobile_android: 'bg-emerald-500/10',
}
const CATEGORY_BORDER: Record<string, string> = {
  memory:         'border-forensic-cyan/30',
  metadata:       'border-forensic-amber/30',
  mobile_ios:     'border-forensic-green/30',
  mobile_android: 'border-emerald-500/30',
}
const CATEGORY_LABEL: Record<string, string> = {
  memory:         'Memory Analysis',
  metadata:       'Metadata Extraction',
  mobile_ios:     'iOS Forensics',
  mobile_android: 'Android Forensics',
}
const TOOL_LABEL: Record<string, string> = {
  volatility: 'Volatility 3',
  exiftool:   'ExifTool',
  ileapp:     'iLEAPP',
  aleapp:     'aLEAPP',
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} MB`
  return `${(bytes / 1024 ** 3).toFixed(2)} GB`
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; icon: React.ElementType; cls: string }> = {
    queued:      { label: 'En attente',  icon: Clock,        cls: 'border-border/50 text-muted-foreground' },
    running:     { label: 'En cours',   icon: Activity,     cls: 'border-forensic-cyan/30 text-forensic-cyan' },
    normalizing: { label: 'Normalisation', icon: Activity,  cls: 'border-forensic-amber/30 text-forensic-amber' },
    completed:   { label: 'Terminé',    icon: CheckCircle2, cls: 'border-forensic-green/30 text-forensic-green' },
    done:        { label: 'Terminé',    icon: CheckCircle2, cls: 'border-forensic-green/30 text-forensic-green' },
    failed:      { label: 'Échec',      icon: XCircle,      cls: 'border-destructive/30 text-destructive' },
  }
  const s = map[status] ?? map.queued
  const Icon = s.icon
  return (
    <Badge variant="outline" className={`font-mono text-xs gap-1 ${s.cls}`}>
      <Icon className="size-3" />
      {s.label}
    </Badge>
  )
}

// ── Main Component ────────────────────────────────────────────────────────────

interface Props { slug: string }

export function ToolDetailPage({ slug }: Props) {
  const { data: toolsData, isLoading: toolsLoading } = useListTools()
  const tool = toolsData?.tools.find((t) => t.name === slug)

  const [selectedFeature, setSelectedFeature] = useState<ToolFeature | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [jobId, setJobId] = useState<string | null>(null)
  const [jobFilename, setJobFilename] = useState<string>('')
  const [jobSizeBytes, setJobSizeBytes] = useState<number>(0)
  const [validationError, setValidationError] = useState<string | null>(null)

  const fileInputRef = useRef<HTMLInputElement>(null)
  const { mutateAsync: directAnalyze, isPending: isAnalyzing } = useDirectAnalyze()
  const { data: jobData } = useJob(jobId ?? undefined)

  const Icon = CATEGORY_ICON[tool?.category ?? ''] ?? Cpu
  const color = CATEGORY_COLOR[tool?.category ?? ''] ?? 'text-muted-foreground'
  const bg = CATEGORY_BG[tool?.category ?? ''] ?? 'bg-muted'
  const border = CATEGORY_BORDER[tool?.category ?? ''] ?? 'border-border/50'
  const label = TOOL_LABEL[slug] ?? slug

  // ── File validation ────────────────────────────────────────────────────────

  const validateFile = useCallback(
    (f: File): string | null => {
      if (f.size > 5 * 1024 ** 3) return 'File exceeds 5 GB limit.'
      if (!selectedFeature) return null
      const exts = selectedFeature.accepted_extensions
      if (exts.includes('*')) return null
      const ext = '.' + f.name.split('.').pop()?.toLowerCase()
      if (!exts.includes(ext)) return `Unsupported format. Accepted: ${exts.join(', ')}`
      return null
    },
    [selectedFeature],
  )

  const handleFileSelect = (f: File) => {
    setValidationError(null)
    setFile(f)
    setJobId(null)
  }

  // ── Drag & Drop ────────────────────────────────────────────────────────────

  const onDragOver = (e: React.DragEvent) => { e.preventDefault(); setDragActive(true) }
  const onDragLeave = () => setDragActive(false)
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault(); setDragActive(false)
    const f = e.dataTransfer.files[0]
    if (f) handleFileSelect(f)
  }

  // ── Submit ─────────────────────────────────────────────────────────────────

  const handleAnalyze = async () => {
    if (!file || !selectedFeature) return
    const err = validateFile(file)
    if (err) { setValidationError(err); return }

    setUploadProgress(0)
    try {
      const res = await directAnalyze({
        file,
        tool: slug,
        feature: selectedFeature.id,
        onProgress: setUploadProgress,
      })
      setJobId(res.job_id)
      setJobFilename(res.filename)
      setJobSizeBytes(res.size_bytes)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setValidationError(msg ?? 'Erreur lors de la soumission. Vérifiez que le backend est démarré.')
    }
  }

  // ── Download results ───────────────────────────────────────────────────────

  const handleDownload = () => {
    if (!jobData?.findings) return
    const blob = new Blob([JSON.stringify(jobData.findings, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${slug}_${selectedFeature?.id ?? 'results'}_${jobId?.slice(0, 8)}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const isDone = jobData?.status === 'done' || jobData?.status === 'completed'
  const isFailed = jobData?.status === 'failed'
  const isRunning = jobData?.status === 'queued' || jobData?.status === 'running' || jobData?.status === 'normalizing'

  // ── Render ─────────────────────────────────────────────────────────────────

  if (toolsLoading) {
    return (
      <div className="flex flex-col gap-4 p-6">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-12 w-64" />
        <div className="flex gap-4 mt-4">
          <Skeleton className="h-96 w-56 rounded-xl" />
          <Skeleton className="h-96 flex-1 rounded-xl" />
        </div>
      </div>
    )
  }

  if (!tool) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 p-12 text-center">
        <FileWarning className="size-12 text-muted-foreground" />
        <h2 className="font-mono font-semibold">Outil &quot;{slug}&quot; introuvable</h2>
        <p className="text-sm text-muted-foreground">Vérifiez que le backend est démarré et que l&apos;outil est enregistré.</p>
        <Button asChild variant="outline" size="sm">
          <Link href="/"><ArrowLeft className="mr-2 size-4" />Retour</Link>
        </Button>
      </div>
    )
  }

  const features: ToolFeature[] = tool.features ?? []

  return (
    <div className="flex flex-col h-full">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 border-b border-border/40 px-6 py-4">
        <Button asChild variant="ghost" size="icon" className="size-8 shrink-0">
          <Link href="/"><ArrowLeft className="size-4" /></Link>
        </Button>
        <div className={`flex size-9 items-center justify-center rounded-lg ${bg}`}>
          <Icon className={`size-5 ${color}`} />
        </div>
        <div>
          <h1 className="font-mono font-bold tracking-tight">{label}</h1>
          <p className="text-xs text-muted-foreground font-mono">{CATEGORY_LABEL[tool.category] ?? tool.category}</p>
        </div>
        <Badge variant="outline" className={`ml-2 font-mono text-[10px] ${border} ${color}`}>
          {features.length} {features.length === 1 ? 'feature' : 'features'}
        </Badge>
      </div>

      {/* ── Body ───────────────────────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">

        {/* ── Left: Feature list ──────────────────────────────────────────── */}
        <aside className="w-60 shrink-0 border-r border-border/40 flex flex-col">
          <div className="px-4 py-3 border-b border-border/30">
            <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
              Features
            </p>
          </div>
          <ScrollArea className="flex-1">
            <div className="flex flex-col gap-1 p-2">
              {features.map((feat, i) => {
                const isSelected = selectedFeature?.id === feat.id
                return (
                  <button
                    key={feat.id}
                    onClick={() => { setSelectedFeature(feat); setFile(null); setJobId(null); setValidationError(null) }}
                    className={`
                      w-full text-left rounded-lg border px-3 py-2.5 transition-all
                      ${isSelected
                        ? `${border} ${bg} ${color}`
                        : 'border-transparent hover:border-border/40 hover:bg-card/50 text-muted-foreground hover:text-foreground'
                      }
                    `}
                  >
                    <div className="flex items-center gap-2">
                      <span className={`font-mono text-[10px] font-bold ${isSelected ? color : 'text-muted-foreground/50'}`}>
                        F{i + 1}
                      </span>
                      <span className="font-mono text-xs font-medium truncate">{feat.label}</span>
                      {isSelected && <ChevronRight className={`ml-auto size-3 shrink-0 ${color}`} />}
                    </div>
                  </button>
                )
              })}
            </div>
          </ScrollArea>
        </aside>

        {/* ── Right: Main panel ───────────────────────────────────────────── */}
        <main className="flex-1 overflow-auto">
          {!selectedFeature ? (
            /* Placeholder */
            <div className="flex h-full flex-col items-center justify-center gap-3 text-center p-8">
              <div className={`flex size-16 items-center justify-center rounded-2xl ${bg}`}>
                <Icon className={`size-8 ${color}`} />
              </div>
              <p className="font-mono text-sm text-muted-foreground">
                Sélectionne une feature à gauche pour commencer
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-6 p-6">

              {/* Feature header */}
              <div className="flex flex-col gap-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <h2 className="font-mono font-semibold">{selectedFeature.label}</h2>
                  <Badge variant="outline" className={`font-mono text-[10px] ${border} ${color}`}>
                    {selectedFeature.id}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed max-w-lg">
                  {selectedFeature.description}
                </p>
                {selectedFeature.accepted_extensions.length > 0 && !selectedFeature.accepted_extensions.includes('*') && (
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider">Formats :</span>
                    {selectedFeature.accepted_extensions.map((ext) => (
                      <Badge key={ext} variant="outline" className="font-mono text-[10px] border-border/40">
                        {ext}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>

              {/* Upload zone */}
              <Card className="border-border/40 bg-card/30">
                <CardHeader className="pb-3">
                  <CardTitle className="font-mono text-sm">Upload &amp; Analyse</CardTitle>
                </CardHeader>
                <CardContent className="flex flex-col gap-4">

                  {/* Drop zone */}
                  <div
                    role="button"
                    tabIndex={0}
                    onClick={() => fileInputRef.current?.click()}
                    onKeyDown={(e) => e.key === 'Enter' && fileInputRef.current?.click()}
                    onDragOver={onDragOver}
                    onDragLeave={onDragLeave}
                    onDrop={onDrop}
                    className={`
                      relative flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed
                      p-8 text-center transition-all cursor-pointer select-none
                      ${dragActive
                        ? `${border} ${bg}`
                        : file
                          ? 'border-forensic-green/40 bg-forensic-green/5'
                          : 'border-border/40 hover:border-border/70 hover:bg-card/50'
                      }
                    `}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      className="hidden"
                      onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFileSelect(f) }}
                    />
                    {file ? (
                      <>
                        <CheckCircle2 className="size-8 text-forensic-green" />
                        <div>
                          <p className="font-mono text-sm font-medium text-forensic-green">{file.name}</p>
                          <p className="text-xs text-muted-foreground font-mono mt-0.5">{formatBytes(file.size)}</p>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-xs font-mono text-muted-foreground"
                          onClick={(e) => { e.stopPropagation(); setFile(null); setJobId(null); setValidationError(null) }}
                        >
                          Changer de fichier
                        </Button>
                      </>
                    ) : (
                      <>
                        <Upload className={`size-8 ${dragActive ? color : 'text-muted-foreground'}`} />
                        <div>
                          <p className="font-mono text-sm font-medium">
                            {dragActive ? 'Dépose le fichier ici' : 'Dépose ton fichier ou clique pour parcourir'}
                          </p>
                          <p className="text-xs text-muted-foreground font-mono mt-0.5">
                            {selectedFeature.accepted_extensions.includes('*')
                              ? 'Tous types de fichiers acceptés · Max 5 GB'
                              : `${selectedFeature.accepted_extensions.join(', ')} · Max 5 GB`
                            }
                          </p>
                        </div>
                      </>
                    )}
                  </div>

                  {/* Validation error */}
                  {validationError && (
                    <p className="text-xs font-mono text-destructive flex items-center gap-1">
                      <XCircle className="size-3 shrink-0" />
                      {validationError}
                    </p>
                  )}

                  {/* Upload progress */}
                  {isAnalyzing && uploadProgress < 100 && (
                    <div className="flex flex-col gap-1.5">
                      <div className="flex justify-between text-[10px] font-mono text-muted-foreground">
                        <span>Upload en cours…</span>
                        <span>{uploadProgress}%</span>
                      </div>
                      <Progress value={uploadProgress} className="h-1.5" />
                    </div>
                  )}

                  {/* Launch button */}
                  <Button
                    onClick={handleAnalyze}
                    disabled={!file || isAnalyzing}
                    className={`w-full font-mono ${bg} ${color} border ${border} hover:opacity-80`}
                    variant="ghost"
                  >
                    {isAnalyzing ? (
                      <>
                        <Activity className="mr-2 size-4 animate-pulse" />
                        {uploadProgress < 100 ? 'Upload…' : 'Analyse en cours…'}
                      </>
                    ) : (
                      <>
                        <Play className="mr-2 size-4" />
                        Lancer l&apos;analyse
                      </>
                    )}
                  </Button>
                </CardContent>
              </Card>

              {/* Results */}
              {jobId && (
                <Card className="border-border/40 bg-card/30">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <CardTitle className="font-mono text-sm">Résultats</CardTitle>
                      {jobData?.status && <StatusBadge status={jobData.status} />}
                    </div>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-4">

                    {/* File info */}
                    <div className="grid grid-cols-2 gap-2 text-xs font-mono sm:grid-cols-4">
                      {[
                        { label: 'Fichier',   value: jobFilename || file?.name },
                        { label: 'Taille',    value: formatBytes(jobSizeBytes || file?.size || 0) },
                        { label: 'Outil',     value: label },
                        { label: 'Feature',   value: selectedFeature.label },
                      ].map(({ label: l, value }) => (
                        <div key={l} className="rounded-lg border border-border/30 bg-background/50 p-2">
                          <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-0.5">{l}</p>
                          <p className="truncate text-foreground">{value}</p>
                        </div>
                      ))}
                    </div>

                    {/* Polling indicator */}
                    {isRunning && (
                      <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground">
                        <Activity className="size-3 animate-pulse text-forensic-cyan" />
                        Polling toutes les 3s…
                        <span className="text-forensic-cyan">{jobData?.status}</span>
                      </div>
                    )}

                    {/* Error */}
                    {isFailed && (
                      <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-xs font-mono text-destructive">
                        <p className="font-semibold mb-1">Analyse échouée</p>
                        <p>{jobData?.error ?? 'Erreur inconnue'}</p>
                      </div>
                    )}

                    {/* Findings */}
                    {isDone && (() => {
                      const findings = jobData?.findings as Array<Record<string, unknown>> | undefined
                      if (!findings || findings.length === 0) {
                        return (
                          <div className="rounded-lg border border-border/30 bg-card/30 p-3 text-xs font-mono text-muted-foreground">
                            Aucun résultat retourné. Vérifiez que le fichier est compatible avec la feature sélectionnée et que l&apos;image Docker de l&apos;outil est bien buildée.
                          </div>
                        )
                      }

                      // Error finding from tool (e.g. Volatility missing symbols)
                      const first = findings[0]
                      if (first?.artifact_type === '_error') {
                        const msg = (first.data as Record<string, string>)?.message ?? ''
                        return (
                          <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 flex flex-col gap-2">
                            <p className="text-xs font-mono font-semibold text-amber-400 flex items-center gap-1">
                              <XCircle className="size-3" />
                              L&apos;outil a terminé sans résultat — message de l&apos;outil :
                            </p>
                            <ScrollArea className="max-h-48">
                              <pre className="text-[10px] font-mono text-amber-300/80 whitespace-pre-wrap break-all leading-relaxed">
                                {msg}
                              </pre>
                            </ScrollArea>
                          </div>
                        )
                      }

                      // Normal results table
                      const dataKeys = first?.data && typeof first.data === 'object' && !Array.isArray(first.data)
                        ? Object.keys(first.data as Record<string, unknown>)
                        : null
                      return (
                        <div className="flex flex-col gap-2">
                          <p className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
                            {findings.length} résultat{findings.length !== 1 ? 's' : ''}
                          </p>
                          {dataKeys ? (
                            <ScrollArea className="max-h-96 rounded-lg border border-border/30 bg-background/50">
                              <div className="overflow-x-auto">
                                <table className="w-full text-[10px] font-mono">
                                  <thead>
                                    <tr className="border-b border-border/30 bg-card/50 sticky top-0">
                                      {dataKeys.map((col) => (
                                        <th key={col} className="px-2 py-1.5 text-left text-muted-foreground whitespace-nowrap font-semibold uppercase tracking-wider">
                                          {col}
                                        </th>
                                      ))}
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {findings.map((f, i) => (
                                      <tr key={i} className="border-b border-border/20 hover:bg-card/30 transition-colors">
                                        {Object.values(f.data as Record<string, unknown>).map((val, j) => (
                                          <td key={j} className="px-2 py-1 whitespace-nowrap text-foreground/80">
                                            {val === null || val === undefined
                                              ? <span className="text-muted-foreground/40">—</span>
                                              : String(val)}
                                          </td>
                                        ))}
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </ScrollArea>
                          ) : (
                            <ScrollArea className="max-h-72 rounded-lg border border-border/30 bg-background/50">
                              <pre className="p-3 text-[11px] font-mono leading-relaxed whitespace-pre-wrap break-all">
                                {JSON.stringify(findings, null, 2)}
                              </pre>
                            </ScrollArea>
                          )}
                          <Button
                            onClick={handleDownload}
                            variant="outline"
                            size="sm"
                            className="w-full font-mono text-xs border-forensic-green/30 text-forensic-green hover:bg-forensic-green/10"
                          >
                            <Download className="mr-2 size-4" />
                            Télécharger les résultats (JSON)
                          </Button>
                        </div>
                      )
                    })()}
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  )
}

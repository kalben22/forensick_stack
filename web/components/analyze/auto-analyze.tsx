"use client"

import * as React from "react"
import {
  Upload,
  Radar,
  Cpu,
  HardDrive,
  Smartphone,
  Network,
  FileCode,
  FileSearch,
  Fingerprint,
  Zap,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Loader2,
  SkipForward,
  ShieldAlert,
  X,
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useCases } from "@/lib/hooks/use-cases"
import { useIdentify, useAutoAnalyze, usePlanStatus } from "@/lib/hooks/use-analyze"
import type { ArtifactIdentity, PlanStep, SkippedTool } from "@/lib/api/analyze"
import { formatBytes } from "@/lib/utils"

// Family → visual identity. Mirrors KindFamily on the backend.
const FAMILY_STYLE: Record<string, { icon: React.ElementType; color: string; label: string }> = {
  memory:           { icon: Cpu,        color: "text-forensic-cyan",   label: "Mémoire" },
  disk:             { icon: HardDrive,  color: "text-forensic-amber",  label: "Disque" },
  mobile:           { icon: Smartphone, color: "text-forensic-green",  label: "Mobile" },
  windows_artifact: { icon: FileCode,   color: "text-forensic-violet", label: "Artefact Windows" },
  network:          { icon: Network,    color: "text-forensic-red",    label: "Réseau" },
  document:         { icon: FileSearch, color: "text-forensic-amber",  label: "Document" },
  executable:       { icon: FileCode,   color: "text-forensic-red",    label: "Exécutable" },
  archive:          { icon: HardDrive,  color: "text-muted-foreground", label: "Archive" },
  opaque:           { icon: ShieldAlert, color: "text-forensic-red",   label: "Chiffré / opaque" },
  data:             { icon: FileSearch, color: "text-muted-foreground", label: "Données" },
  unknown:          { icon: AlertCircle, color: "text-muted-foreground", label: "Inconnu" },
}

function familyStyle(family: string) {
  return FAMILY_STYLE[family] ?? FAMILY_STYLE.unknown
}

// A DFIR analyst reads confidence as a trust signal on the whole plan.
function confidenceTone(conf: number): { label: string; color: string } {
  if (conf >= 0.75) return { label: "élevée", color: "text-forensic-green" }
  if (conf >= 0.4) return { label: "moyenne", color: "text-forensic-amber" }
  return { label: "faible", color: "text-forensic-red" }
}

const TERMINAL = new Set(["completed", "done", "failed", "cancelled"])

function jobTone(status: string): { icon: React.ElementType; color: string; spin?: boolean } {
  switch (status) {
    case "completed":
    case "done":
      return { icon: CheckCircle2, color: "text-forensic-green" }
    case "failed":
      return { icon: XCircle, color: "text-forensic-red" }
    case "cancelled":
      return { icon: X, color: "text-muted-foreground" }
    case "running":
    case "normalizing":
      return { icon: Loader2, color: "text-forensic-cyan", spin: true }
    default:
      return { icon: Loader2, color: "text-muted-foreground", spin: true }
  }
}

export function AutoAnalyze() {
  const fileInputRef = React.useRef<HTMLInputElement>(null)
  const [dragActive, setDragActive] = React.useState(false)
  const [file, setFile] = React.useState<File | null>(null)
  const [selectedCaseId, setSelectedCaseId] = React.useState<string>("")
  const [planId, setPlanId] = React.useState<string | undefined>(undefined)

  const { data: casesData } = useCases({ limit: 100 })
  const identify = useIdentify()
  const analyze = useAutoAnalyze()
  const plan = usePlanStatus(planId)

  // The dry-run result (identity + plan) is what we render before committing.
  const preview = identify.data
  const identity: ArtifactIdentity | undefined = preview?.identity ?? analyze.data?.identity
  const steps: PlanStep[] = preview?.plan.steps ?? analyze.data?.plan.steps ?? []
  const skipped: SkippedTool[] = preview?.plan.skipped ?? analyze.data?.plan.skipped ?? []
  const notes: string[] = preview?.plan.notes ?? analyze.data?.plan.notes ?? []
  const advice = preview?.advice ?? analyze.data?.advice ?? ""

  const caseIdNum = selectedCaseId ? Number(selectedCaseId) : undefined
  const busy = identify.isPending || analyze.isPending

  const reset = () => {
    setFile(null)
    setPlanId(undefined)
    identify.reset()
    analyze.reset()
    if (fileInputRef.current) fileInputRef.current.value = ""
  }

  const onPick = (f: File) => {
    // New file → drop any previous verdict, then auto-identify (dry run, cheap).
    setPlanId(undefined)
    analyze.reset()
    setFile(f)
    identify.mutate({ file: f })
  }

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(false)
    const f = e.dataTransfer.files[0]
    if (f) onPick(f)
  }

  const launch = () => {
    if (!file) return
    analyze.mutate(
      { file, caseId: caseIdNum },
      { onSuccess: (res) => setPlanId(res.plan_id) },
    )
  }

  const fam = identity ? familyStyle(identity.family) : null
  const FamIcon = fam?.icon ?? Radar
  const conf = identity ? confidenceTone(identity.confidence) : null
  const queued = plan.data
  const launched = !!planId

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold font-mono tracking-tight">
            <Radar className="size-6 text-forensic-cyan" />
            Triage automatique
          </h1>
          <p className="text-sm text-muted-foreground font-mono">
            Dépose un artefact — le système l&apos;identifie par son contenu et lance seul les bons outils.
          </p>
        </div>
        {file && (
          <Button variant="ghost" size="sm" className="font-mono text-muted-foreground" onClick={reset}>
            <X className="size-4 mr-1" /> Recommencer
          </Button>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* ── Left: dropzone + verdict + plan ─────────────────────────────── */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          <input
            ref={fileInputRef}
            type="file"
            aria-label="Artefact à analyser"
            className="sr-only"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) onPick(f) }}
          />

          {!file ? (
            <Card
              className={`border-2 border-dashed transition-colors cursor-pointer ${
                dragActive ? "border-forensic-cyan bg-forensic-cyan/5" : "border-border/50 bg-card/50 hover:border-forensic-cyan/30"
              }`}
              role="button"
              tabIndex={0}
              aria-label="Choisir un artefact à analyser"
              onClick={() => fileInputRef.current?.click()}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); fileInputRef.current?.click() } }}
              onDragOver={(e) => { e.preventDefault(); setDragActive(true) }}
              onDragLeave={() => setDragActive(false)}
              onDrop={onDrop}
            >
              <CardContent className="flex flex-col items-center justify-center py-16">
                <div className={`flex size-16 items-center justify-center rounded-full mb-4 ${dragActive ? "bg-forensic-cyan/20" : "bg-muted"}`}>
                  <Upload className={`size-8 ${dragActive ? "text-forensic-cyan" : "text-muted-foreground"}`} />
                </div>
                <p className="text-lg font-medium">Dépose n&apos;importe quel artefact</p>
                <p className="text-sm text-muted-foreground mt-1">
                  dump mémoire, image disque, backup mobile, pcap, hive… ou un fichier inconnu de CTF
                </p>
                <p className="text-xs text-muted-foreground/70 mt-3 font-mono">
                  Aucune extension requise — l&apos;identification se fait par le contenu.
                </p>
              </CardContent>
            </Card>
          ) : (
            <Card className="border-border/50 bg-card/50">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className={`flex size-11 items-center justify-center rounded-lg bg-muted ${fam?.color ?? ""}`}>
                    {identify.isPending ? <Loader2 className="size-5 animate-spin text-forensic-cyan" /> : <FamIcon className="size-5" />}
                  </div>
                  <div className="min-w-0">
                    <p className="font-mono font-semibold truncate">{file.name}</p>
                    <p className="text-xs text-muted-foreground font-mono">{formatBytes(file.size)}</p>
                  </div>
                  {identify.isPending && (
                    <span className="ml-auto text-xs font-mono text-muted-foreground">Identification…</span>
                  )}
                </div>

                {identify.isError && (
                  <div className="mt-3 flex items-center gap-2 text-sm text-destructive font-mono">
                    <AlertCircle className="size-4" />
                    {identify.error?.message ?? "Échec de l'identification"}
                  </div>
                )}

                {identity && (
                  <>
                    <Separator className="my-4" />
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="outline" className={`font-mono ${fam?.color ?? ""} border-current/30`}>
                        <FamIcon className="size-3 mr-1" />
                        {identity.label || identity.kind}
                      </Badge>
                      <Badge variant="outline" className="font-mono text-[10px] border-border/50">
                        {identity.kind}
                      </Badge>
                      {identity.os_hint && (
                        <Badge variant="outline" className="font-mono text-[10px] border-border/50">
                          OS: {identity.os_hint}
                        </Badge>
                      )}
                      {conf && (
                        <span className={`ml-auto text-xs font-mono ${conf.color}`}>
                          confiance {conf.label} · {(identity.confidence * 100).toFixed(0)}%
                        </span>
                      )}
                    </div>

                    <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-[11px] font-mono text-muted-foreground sm:grid-cols-3">
                      <Metric label="entropie" value={identity.entropy.toFixed(2)} />
                      <Metric label="imprimable" value={`${(identity.printable_ratio * 100).toFixed(0)}%`} />
                      <Metric label="page-aligné" value={identity.page_aligned ? "oui" : "non"} />
                      {identity.mime && <Metric label="mime" value={identity.mime} />}
                      <Metric label="taille" value={formatBytes(identity.size)} />
                    </div>

                    <div className="mt-2 flex items-center gap-2">
                      <Fingerprint className="size-3 text-muted-foreground shrink-0" />
                      <code className="text-[10px] text-muted-foreground truncate" title={identity.sha256}>
                        sha256:{identity.sha256}
                      </code>
                    </div>

                    {identity.evidence.length > 0 && (
                      <div className="mt-3">
                        <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground mb-1">Indices</p>
                        <ul className="space-y-0.5">
                          {identity.evidence.slice(0, 5).map((e, i) => (
                            <li key={i} className="text-[11px] font-mono text-muted-foreground/90">· {e}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {identity.alternatives.length > 0 && (
                      <p className="mt-2 text-[11px] font-mono text-muted-foreground">
                        Hypothèses alternatives : {identity.alternatives.map((a) => `${a.kind} (${(a.confidence * 100).toFixed(0)}%)`).join(", ")}
                      </p>
                    )}
                  </>
                )}
              </CardContent>
            </Card>
          )}

          {/* ── The plan: what will run, and WHY ──────────────────────────── */}
          {identity && (
            <Card className="border-border/50 bg-card/50">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-sm font-mono uppercase tracking-wider text-muted-foreground">
                  <Zap className="size-3.5 text-forensic-cyan" />
                  Plan d&apos;analyse
                  <Badge variant="outline" className="ml-1 font-mono text-[10px] border-border/50">
                    {steps.length} étape{steps.length > 1 ? "s" : ""}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-2 pt-0">
                {steps.length === 0 && (
                  <div className="flex items-center gap-2 text-sm font-mono text-forensic-amber">
                    <AlertCircle className="size-4" />
                    Aucun outil ne déclare supporter cet artefact.
                  </div>
                )}

                {steps.map((s, i) => {
                  const live = queued?.jobs.find((j) => j.tool === s.tool && j.feature === s.feature)
                  const status = live?.status
                  const tone = status ? jobTone(status) : null
                  const ToneIcon = tone?.icon
                  return (
                    <div key={`${s.tool}/${s.feature}`} className="flex items-start gap-3 rounded-lg border border-border/40 bg-background/40 px-3 py-2">
                      <div className="mt-0.5 flex size-5 items-center justify-center rounded-full bg-muted text-[10px] font-mono text-muted-foreground shrink-0">
                        {i + 1}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-sm text-forensic-cyan">{s.tool}</span>
                          <span className="font-mono text-xs text-muted-foreground">/ {s.feature}</span>
                          {s.stage > 1 && (
                            <Badge variant="outline" className="font-mono text-[9px] border-border/40">étape {s.stage}</Badge>
                          )}
                        </div>
                        <p className="text-[11px] font-mono text-muted-foreground/90 mt-0.5">{s.reason}</p>
                        {live?.findings != null && status && TERMINAL.has(status) && status !== "failed" && (
                          <p className="text-[11px] font-mono text-forensic-green mt-0.5">{live.findings} résultat(s)</p>
                        )}
                        {live?.error && (
                          <p className="text-[11px] font-mono text-forensic-red mt-0.5 truncate" title={live.error}>{live.error}</p>
                        )}
                      </div>
                      {ToneIcon && tone && (
                        <ToneIcon className={`size-4 shrink-0 ${tone.color} ${tone.spin ? "animate-spin" : ""}`} />
                      )}
                    </div>
                  )
                })}

                {skipped.length > 0 && (
                  <>
                    <Separator className="my-1" />
                    <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Écartés</p>
                    {skipped.map((sk) => (
                      <div key={sk.target} className="flex items-start gap-2 text-[11px] font-mono text-muted-foreground/70">
                        <SkipForward className="size-3 mt-0.5 shrink-0" />
                        <span><span className="text-muted-foreground">{sk.target}</span> — {sk.reason}</span>
                      </div>
                    ))}
                  </>
                )}

                {notes.map((n, i) => (
                  <p key={i} className="text-[11px] font-mono text-muted-foreground/70">ℹ {n}</p>
                ))}
              </CardContent>
            </Card>
          )}
        </div>

        {/* ── Right: launch panel ─────────────────────────────────────────── */}
        <div className="flex flex-col gap-4">
          <Card className="border-border/50 bg-card/50">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-mono uppercase tracking-wider text-muted-foreground">Lancement</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div className="flex flex-col gap-2">
                <Label className="font-mono text-xs text-muted-foreground">Rattacher à un dossier (optionnel)</Label>
                <Select value={selectedCaseId} onValueChange={setSelectedCaseId}>
                  <SelectTrigger className="font-mono text-xs">
                    <SelectValue placeholder="Aucun — triage libre" />
                  </SelectTrigger>
                  <SelectContent>
                    {casesData?.cases
                      ?.filter((c) => c.status === "open")
                      .map((c) => (
                        <SelectItem key={c.id} value={String(c.id)} className="font-mono text-xs">
                          {c.case_number} — {c.title}
                        </SelectItem>
                      )) ?? (
                      <SelectItem value="__loading" disabled className="font-mono text-xs">
                        Chargement…
                      </SelectItem>
                    )}
                  </SelectContent>
                </Select>
                <p className="text-[10px] font-mono text-muted-foreground/60">
                  Sans dossier, le triage tourne quand même — utile pour un CTF rapide.
                </p>
              </div>

              {advice && (
                <div className="rounded-lg border border-forensic-cyan/20 bg-forensic-cyan/5 px-3 py-2">
                  <p className="text-[11px] font-mono text-muted-foreground">{advice}</p>
                </div>
              )}

              {!launched ? (
                <Button
                  className="bg-forensic-cyan text-background hover:bg-forensic-cyan/90 font-mono gap-2"
                  onClick={launch}
                  disabled={!identity || steps.length === 0 || busy}
                >
                  {analyze.isPending ? <Loader2 className="size-4 animate-spin" /> : <Zap className="size-4" />}
                  {analyze.isPending ? "Mise en file…" : `Lancer l'analyse${steps.length ? ` (${steps.length})` : ""}`}
                </Button>
              ) : (
                <div className="flex flex-col gap-2">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="text-muted-foreground">
                      {queued ? `${queued.finished}/${queued.total} terminés` : "Démarrage…"}
                    </span>
                    <span className="text-forensic-cyan">{queued ? `${Math.round(queued.progress * 100)}%` : ""}</span>
                  </div>
                  <Progress value={queued ? queued.progress * 100 : 5} className="h-2" />
                  {queued && queued.total > 0 && queued.finished >= queued.total && (
                    <div className="flex items-center gap-2 text-xs font-mono text-forensic-green mt-1">
                      <CheckCircle2 className="size-4" /> Analyse terminée
                    </div>
                  )}
                  <p className="text-[10px] font-mono text-muted-foreground/60">
                    Plan <code>{planId?.slice(0, 12)}</code> — suivi en direct. Résultats dans Findings.
                  </p>
                </div>
              )}

              {analyze.isError && (
                <div className="flex items-center gap-2 text-xs text-destructive font-mono">
                  <AlertCircle className="size-4" />
                  {analyze.error?.message ?? "Échec de la mise en file"}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="border-border/50 bg-card/50">
            <CardContent className="p-4">
              <p className="text-[11px] font-mono text-muted-foreground/80 leading-relaxed">
                <span className="text-forensic-cyan">Comment ça marche —</span> identification par contenu
                (magic, marqueurs kernel, entropie), puis planification depuis les manifestes de plugins.
                Les outils incompatibles (mauvais OS, taille) sont écartés et la raison est affichée : jamais de troncature silencieuse.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center gap-1 truncate">
      <span className="text-muted-foreground/60">{label}:</span>
      <span className="text-muted-foreground">{value}</span>
    </div>
  )
}

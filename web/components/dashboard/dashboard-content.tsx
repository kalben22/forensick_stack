'use client'

import Link from 'next/link'
import {
  Brain,
  Smartphone,
  FileSearch,
  ArrowRight,
  Shield,
  Cpu,
  GitBranch,
  Layers,
} from 'lucide-react'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useListTools } from '@/lib/hooks/use-jobs'
import type { ToolInfo } from '@/lib/api/jobs'

// ── Static metadata per tool slug ────────────────────────────────────────────

const TOOL_META: Record<
  string,
  { description: string; icon: React.ElementType; color: string; bg: string; border: string }
> = {
  volatility: {
    description:
      'Analyse de dump mémoire Windows/Linux. Extrait les processus, connexions réseau, DLLs chargées et détecte les injections de code.',
    icon: Brain,
    color: 'text-forensic-cyan',
    bg: 'bg-forensic-cyan/10',
    border: 'border-forensic-cyan/20',
  },
  exiftool: {
    description:
      'Extraction de métadonnées sur tout type de fichier : EXIF, XMP, GPS, informations caméra, timestamps et données embarquées.',
    icon: FileSearch,
    color: 'text-forensic-amber',
    bg: 'bg-forensic-amber/10',
    border: 'border-forensic-amber/20',
  },
  ileapp: {
    description:
      'Extraction et analyse d\'artefacts iOS : messages iMessage, appels, contacts, géolocalisation, historique Safari et applications.',
    icon: Smartphone,
    color: 'text-forensic-green',
    bg: 'bg-forensic-green/10',
    border: 'border-forensic-green/20',
  },
  aleapp: {
    description:
      'Extraction et analyse d\'artefacts Android : SMS, journaux d\'appels, applications installées, comptes Google et historique Chrome.',
    icon: Smartphone,
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/20',
  },
}

const CATEGORY_LABEL: Record<string, string> = {
  memory: 'Memory',
  metadata: 'Metadata',
  mobile_ios: 'iOS',
  mobile_android: 'Android',
  disk: 'Disk',
  network: 'Network',
  timeline: 'Timeline',
}

// ── Fallback tools shown while API loads or on error ─────────────────────────

const FALLBACK_TOOLS: ToolInfo[] = [
  { name: 'volatility', category: 'memory',         memory: '6g',   cpus: 2, timeout: 7200, features: [{id:'windows.pslist',label:'Process List',description:'',accepted_extensions:[]}] },
  { name: 'exiftool',  category: 'metadata',        memory: '512m', cpus: 0.5, timeout: 300, features: [{id:'all',label:'All Metadata',description:'',accepted_extensions:[]}] },
  { name: 'ileapp',    category: 'mobile_ios',      memory: '4g',   cpus: 2, timeout: 3600, features: [{id:'fs',label:'Full iOS Extraction',description:'',accepted_extensions:[]}] },
  { name: 'aleapp',    category: 'mobile_android',  memory: '4g',   cpus: 2, timeout: 3600, features: [{id:'fs',label:'Full Android Extraction',description:'',accepted_extensions:[]}] },
]

// ── Tool Card ─────────────────────────────────────────────────────────────────

function ToolCard({ tool, loading }: { tool: ToolInfo; loading?: boolean }) {
  const meta = TOOL_META[tool.name]
  const Icon = meta?.icon ?? Cpu
  const featureCount = tool.features?.length ?? 0
  const label = tool.name.charAt(0).toUpperCase() + tool.name.slice(1)

  if (loading) {
    return (
      <Card className="border-border/50 bg-card/50">
        <CardHeader className="pb-2">
          <Skeleton className="h-10 w-10 rounded-lg" />
          <Skeleton className="mt-3 h-5 w-24" />
          <Skeleton className="h-3 w-16" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-12 w-full" />
          <Skeleton className="mt-4 h-8 w-full" />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card
      className={`group relative flex flex-col border bg-card/50 transition-all duration-200 hover:shadow-md hover:shadow-black/20 ${meta?.border ?? 'border-border/50'} hover:border-opacity-60`}
    >
      <CardHeader className="pb-2">
        <div
          className={`flex size-10 items-center justify-center rounded-lg ${meta?.bg ?? 'bg-muted'}`}
        >
          <Icon className={`size-5 ${meta?.color ?? 'text-muted-foreground'}`} />
        </div>
        <div className="mt-3 flex items-center gap-2 flex-wrap">
          <h3 className="font-mono font-semibold tracking-tight">
            {label === 'Ileapp' ? 'iLEAPP' : label === 'Aleapp' ? 'aLEAPP' : label}
          </h3>
          <Badge
            variant="outline"
            className={`text-[10px] font-mono ${meta?.color ?? ''} border-current/30`}
          >
            {CATEGORY_LABEL[tool.category] ?? tool.category}
          </Badge>
        </div>
        <p className="text-[10px] font-mono text-muted-foreground">
          {featureCount} {featureCount === 1 ? 'feature' : 'features'}
        </p>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col justify-between gap-4">
        <p className="text-xs text-muted-foreground leading-relaxed">
          {meta?.description ?? `Forensic analysis tool — category: ${tool.category}`}
        </p>
        <Button
          asChild
          size="sm"
          className={`w-full justify-between font-mono text-xs ${meta?.bg ?? 'bg-muted'} ${meta?.color ?? ''} border ${meta?.border ?? ''} hover:opacity-80`}
          variant="ghost"
        >
          <Link href={`/tools/${tool.name}`}>
            Analyze
            <ArrowRight className="size-3 transition-transform group-hover:translate-x-1" />
          </Link>
        </Button>
      </CardContent>
    </Card>
  )
}

// ── Main Component ────────────────────────────────────────────────────────────

export function DashboardContent() {
  const { data: toolsData, isLoading, isError } = useListTools()

  const tools = isError || (!isLoading && !toolsData)
    ? FALLBACK_TOOLS
    : (toolsData?.tools ?? [])

  return (
    <div className="flex flex-col gap-10 p-6 max-w-5xl">

      {/* ── Platform Intro ─────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-4">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="flex size-12 items-center justify-center rounded-xl bg-forensic-cyan/10 border border-forensic-cyan/20">
              <Shield className="size-6 text-forensic-cyan" />
            </div>
            <div>
              <h1 className="text-2xl font-bold font-mono tracking-tight">ForensicStack</h1>
              <p className="text-sm text-forensic-cyan font-mono">DFIR Analysis Platform</p>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Badge variant="outline" className="font-mono text-[10px] border-forensic-cyan/30 text-forensic-cyan">
              v1.0
            </Badge>
            <Badge variant="outline" className="font-mono text-[10px] border-border/50 text-muted-foreground">
              Open Source
            </Badge>
            <Badge variant="outline" className="font-mono text-[10px] border-border/50 text-muted-foreground">
              Docker-based
            </Badge>
          </div>
        </div>

        <div className="rounded-xl border border-border/40 bg-card/30 p-5 flex flex-col gap-4">
          <p className="text-sm text-muted-foreground leading-relaxed max-w-2xl">
            Plateforme d'analyse forensique numérique pour les équipes DFIR. Exécutez des outils
            spécialisés dans des conteneurs Docker isolés, analysez des artefacts numériques et
            exportez les résultats de façon sécurisée.
          </p>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 text-xs font-mono">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Layers className="size-3.5 text-forensic-cyan shrink-0" />
              <span>Conteneurs Docker isolés (réseau coupé)</span>
            </div>
            <div className="flex items-center gap-2 text-muted-foreground">
              <GitBranch className="size-3.5 text-forensic-amber shrink-0" />
              <span>Résultats normalisés &amp; exportables</span>
            </div>
            <div className="flex items-center gap-2 text-muted-foreground">
              <Shield className="size-3.5 text-forensic-green shrink-0" />
              <span>Auth JWT · Audit log · RBAC</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Tools Grid ─────────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h2 className="font-mono text-sm font-semibold uppercase tracking-widest text-muted-foreground">
            Outils disponibles
          </h2>
          {isError && (
            <Badge variant="outline" className="text-[10px] font-mono border-forensic-amber/30 text-forensic-amber">
              Backend offline · données statiques
            </Badge>
          )}
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {isLoading
            ? Array.from({ length: 4 }).map((_, i) => (
                <ToolCard key={i} tool={FALLBACK_TOOLS[i]} loading />
              ))
            : tools.map((tool) => <ToolCard key={tool.name} tool={tool} />)}
        </div>
      </div>
    </div>
  )
}

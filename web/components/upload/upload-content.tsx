"use client"

import * as React from "react"
import {
  Upload,
  FileSearch,
  Cpu,
  HardDrive,
  Smartphone,
  Network,
  FileCode,
  Zap,
  Settings2,
  CheckCircle2,
  AlertCircle,
  X,
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Progress } from "@/components/ui/progress"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useCases } from "@/lib/hooks/use-cases"
import { useUploadArtifact } from "@/lib/hooks/use-artifacts"
import { useListTools } from "@/lib/hooks/use-jobs"
import { validateArtifactFile, type ArtifactType } from "@/lib/api/artifacts"
import { useToast } from "@/components/ui/use-toast"

const FILE_TYPE_MAP: Record<string, { label: string; icon: React.ElementType; artifactType: ArtifactType; color: string }> = {
  ".raw":    { label: "Memory Dump",      icon: Cpu,       artifactType: "memory_dump",    color: "text-forensic-cyan" },
  ".mem":    { label: "Memory Dump",      icon: Cpu,       artifactType: "memory_dump",    color: "text-forensic-cyan" },
  ".vmem":   { label: "Memory Dump",      icon: Cpu,       artifactType: "memory_dump",    color: "text-forensic-cyan" },
  ".E01":    { label: "Disk Image",       icon: HardDrive, artifactType: "disk_image",     color: "text-forensic-amber" },
  ".dd":     { label: "Disk Image (RAW)", icon: HardDrive, artifactType: "disk_image",     color: "text-forensic-amber" },
  ".tar.gz": { label: "Mobile Backup",   icon: Smartphone, artifactType: "mobile_backup", color: "text-forensic-green" },
  ".ab":     { label: "Android Backup",  icon: Smartphone, artifactType: "mobile_backup", color: "text-forensic-green" },
  ".pcap":   { label: "Network Capture", icon: Network,   artifactType: "pcap",           color: "text-forensic-red" },
  ".pcapng": { label: "Network Capture", icon: Network,   artifactType: "pcap",           color: "text-forensic-red" },
  ".evtx":   { label: "Event Log",       icon: FileCode,  artifactType: "evtx",           color: "text-forensic-violet" },
  ".DAT":    { label: "Registry Hive",   icon: FileCode,  artifactType: "registry",       color: "text-forensic-violet" },
}

function detectType(filename: string) {
  return Object.entries(FILE_TYPE_MAP).find(([ext]) => filename.endsWith(ext))?.[1] ?? null
}

export function UploadContent() {
  const fileInputRef = React.useRef<HTMLInputElement>(null)
  const [dragActive, setDragActive] = React.useState(false)
  const [selectedFile, setSelectedFile] = React.useState<File | null>(null)
  const [detectedInfo, setDetectedInfo] = React.useState<typeof FILE_TYPE_MAP[string] | null>(null)
  const [autoDetect, setAutoDetect] = React.useState(true)
  const [advancedOpen, setAdvancedOpen] = React.useState(false)
  const [selectedCaseId, setSelectedCaseId] = React.useState<string>("")
  const [validationError, setValidationError] = React.useState<string | null>(null)

  const { data: casesData } = useCases({ limit: 100 })
  const { data: toolsData } = useListTools()
  const { toast } = useToast()

  const caseIdNum = selectedCaseId ? Number(selectedCaseId) : undefined
  const { mutateAsync: upload, isPending: uploading, progress } = useUploadArtifact(caseIdNum)

  const handleFileSelect = (file: File) => {
    setSelectedFile(file)
    setValidationError(null)
    const info = detectType(file.name)
    setDetectedInfo(info)
  }

  const handleDragOver = (e: React.DragEvent) => { e.preventDefault(); setDragActive(true) }
  const handleDragLeave = () => setDragActive(false)
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFileSelect(file)
  }

  const handleBrowse = () => fileInputRef.current?.click()

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleFileSelect(file)
  }

  const handleAnalyze = async () => {
    if (!selectedFile || !detectedInfo || !caseIdNum) return

    const validation = validateArtifactFile(selectedFile, detectedInfo.artifactType)
    if (!validation.valid) {
      setValidationError(validation.error ?? "Invalid file")
      return
    }

    try {
      await upload({ file: selectedFile, artifactType: detectedInfo.artifactType })
      toast({
        title: "Upload successful",
        description: `${selectedFile.name} uploaded and queued for analysis.`,
      })
      setSelectedFile(null)
      setDetectedInfo(null)
      if (fileInputRef.current) fileInputRef.current.value = ""
    } catch (err: unknown) {
      const msg = (err as Error)?.message ?? "Upload failed."
      toast({ title: "Upload failed", description: msg, variant: "destructive" })
    }
  }

  const canAnalyze = !!selectedFile && !!detectedInfo && !!caseIdNum && !uploading

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-bold font-mono tracking-tight">Upload & Analyze</h1>
        <p className="text-sm text-muted-foreground font-mono">Upload evidence files for automated forensic analysis</p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Upload Zone */}
        <div className="lg:col-span-2 flex flex-col gap-6">

          {/* Hidden real file input */}
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            onChange={handleFileInputChange}
            accept=".raw,.mem,.vmem,.dmp,.E01,.dd,.img,.tar.gz,.ab,.pcap,.pcapng,.evtx,.DAT,.reg"
          />

          <Card
            className={`border-2 border-dashed transition-colors cursor-pointer ${
              dragActive
                ? "border-forensic-cyan bg-forensic-cyan/5"
                : selectedFile
                ? "border-forensic-green/50 bg-forensic-green/5"
                : "border-border/50 bg-card/50 hover:border-forensic-cyan/30"
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={!selectedFile ? handleBrowse : undefined}
          >
            <CardContent className="flex flex-col items-center justify-center py-16">
              {selectedFile ? (
                <>
                  <div className="flex size-16 items-center justify-center rounded-full bg-forensic-green/20 mb-4">
                    <CheckCircle2 className="size-8 text-forensic-green" />
                  </div>
                  <p className="text-lg font-mono font-semibold">{selectedFile.name}</p>
                  <p className="text-sm text-muted-foreground font-mono">
                    {(selectedFile.size / 1e9).toFixed(2)} GB
                  </p>
                  {detectedInfo && autoDetect && (
                    <div className="mt-4 flex items-center gap-3 rounded-lg border border-forensic-cyan/20 bg-forensic-cyan/5 px-4 py-3">
                      <FileSearch className="size-5 text-forensic-cyan" />
                      <div>
                        <p className="text-sm font-mono">
                          Detected: <span className={detectedInfo.color}>{detectedInfo.label}</span>
                        </p>
                      </div>
                    </div>
                  )}
                  {validationError && (
                    <div className="mt-3 flex items-center gap-2 text-sm text-destructive">
                      <AlertCircle className="size-4" />
                      {validationError}
                    </div>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    className="mt-3 text-muted-foreground hover:text-destructive"
                    onClick={(e) => { e.stopPropagation(); setSelectedFile(null); setDetectedInfo(null) }}
                  >
                    <X className="size-3 mr-1" /> Remove file
                  </Button>
                </>
              ) : (
                <>
                  <div className={`flex size-16 items-center justify-center rounded-full mb-4 ${
                    dragActive ? "bg-forensic-cyan/20" : "bg-muted"
                  }`}>
                    <Upload className={`size-8 ${dragActive ? "text-forensic-cyan" : "text-muted-foreground"}`} />
                  </div>
                  <p className="text-lg font-medium">Drop evidence files here</p>
                  <p className="text-sm text-muted-foreground mt-1">or click to browse</p>
                  <div className="mt-4 flex flex-wrap justify-center gap-2">
                    {[".raw", ".E01", ".dd", ".tar.gz", ".ab", ".pcap", ".evtx", ".DAT"].map((ext) => (
                      <Badge key={ext} variant="outline" className="font-mono text-[10px] border-border/50">
                        {ext}
                      </Badge>
                    ))}
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {/* Upload progress */}
          {uploading && (
            <Card className="border-border/50 bg-card/50">
              <CardContent className="p-4 space-y-2">
                <div className="flex items-center justify-between text-sm font-mono">
                  <span className="text-muted-foreground">Uploading…</span>
                  <span className="text-forensic-cyan">{progress}%</span>
                </div>
                <Progress value={progress} className="h-2" />
              </CardContent>
            </Card>
          )}

          {selectedFile && !uploading && (
            <Button
              className="bg-forensic-cyan text-background hover:bg-forensic-cyan/90 font-mono gap-2"
              onClick={handleAnalyze}
              disabled={!canAnalyze}
            >
              <Zap className="size-4" />
              {!caseIdNum ? "Select a case first…" : "Upload & Analyze"}
            </Button>
          )}
        </div>

        {/* Options Panel */}
        <div className="flex flex-col gap-4">
          <Card className="border-border/50 bg-card/50">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-mono uppercase tracking-wider text-muted-foreground">Analysis Options</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div className="flex flex-col gap-2">
                <Label className="font-mono text-xs text-muted-foreground">Assign to Case *</Label>
                <Select value={selectedCaseId} onValueChange={setSelectedCaseId}>
                  <SelectTrigger className="font-mono text-xs">
                    <SelectValue placeholder="Select case…" />
                  </SelectTrigger>
                  <SelectContent>
                    {casesData?.cases
                      .filter((c) => c.status === "open")
                      .map((c) => (
                        <SelectItem key={c.id} value={String(c.id)} className="font-mono text-xs">
                          {c.case_number} — {c.title}
                        </SelectItem>
                      )) ?? (
                        <SelectItem value="__loading" disabled className="font-mono text-xs text-muted-foreground">
                          Loading cases…
                        </SelectItem>
                      )}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center justify-between">
                <Label className="font-mono text-xs text-muted-foreground">Auto-detect type</Label>
                <Switch checked={autoDetect} onCheckedChange={setAutoDetect} />
              </div>
            </CardContent>
          </Card>

          <Collapsible open={advancedOpen} onOpenChange={setAdvancedOpen}>
            <Card className="border-border/50 bg-card/50">
              <CollapsibleTrigger asChild>
                <CardHeader className="pb-3 cursor-pointer">
                  <CardTitle className="flex items-center gap-2 text-sm font-mono uppercase tracking-wider text-muted-foreground">
                    <Settings2 className="size-3" />
                    Available Tools
                  </CardTitle>
                </CardHeader>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <CardContent className="flex flex-col gap-2 pt-0">
                  {toolsData?.tools?.map((tool) => (
                    <div key={tool.name} className="flex items-center justify-between text-xs font-mono">
                      <span className="text-forensic-cyan">{tool.name}</span>
                      <Badge variant="outline" className="text-[9px] border-border/30">{tool.category}</Badge>
                    </div>
                  )) ?? (
                    Object.entries(FILE_TYPE_MAP).map(([ext, info]) => (
                      <div key={ext} className="flex items-center gap-2 text-xs">
                        <info.icon className={`size-3 ${info.color}`} />
                        <span className="font-mono text-muted-foreground">{ext}</span>
                        <span className={`ml-auto ${info.color}`}>{info.label}</span>
                      </div>
                    ))
                  )}
                </CardContent>
              </CollapsibleContent>
            </Card>
          </Collapsible>
        </div>
      </div>
    </div>
  )
}

"use client"

import * as React from "react"
import {
  Clock,
  Activity,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Filter,
  Terminal,
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import { ScrollArea } from "@/components/ui/scroll-area"
import { mockJobs, type JobStatus } from "@/lib/mock-data"

const COLUMNS: { status: JobStatus; label: string; icon: React.ElementType; color: string; bg: string }[] = [
  { status: "queued", label: "Queued", icon: Clock, color: "text-muted-foreground", bg: "bg-muted/50" },
  { status: "running", label: "Running", icon: Activity, color: "text-forensic-cyan", bg: "bg-forensic-cyan/10" },
  { status: "normalizing", label: "Normalizing", icon: AlertTriangle, color: "text-forensic-amber", bg: "bg-forensic-amber/10" },
  { status: "done", label: "Done", icon: CheckCircle2, color: "text-forensic-green", bg: "bg-forensic-green/10" },
  { status: "failed", label: "Failed", icon: XCircle, color: "text-forensic-red", bg: "bg-forensic-red/10" },
]

function JobCard({ job }: { job: typeof mockJobs[number] }) {
  return (
    <Sheet>
      <SheetTrigger asChild>
        <Card className="border-border/30 bg-background/50 cursor-pointer hover:border-forensic-cyan/30 transition-colors">
          <CardContent className="p-3 flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="font-mono text-[10px] text-forensic-cyan">{job.id}</span>
              <Badge variant="outline" className="font-mono text-[9px] border-border/30">{job.tool}</Badge>
            </div>
            <p className="font-mono text-xs truncate">{job.evidenceFile}</p>
            <div className="flex items-center gap-2">
              <span className="font-mono text-[10px] text-muted-foreground">{job.caseId}</span>
            </div>
            {job.status === "running" || job.status === "normalizing" ? (
              <div className="flex items-center gap-2">
                <Progress value={job.progress} className="h-1 flex-1" />
                <span className="font-mono text-[10px] text-muted-foreground">{job.progress}%</span>
              </div>
            ) : null}
            <div className="flex items-center justify-between">
              <span className="font-mono text-[10px] text-muted-foreground">{job.duration}</span>
            </div>
          </CardContent>
        </Card>
      </SheetTrigger>
      <SheetContent className="bg-card border-border/50">
        <SheetHeader>
          <SheetTitle className="font-mono text-forensic-cyan">{job.id}</SheetTitle>
          <SheetDescription className="font-mono text-xs">
            {job.tool} - {job.evidenceFile}
          </SheetDescription>
        </SheetHeader>
        <div className="flex flex-col gap-4 mt-6">
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg border border-border/30 bg-background/50 p-3">
              <p className="text-[10px] font-mono text-muted-foreground uppercase">Status</p>
              <p className={`font-mono text-sm ${
                job.status === "done" ? "text-forensic-green" :
                job.status === "failed" ? "text-forensic-red" :
                job.status === "running" ? "text-forensic-cyan" :
                "text-muted-foreground"
              }`}>{job.status}</p>
            </div>
            <div className="rounded-lg border border-border/30 bg-background/50 p-3">
              <p className="text-[10px] font-mono text-muted-foreground uppercase">Duration</p>
              <p className="font-mono text-sm">{job.duration}</p>
            </div>
            <div className="rounded-lg border border-border/30 bg-background/50 p-3">
              <p className="text-[10px] font-mono text-muted-foreground uppercase">Case</p>
              <p className="font-mono text-sm text-forensic-cyan">{job.caseId}</p>
            </div>
            <div className="rounded-lg border border-border/30 bg-background/50 p-3">
              <p className="text-[10px] font-mono text-muted-foreground uppercase">Progress</p>
              <p className="font-mono text-sm">{job.progress}%</p>
            </div>
          </div>

          {/* Logs */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Terminal className="size-3 text-muted-foreground" />
              <span className="font-mono text-xs text-muted-foreground uppercase tracking-wider">Live Logs</span>
            </div>
            <ScrollArea className="h-[300px] rounded-lg border border-border/30 bg-background p-3">
              <pre className="font-mono text-[11px] leading-relaxed">
                {job.logs.length > 0 ? job.logs.join("\n") : "No logs available."}
              </pre>
            </ScrollArea>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}

export function JobsContent() {
  const [toolFilter, setToolFilter] = React.useState<string>("all")

  const tools = Array.from(new Set(mockJobs.map((j) => j.tool)))
  const filtered = toolFilter === "all" ? mockJobs : mockJobs.filter((j) => j.tool === toolFilter)

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold font-mono tracking-tight">Jobs Pipeline</h1>
          <p className="text-sm text-muted-foreground font-mono">{mockJobs.length} total jobs</p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={toolFilter} onValueChange={setToolFilter}>
            <SelectTrigger className="w-[160px] font-mono text-xs">
              <Filter className="mr-2 size-3" />
              <SelectValue placeholder="Filter by tool" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all" className="font-mono text-xs">All Tools</SelectItem>
              {tools.map((tool) => (
                <SelectItem key={tool} value={tool} className="font-mono text-xs">{tool}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Kanban Board */}
      <div className="grid grid-cols-5 gap-4">
        {COLUMNS.map((col) => {
          const columnJobs = filtered.filter((j) => j.status === col.status)
          return (
            <div key={col.status} className="flex flex-col gap-3">
              {/* Column Header */}
              <div className={`flex items-center gap-2 rounded-lg ${col.bg} px-3 py-2`}>
                <col.icon className={`size-4 ${col.color}`} />
                <span className="font-mono text-xs font-medium">{col.label}</span>
                <Badge variant="outline" className={`ml-auto font-mono text-[10px] border-border/30 ${col.color}`}>
                  {columnJobs.length}
                </Badge>
              </div>

              {/* Cards */}
              <div className="flex flex-col gap-2 min-h-[200px]">
                {columnJobs.map((job) => (
                  <JobCard key={job.id} job={job} />
                ))}
                {columnJobs.length === 0 && (
                  <div className="flex items-center justify-center rounded-lg border border-dashed border-border/30 p-8">
                    <span className="font-mono text-[10px] text-muted-foreground">No jobs</span>
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

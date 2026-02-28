"use client"

import * as React from "react"
import Link from "next/link"
import { ArrowLeft, FileText, Cpu, Activity, Search, Clock, BarChart3, Shield, Download, Play, Eye } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  mockCases,
  mockEvidence,
  mockJobs,
  mockFindings,
  mockTimelineEvents,
  mockAuditLog,
  type CaseStatus,
  type JobStatus,
  type FindingSeverity,
} from "@/lib/mock-data"

function StatusBadge({ status }: { status: CaseStatus }) {
  const config = {
    open: { label: "Open", className: "border-forensic-green/30 text-forensic-green bg-forensic-green/10" },
    closed: { label: "Closed", className: "border-forensic-cyan/30 text-forensic-cyan bg-forensic-cyan/10" },
    archived: { label: "Archived", className: "border-muted-foreground/30 text-muted-foreground bg-muted" },
  }
  const c = config[status]
  return <Badge variant="outline" className={`font-mono text-[10px] ${c.className}`}>{c.label}</Badge>
}

function JobStatusBadge({ status }: { status: JobStatus }) {
  const config: Record<JobStatus, { className: string }> = {
    queued: { className: "border-muted-foreground/30 text-muted-foreground" },
    running: { className: "border-forensic-cyan/30 text-forensic-cyan" },
    normalizing: { className: "border-forensic-amber/30 text-forensic-amber" },
    done: { className: "border-forensic-green/30 text-forensic-green" },
    failed: { className: "border-forensic-red/30 text-forensic-red" },
  }
  return <Badge variant="outline" className={`font-mono text-[10px] ${config[status].className}`}>{status}</Badge>
}

function SeverityBadge({ severity }: { severity: FindingSeverity }) {
  const config: Record<FindingSeverity, { className: string }> = {
    critical: { className: "border-forensic-red/30 text-forensic-red bg-forensic-red/10" },
    high: { className: "border-forensic-amber/30 text-forensic-amber bg-forensic-amber/10" },
    medium: { className: "border-forensic-cyan/30 text-forensic-cyan bg-forensic-cyan/10" },
    low: { className: "border-forensic-green/30 text-forensic-green bg-forensic-green/10" },
    info: { className: "border-muted-foreground/30 text-muted-foreground bg-muted" },
  }
  return <Badge variant="outline" className={`font-mono text-[10px] ${config[severity].className}`}>{severity}</Badge>
}

const sourceColors: Record<string, string> = {
  mobile: "bg-forensic-green",
  memory: "bg-forensic-cyan",
  disk: "bg-forensic-amber",
  network: "bg-forensic-red",
}

export function CaseDetailContent({ caseId }: { caseId: string }) {
  const caseData = mockCases.find((c) => c.id === caseId) || mockCases[0]
  const evidence = mockEvidence.filter((e) => e.caseId === caseData.id)
  const jobs = mockJobs.filter((j) => j.caseId === caseData.id)
  const findings = mockFindings.filter((f) => f.caseId === caseData.id)
  const timeline = mockTimelineEvents.filter((t) => t.caseId === caseData.id)

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <Button asChild variant="ghost" size="icon" className="shrink-0 mt-1">
          <Link href="/cases"><ArrowLeft className="size-4" /></Link>
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold font-mono tracking-tight">{caseData.name}</h1>
            <StatusBadge status={caseData.status} />
          </div>
          <div className="flex items-center gap-4 mt-1">
            <span className="font-mono text-xs text-forensic-cyan">{caseData.id}</span>
            <span className="text-xs text-muted-foreground">Analyst: {caseData.analyst}</span>
            <span className="text-xs text-muted-foreground">Created: {new Date(caseData.createdAt).toLocaleDateString()}</span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview" className="flex flex-col gap-4">
        <TabsList className="bg-muted/30 h-auto flex-wrap justify-start">
          <TabsTrigger value="overview" className="font-mono text-xs gap-1"><BarChart3 className="size-3" /> Overview</TabsTrigger>
          <TabsTrigger value="evidence" className="font-mono text-xs gap-1"><Cpu className="size-3" /> Evidence</TabsTrigger>
          <TabsTrigger value="analyses" className="font-mono text-xs gap-1"><Activity className="size-3" /> Analyses</TabsTrigger>
          <TabsTrigger value="findings" className="font-mono text-xs gap-1"><Search className="size-3" /> Findings</TabsTrigger>
          <TabsTrigger value="timeline" className="font-mono text-xs gap-1"><Clock className="size-3" /> Timeline</TabsTrigger>
          <TabsTrigger value="reports" className="font-mono text-xs gap-1"><FileText className="size-3" /> Reports</TabsTrigger>
          <TabsTrigger value="audit" className="font-mono text-xs gap-1"><Shield className="size-3" /> Audit Log</TabsTrigger>
        </TabsList>

        {/* Overview */}
        <TabsContent value="overview" className="flex flex-col gap-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
            <Card className="border-border/50 bg-card/50">
              <CardContent className="p-4 text-center">
                <p className="text-3xl font-bold font-mono text-forensic-cyan">{evidence.length}</p>
                <p className="text-xs font-mono text-muted-foreground uppercase tracking-wider mt-1">Evidence Files</p>
              </CardContent>
            </Card>
            <Card className="border-border/50 bg-card/50">
              <CardContent className="p-4 text-center">
                <p className="text-3xl font-bold font-mono text-forensic-green">{jobs.filter(j => j.status === "done").length}/{jobs.length}</p>
                <p className="text-xs font-mono text-muted-foreground uppercase tracking-wider mt-1">Jobs Complete</p>
              </CardContent>
            </Card>
            <Card className="border-border/50 bg-card/50">
              <CardContent className="p-4 text-center">
                <p className="text-3xl font-bold font-mono text-forensic-amber">{findings.length}</p>
                <p className="text-xs font-mono text-muted-foreground uppercase tracking-wider mt-1">Findings</p>
              </CardContent>
            </Card>
            <Card className="border-border/50 bg-card/50">
              <CardContent className="p-4 text-center">
                <p className="text-3xl font-bold font-mono text-forensic-red">{findings.filter(f => f.severity === "critical").length}</p>
                <p className="text-xs font-mono text-muted-foreground uppercase tracking-wider mt-1">Critical</p>
              </CardContent>
            </Card>
          </div>
          <Card className="border-border/50 bg-card/50">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-mono uppercase tracking-wider text-muted-foreground">Description</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm leading-relaxed">{caseData.description}</p>
              <div className="flex gap-2 mt-4">
                {caseData.tags.map((tag) => (
                  <Badge key={tag} variant="outline" className="font-mono text-[10px] border-forensic-cyan/20 text-forensic-cyan">
                    {tag}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Evidence */}
        <TabsContent value="evidence">
          <Card className="border-border/50 bg-card/50">
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow className="border-border/30 hover:bg-transparent">
                    <TableHead className="font-mono text-xs">Filename</TableHead>
                    <TableHead className="font-mono text-xs">Type</TableHead>
                    <TableHead className="font-mono text-xs">Size</TableHead>
                    <TableHead className="font-mono text-xs">Hash (MD5)</TableHead>
                    <TableHead className="font-mono text-xs">Status</TableHead>
                    <TableHead className="font-mono text-xs">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {evidence.map((ev) => (
                    <TableRow key={ev.id} className="border-border/20">
                      <TableCell className="font-mono text-sm">{ev.filename}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className="font-mono text-[10px] border-border/50">{ev.type.replace("_", " ")}</Badge>
                      </TableCell>
                      <TableCell className="font-mono text-sm text-muted-foreground">{ev.size}</TableCell>
                      <TableCell className="font-mono text-[10px] text-muted-foreground">{ev.hash.slice(0, 16)}...</TableCell>
                      <TableCell>
                        <Badge variant="outline" className={`font-mono text-[10px] ${
                          ev.analysisStatus === "complete" ? "border-forensic-green/30 text-forensic-green" :
                          ev.analysisStatus === "analyzing" ? "border-forensic-cyan/30 text-forensic-cyan" :
                          ev.analysisStatus === "failed" ? "border-forensic-red/30 text-forensic-red" :
                          "border-muted-foreground/30 text-muted-foreground"
                        }`}>{ev.analysisStatus}</Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button variant="ghost" size="icon" className="size-7"><Play className="size-3" /></Button>
                          <Button variant="ghost" size="icon" className="size-7"><Eye className="size-3" /></Button>
                          <Button variant="ghost" size="icon" className="size-7"><Download className="size-3" /></Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Analyses */}
        <TabsContent value="analyses">
          <Card className="border-border/50 bg-card/50">
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow className="border-border/30 hover:bg-transparent">
                    <TableHead className="font-mono text-xs">Job ID</TableHead>
                    <TableHead className="font-mono text-xs">Tool</TableHead>
                    <TableHead className="font-mono text-xs">Evidence</TableHead>
                    <TableHead className="font-mono text-xs">Status</TableHead>
                    <TableHead className="font-mono text-xs">Progress</TableHead>
                    <TableHead className="font-mono text-xs">Duration</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {jobs.map((job) => (
                    <TableRow key={job.id} className="border-border/20">
                      <TableCell className="font-mono text-sm text-forensic-cyan">{job.id}</TableCell>
                      <TableCell className="font-mono text-sm">{job.tool}</TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">{job.evidenceFile}</TableCell>
                      <TableCell><JobStatusBadge status={job.status} /></TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <div className="h-1.5 w-16 rounded-full bg-muted">
                            <div className={`h-full rounded-full ${
                              job.status === "done" ? "bg-forensic-green" :
                              job.status === "failed" ? "bg-forensic-red" :
                              "bg-forensic-cyan"
                            }`} style={{ width: `${job.progress}%` }} />
                          </div>
                          <span className="font-mono text-[10px] text-muted-foreground">{job.progress}%</span>
                        </div>
                      </TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">{job.duration}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Findings */}
        <TabsContent value="findings">
          <Card className="border-border/50 bg-card/50">
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow className="border-border/30 hover:bg-transparent">
                    <TableHead className="font-mono text-xs">Severity</TableHead>
                    <TableHead className="font-mono text-xs">Title</TableHead>
                    <TableHead className="font-mono text-xs">Type</TableHead>
                    <TableHead className="font-mono text-xs">Source</TableHead>
                    <TableHead className="font-mono text-xs">Tool</TableHead>
                    <TableHead className="font-mono text-xs">Timestamp</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {findings.map((f) => (
                    <TableRow key={f.id} className="border-border/20">
                      <TableCell><SeverityBadge severity={f.severity} /></TableCell>
                      <TableCell className="text-sm font-medium max-w-[300px] truncate">{f.title}</TableCell>
                      <TableCell><Badge variant="outline" className="font-mono text-[10px] border-border/50">{f.type}</Badge></TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1.5">
                          <div className={`size-2 rounded-full ${sourceColors[f.source] || "bg-muted-foreground"}`} />
                          <span className="text-xs font-mono">{f.source}</span>
                        </div>
                      </TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">{f.tool}</TableCell>
                      <TableCell className="font-mono text-[10px] text-muted-foreground">{new Date(f.timestamp).toLocaleString()}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Timeline */}
        <TabsContent value="timeline">
          <Card className="border-border/50 bg-card/50">
            <CardContent className="p-6">
              <div className="relative flex flex-col gap-0">
                {/* Line */}
                <div className="absolute left-[7px] top-3 bottom-3 w-px bg-border/50" />
                {timeline.map((event, i) => (
                  <div key={event.id} className="relative flex gap-4 pb-6 last:pb-0">
                    <div className={`relative z-10 mt-1 size-[15px] shrink-0 rounded-full border-2 border-background ${sourceColors[event.source] || "bg-muted-foreground"}`} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono text-[10px] text-muted-foreground">{new Date(event.timestamp).toLocaleString()}</span>
                        <Badge variant="outline" className="font-mono text-[9px] border-border/30">{event.source}</Badge>
                        <Badge variant="outline" className="font-mono text-[9px] border-border/30">{event.tool}</Badge>
                      </div>
                      <p className="text-sm mt-1">{event.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Reports */}
        <TabsContent value="reports">
          <Card className="border-border/50 bg-card/50">
            <CardContent className="flex flex-col items-center justify-center py-12">
              <FileText className="size-12 text-muted-foreground/30 mb-4" />
              <p className="text-sm text-muted-foreground font-mono">No reports generated yet for this case.</p>
              <Button className="mt-4 bg-forensic-cyan text-background hover:bg-forensic-cyan/90 font-mono gap-2">
                <FileText className="size-4" />
                Generate Report
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Audit Log */}
        <TabsContent value="audit">
          <Card className="border-border/50 bg-card/50">
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow className="border-border/30 hover:bg-transparent">
                    <TableHead className="font-mono text-xs">Timestamp</TableHead>
                    <TableHead className="font-mono text-xs">User</TableHead>
                    <TableHead className="font-mono text-xs">Action</TableHead>
                    <TableHead className="font-mono text-xs">Details</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {mockAuditLog.slice(0, 5).map((entry) => (
                    <TableRow key={entry.id} className="border-border/20">
                      <TableCell className="font-mono text-[10px] text-muted-foreground">{new Date(entry.timestamp).toLocaleString()}</TableCell>
                      <TableCell className="text-sm">{entry.user}</TableCell>
                      <TableCell><Badge variant="outline" className="font-mono text-[10px] border-border/50">{entry.action}</Badge></TableCell>
                      <TableCell className="text-xs text-muted-foreground max-w-[300px] truncate">{entry.details}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

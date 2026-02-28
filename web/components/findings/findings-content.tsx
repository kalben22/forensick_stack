"use client"

import * as React from "react"
import { Search, Filter, LayoutGrid, List } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { mockFindings, type FindingSeverity } from "@/lib/mock-data"

const sourceColors: Record<string, string> = {
  mobile: "bg-forensic-green",
  memory: "bg-forensic-cyan",
  disk: "bg-forensic-amber",
  network: "bg-forensic-red",
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

export function FindingsContent() {
  const [searchQuery, setSearchQuery] = React.useState("")
  const [severityFilter, setSeverityFilter] = React.useState<string>("all")
  const [sourceFilter, setSourceFilter] = React.useState<string>("all")
  const [viewMode, setViewMode] = React.useState<"grid" | "list">("list")

  const filtered = mockFindings.filter((f) => {
    const matchesSearch = f.title.toLowerCase().includes(searchQuery.toLowerCase()) || f.description.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesSeverity = severityFilter === "all" || f.severity === severityFilter
    const matchesSource = sourceFilter === "all" || f.source === sourceFilter
    return matchesSearch && matchesSeverity && matchesSource
  })

  const severityCounts = {
    critical: mockFindings.filter((f) => f.severity === "critical").length,
    high: mockFindings.filter((f) => f.severity === "high").length,
    medium: mockFindings.filter((f) => f.severity === "medium").length,
    low: mockFindings.filter((f) => f.severity === "low").length,
    info: mockFindings.filter((f) => f.severity === "info").length,
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold font-mono tracking-tight">Findings Explorer</h1>
          <p className="text-sm text-muted-foreground font-mono">{mockFindings.length} total findings across all cases</p>
        </div>
        <div className="flex items-center gap-1 rounded-lg border border-border/50 p-0.5">
          <Button
            variant={viewMode === "list" ? "secondary" : "ghost"}
            size="icon"
            className="size-7"
            onClick={() => setViewMode("list")}
          >
            <List className="size-3.5" />
          </Button>
          <Button
            variant={viewMode === "grid" ? "secondary" : "ghost"}
            size="icon"
            className="size-7"
            onClick={() => setViewMode("grid")}
          >
            <LayoutGrid className="size-3.5" />
          </Button>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-5 gap-3">
        {Object.entries(severityCounts).map(([sev, count]) => (
          <Card key={sev} className="border-border/50 bg-card/50">
            <CardContent className="flex items-center justify-between p-3">
              <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">{sev}</span>
              <span className={`font-mono text-lg font-bold ${
                sev === "critical" ? "text-forensic-red" :
                sev === "high" ? "text-forensic-amber" :
                sev === "medium" ? "text-forensic-cyan" :
                sev === "low" ? "text-forensic-green" :
                "text-muted-foreground"
              }`}>{count}</span>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Filters */}
      <Card className="border-border/50 bg-card/50">
        <CardContent className="flex flex-wrap items-center gap-3 p-4">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <Input
              placeholder="Search findings..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 font-mono text-sm bg-background/50"
            />
          </div>
          <Select value={severityFilter} onValueChange={setSeverityFilter}>
            <SelectTrigger className="w-[140px] font-mono text-xs">
              <SelectValue placeholder="Severity" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all" className="font-mono text-xs">All Severity</SelectItem>
              <SelectItem value="critical" className="font-mono text-xs">Critical</SelectItem>
              <SelectItem value="high" className="font-mono text-xs">High</SelectItem>
              <SelectItem value="medium" className="font-mono text-xs">Medium</SelectItem>
              <SelectItem value="low" className="font-mono text-xs">Low</SelectItem>
              <SelectItem value="info" className="font-mono text-xs">Info</SelectItem>
            </SelectContent>
          </Select>
          <Select value={sourceFilter} onValueChange={setSourceFilter}>
            <SelectTrigger className="w-[140px] font-mono text-xs">
              <SelectValue placeholder="Source" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all" className="font-mono text-xs">All Sources</SelectItem>
              <SelectItem value="memory" className="font-mono text-xs">Memory</SelectItem>
              <SelectItem value="disk" className="font-mono text-xs">Disk</SelectItem>
              <SelectItem value="mobile" className="font-mono text-xs">Mobile</SelectItem>
              <SelectItem value="network" className="font-mono text-xs">Network</SelectItem>
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {/* Results */}
      {viewMode === "list" ? (
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
                  <TableHead className="font-mono text-xs">Case</TableHead>
                  <TableHead className="font-mono text-xs">Timestamp</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((f) => (
                  <TableRow key={f.id} className="border-border/20 cursor-pointer hover:bg-forensic-cyan/5">
                    <TableCell><SeverityBadge severity={f.severity} /></TableCell>
                    <TableCell className="text-sm font-medium max-w-[250px] truncate">{f.title}</TableCell>
                    <TableCell><Badge variant="outline" className="font-mono text-[10px] border-border/50">{f.type}</Badge></TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1.5">
                        <div className={`size-2 rounded-full ${sourceColors[f.source] || "bg-muted-foreground"}`} />
                        <span className="text-xs font-mono">{f.source}</span>
                      </div>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">{f.tool}</TableCell>
                    <TableCell className="font-mono text-xs text-forensic-cyan">{f.caseId}</TableCell>
                    <TableCell className="font-mono text-[10px] text-muted-foreground">{new Date(f.timestamp).toLocaleString()}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map((f) => (
            <Card key={f.id} className="border-border/50 bg-card/50 cursor-pointer hover:border-forensic-cyan/30 transition-colors">
              <CardContent className="p-4 flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <SeverityBadge severity={f.severity} />
                  <div className="flex items-center gap-1.5">
                    <div className={`size-2 rounded-full ${sourceColors[f.source] || "bg-muted-foreground"}`} />
                    <span className="text-[10px] font-mono text-muted-foreground">{f.source}</span>
                  </div>
                </div>
                <h3 className="text-sm font-medium leading-tight">{f.title}</h3>
                <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">{f.description}</p>
                <div className="rounded-md bg-background/80 p-2 border border-border/20">
                  <pre className="font-mono text-[10px] text-muted-foreground truncate">{f.rawData}</pre>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex gap-1">
                    <Badge variant="outline" className="font-mono text-[9px] border-border/30">{f.tool}</Badge>
                    <Badge variant="outline" className="font-mono text-[9px] border-border/30">{f.type}</Badge>
                  </div>
                  <span className="font-mono text-[10px] text-forensic-cyan">{f.caseId}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

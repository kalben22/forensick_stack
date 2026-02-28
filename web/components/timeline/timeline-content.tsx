"use client"

import * as React from "react"
import { Filter, ZoomIn, ZoomOut } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { mockTimelineEvents } from "@/lib/mock-data"

const sourceConfig: Record<string, { color: string; bg: string; label: string }> = {
  mobile: { color: "bg-forensic-green", bg: "bg-forensic-green/10", label: "Mobile" },
  memory: { color: "bg-forensic-cyan", bg: "bg-forensic-cyan/10", label: "Memory" },
  disk: { color: "bg-forensic-amber", bg: "bg-forensic-amber/10", label: "Disk" },
  network: { color: "bg-forensic-red", bg: "bg-forensic-red/10", label: "Network" },
}

export function TimelineContent() {
  const [sourceFilter, setSourceFilter] = React.useState<string>("all")
  const [caseFilter, setCaseFilter] = React.useState<string>("all")

  const cases = Array.from(new Set(mockTimelineEvents.map((e) => e.caseId)))

  const filtered = mockTimelineEvents
    .filter((e) => {
      const matchesSource = sourceFilter === "all" || e.source === sourceFilter
      const matchesCase = caseFilter === "all" || e.caseId === caseFilter
      return matchesSource && matchesCase
    })
    .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold font-mono tracking-tight">Timeline</h1>
          <p className="text-sm text-muted-foreground font-mono">{mockTimelineEvents.length} events across all cases</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" className="size-8 border-border/50">
            <ZoomOut className="size-3.5" />
          </Button>
          <Button variant="outline" size="icon" className="size-8 border-border/50">
            <ZoomIn className="size-3.5" />
          </Button>
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-4">
        {Object.entries(sourceConfig).map(([key, conf]) => (
          <div key={key} className="flex items-center gap-2">
            <div className={`size-3 rounded-full ${conf.color}`} />
            <span className="font-mono text-xs text-muted-foreground">{conf.label}</span>
          </div>
        ))}
      </div>

      {/* Filters */}
      <Card className="border-border/50 bg-card/50">
        <CardContent className="flex flex-wrap items-center gap-3 p-4">
          <Select value={sourceFilter} onValueChange={setSourceFilter}>
            <SelectTrigger className="w-[140px] font-mono text-xs">
              <Filter className="mr-2 size-3" />
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
          <Select value={caseFilter} onValueChange={setCaseFilter}>
            <SelectTrigger className="w-[180px] font-mono text-xs">
              <SelectValue placeholder="Case" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all" className="font-mono text-xs">All Cases</SelectItem>
              {cases.map((c) => (
                <SelectItem key={c} value={c} className="font-mono text-xs">{c}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Badge variant="outline" className="font-mono text-[10px] border-border/50 ml-auto">
            {filtered.length} events
          </Badge>
        </CardContent>
      </Card>

      {/* Timeline */}
      <Card className="border-border/50 bg-card/50">
        <CardContent className="p-6">
          <div className="relative flex flex-col gap-0">
            {/* Vertical line */}
            <div className="absolute left-[11px] top-3 bottom-3 w-px bg-border/30" />

            {filtered.map((event, i) => {
              const conf = sourceConfig[event.source] || { color: "bg-muted-foreground", bg: "bg-muted", label: event.source }
              return (
                <div key={event.id} className="group relative flex gap-5 pb-8 last:pb-0">
                  {/* Dot */}
                  <div className={`relative z-10 mt-1.5 size-[23px] shrink-0 rounded-full border-[3px] border-card ${conf.color}`} />

                  {/* Content */}
                  <div className="flex-1 min-w-0 rounded-lg border border-border/20 bg-background/50 p-4 group-hover:border-border/40 transition-colors">
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs text-muted-foreground">
                          {new Date(event.timestamp).toLocaleString()}
                        </span>
                        <Badge variant="outline" className={`font-mono text-[9px] ${conf.bg} border-transparent`}>
                          {conf.label}
                        </Badge>
                        <Badge variant="outline" className="font-mono text-[9px] border-border/30">
                          {event.tool}
                        </Badge>
                      </div>
                      <Badge variant="outline" className="font-mono text-[9px] border-border/30 text-forensic-cyan">
                        {event.caseId}
                      </Badge>
                    </div>
                    <p className="text-sm mt-2 leading-relaxed">{event.description}</p>
                    <Badge variant="outline" className="font-mono text-[9px] border-border/20 mt-2">
                      {event.eventType}
                    </Badge>
                  </div>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

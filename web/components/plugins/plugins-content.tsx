"use client"

import * as React from "react"
import {
  Search,
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Settings2,
  Download,
  Trash2,
  Plus,
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { mockPlugins, type PluginStatus, type EvidenceType } from "@/lib/mock-data"

function StatusIcon({ status }: { status: PluginStatus }) {
  if (status === "active") return <CheckCircle2 className="size-4 text-forensic-green" />
  if (status === "error") return <XCircle className="size-4 text-forensic-red" />
  return <AlertTriangle className="size-4 text-forensic-amber" />
}

function ResourceBadge({ profile }: { profile: "low" | "medium" | "high" }) {
  const config = {
    low: "border-forensic-green/30 text-forensic-green",
    medium: "border-forensic-amber/30 text-forensic-amber",
    high: "border-forensic-red/30 text-forensic-red",
  }
  return <Badge variant="outline" className={`font-mono text-[10px] ${config[profile]}`}>{profile}</Badge>
}

const typeLabels: Record<EvidenceType, string> = {
  memory_dump: "Memory",
  disk_image: "Disk",
  mobile_backup: "Mobile",
  pcap: "PCAP",
  evtx: "EVTX",
  registry: "Registry",
  unknown: "Unknown",
}

export function PluginsContent() {
  const [searchQuery, setSearchQuery] = React.useState("")

  const filtered = mockPlugins.filter((p) =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.description.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const statusCounts = {
    active: mockPlugins.filter((p) => p.status === "active").length,
    inactive: mockPlugins.filter((p) => p.status === "inactive").length,
    error: mockPlugins.filter((p) => p.status === "error").length,
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold font-mono tracking-tight">Plugin Registry</h1>
          <p className="text-sm text-muted-foreground font-mono">{mockPlugins.length} plugins installed</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" className="font-mono text-xs gap-2 border-border/50">
            <RefreshCw className="size-3" /> Refresh
          </Button>
          <Button className="bg-primary text-primary-foreground font-mono text-xs gap-2">
            <Plus className="size-3" /> Add Plugin
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="border-border/50 bg-card/50">
          <CardContent className="flex items-center justify-between p-4">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="size-4 text-forensic-green" />
              <span className="font-mono text-xs text-muted-foreground">Active</span>
            </div>
            <span className="text-xl font-bold font-mono text-forensic-green">{statusCounts.active}</span>
          </CardContent>
        </Card>
        <Card className="border-border/50 bg-card/50">
          <CardContent className="flex items-center justify-between p-4">
            <div className="flex items-center gap-2">
              <AlertTriangle className="size-4 text-forensic-amber" />
              <span className="font-mono text-xs text-muted-foreground">Inactive</span>
            </div>
            <span className="text-xl font-bold font-mono text-forensic-amber">{statusCounts.inactive}</span>
          </CardContent>
        </Card>
        <Card className="border-border/50 bg-card/50">
          <CardContent className="flex items-center justify-between p-4">
            <div className="flex items-center gap-2">
              <XCircle className="size-4 text-forensic-red" />
              <span className="font-mono text-xs text-muted-foreground">Error</span>
            </div>
            <span className="text-xl font-bold font-mono text-forensic-red">{statusCounts.error}</span>
          </CardContent>
        </Card>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
        <Input
          placeholder="Search plugins..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-9 font-mono text-sm bg-card/50"
        />
      </div>

      {/* Plugins Table */}
      <Card className="border-border/50 bg-card/50">
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="border-border/30 hover:bg-transparent">
                <TableHead className="font-mono text-xs">Status</TableHead>
                <TableHead className="font-mono text-xs">Plugin</TableHead>
                <TableHead className="font-mono text-xs">Version</TableHead>
                <TableHead className="font-mono text-xs">Docker Image</TableHead>
                <TableHead className="font-mono text-xs">Supported Types</TableHead>
                <TableHead className="font-mono text-xs">Resources</TableHead>
                <TableHead className="font-mono text-xs">Updated</TableHead>
                <TableHead className="font-mono text-xs">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((plugin) => (
                <TableRow key={plugin.id} className="border-border/20">
                  <TableCell><StatusIcon status={plugin.status} /></TableCell>
                  <TableCell>
                    <div>
                      <p className="font-mono text-sm font-semibold">{plugin.name}</p>
                      <p className="text-xs text-muted-foreground line-clamp-1 max-w-[200px]">{plugin.description}</p>
                    </div>
                  </TableCell>
                  <TableCell className="font-mono text-xs">{plugin.version}</TableCell>
                  <TableCell className="font-mono text-[10px] text-primary max-w-[180px] truncate">{plugin.dockerImage}</TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {plugin.supportedTypes.map((t) => (
                        <Badge key={t} variant="outline" className="font-mono text-[9px] border-border/30">{typeLabels[t]}</Badge>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell><ResourceBadge profile={plugin.resourceProfile} /></TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">{plugin.lastUpdated}</TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button variant="ghost" size="icon" className="size-7"><Settings2 className="size-3" /></Button>
                      <Button variant="ghost" size="icon" className="size-7"><Download className="size-3" /></Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}

"use client"

import * as React from "react"
import {
  Upload,
  Zap,
  Flag,
  Search,
  Binary,
  BarChart3,
  FileText,
  Hash,
  Clock,
  ChevronRight,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"

const CTF_TOOLS = [
  { name: "Find Flag", icon: Flag, description: "Search for CTF flag patterns in artifacts", color: "text-forensic-amber" },
  { name: "IOC Highlighter", icon: AlertTriangle, description: "Highlight indicators of compromise", color: "text-forensic-red" },
  { name: "Regex Search", icon: Search, description: "Search with custom regex patterns", color: "text-forensic-cyan" },
  { name: "Entropy Scanner", icon: BarChart3, description: "Detect high-entropy regions (encryption/packing)", color: "text-forensic-violet" },
  { name: "File Signatures", icon: FileText, description: "Detect file types by magic bytes", color: "text-forensic-green" },
  { name: "Strings Extractor", icon: Binary, description: "Extract readable strings from binary data", color: "text-forensic-cyan" },
]

const MOCK_RESULTS = [
  { type: "flag_candidate", value: "FLAG{m3m0ry_f0r3ns1cs_r0ck5}", confidence: "high", source: "strings", timestamp: "12:34:56" },
  { type: "suspicious_ip", value: "185.234.72.15", confidence: "medium", source: "netscan", timestamp: "12:34:58" },
  { type: "encoded_string", value: "aHR0cHM6Ly9ldmlsLmNvbS9wYXlsb2Fk", confidence: "high", source: "strings", timestamp: "12:35:01" },
  { type: "process", value: "svchost.exe (PID 4592) - Injected", confidence: "critical", source: "pslist", timestamp: "12:35:03" },
  { type: "hash", value: "e99a18c428cb38d5f260853678922e03", confidence: "medium", source: "hashdump", timestamp: "12:35:05" },
]

const MOCK_HISTORY = [
  { id: 1, file: "challenge_memdump.raw", tool: "Volatility3", findings: 5, duration: "3m 12s", date: "Nov 18, 2024" },
  { id: 2, file: "network_capture.pcap", tool: "Bulk Extractor", findings: 3, duration: "1m 45s", date: "Nov 17, 2024" },
  { id: 3, file: "firmware.bin", tool: "Strings + Entropy", findings: 8, duration: "0m 34s", date: "Nov 16, 2024" },
]

export function CtfContent() {
  const [hasFile, setHasFile] = React.useState(false)
  const [analyzing, setAnalyzing] = React.useState(false)
  const [showResults, setShowResults] = React.useState(false)

  const handleAnalyze = () => {
    setAnalyzing(true)
    setTimeout(() => {
      setAnalyzing(false)
      setShowResults(true)
    }, 1500)
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold font-mono tracking-tight">CTF Workspace</h1>
          <p className="text-sm text-muted-foreground font-mono">Quick analysis mode for CTF competitions</p>
        </div>
        <Badge variant="outline" className="border-forensic-amber/30 text-forensic-amber font-mono text-xs">
          CTF MODE
        </Badge>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Main Area */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          {/* Quick Upload */}
          <Card
            className={`border-2 border-dashed cursor-pointer transition-colors ${
              hasFile
                ? "border-forensic-green/50 bg-forensic-green/5"
                : "border-forensic-amber/30 bg-card/50 hover:border-forensic-amber/50"
            }`}
            onClick={() => setHasFile(true)}
          >
            <CardContent className="flex items-center gap-4 p-6">
              {hasFile ? (
                <>
                  <div className="flex size-12 items-center justify-center rounded-lg bg-forensic-green/20">
                    <CheckCircle2 className="size-6 text-forensic-green" />
                  </div>
                  <div className="flex-1">
                    <p className="font-mono font-semibold">challenge_memdump.raw</p>
                    <p className="text-xs text-muted-foreground font-mono">4.2 GB - Memory Dump - Volatility3 suggested</p>
                  </div>
                  <Button
                    onClick={(e) => { e.stopPropagation(); handleAnalyze() }}
                    disabled={analyzing}
                    className="bg-forensic-amber text-background hover:bg-forensic-amber/90 font-mono gap-2"
                  >
                    <Zap className="size-4" />
                    {analyzing ? "Analyzing..." : "Quick Analyze"}
                  </Button>
                </>
              ) : (
                <>
                  <div className="flex size-12 items-center justify-center rounded-lg bg-forensic-amber/20">
                    <Upload className="size-6 text-forensic-amber" />
                  </div>
                  <div className="flex-1">
                    <p className="font-medium">Drop file here for quick analysis</p>
                    <p className="text-xs text-muted-foreground">Supports all forensic formats - Auto-detect enabled</p>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {/* Results */}
          {showResults && (
            <Card className="border-border/50 bg-card/50">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-mono uppercase tracking-wider text-muted-foreground">Artifacts Found</CardTitle>
                  <Badge variant="outline" className="font-mono text-[10px] border-forensic-green/30 text-forensic-green">
                    {MOCK_RESULTS.length} results
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="flex flex-col gap-2">
                {MOCK_RESULTS.map((result, i) => (
                  <div key={i} className="flex items-start gap-3 rounded-lg border border-border/30 bg-background/50 p-3">
                    <div className={`mt-0.5 size-2 shrink-0 rounded-full ${
                      result.confidence === "critical" ? "bg-forensic-red" :
                      result.confidence === "high" ? "bg-forensic-amber" :
                      "bg-forensic-cyan"
                    }`} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="font-mono text-[9px] border-border/30">{result.type}</Badge>
                        <Badge variant="outline" className="font-mono text-[9px] border-border/30">{result.source}</Badge>
                      </div>
                      <p className="font-mono text-sm mt-1 break-all text-forensic-cyan">{result.value}</p>
                    </div>
                    <span className="font-mono text-[10px] text-muted-foreground shrink-0">{result.timestamp}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* History */}
          <Card className="border-border/50 bg-card/50">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-mono uppercase tracking-wider text-muted-foreground">Recent Sessions</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              {MOCK_HISTORY.map((session) => (
                <div key={session.id} className="flex items-center gap-3 rounded-lg border border-border/30 bg-background/50 p-3 cursor-pointer hover:border-forensic-amber/30">
                  <Clock className="size-4 text-muted-foreground shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="font-mono text-sm truncate">{session.file}</p>
                    <p className="text-xs text-muted-foreground">{session.tool} - {session.findings} findings - {session.duration}</p>
                  </div>
                  <span className="font-mono text-[10px] text-muted-foreground shrink-0">{session.date}</span>
                  <ChevronRight className="size-3 text-muted-foreground shrink-0" />
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* CTF Tools */}
        <div className="flex flex-col gap-4">
          <Card className="border-border/50 bg-card/50">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-mono uppercase tracking-wider text-muted-foreground">CTF Tools</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              {CTF_TOOLS.map((tool) => (
                <Button
                  key={tool.name}
                  variant="outline"
                  className="justify-start h-auto py-3 border-border/30 hover:border-forensic-amber/30"
                >
                  <tool.icon className={`size-4 mr-3 shrink-0 ${tool.color}`} />
                  <div className="text-left">
                    <p className="text-sm font-mono">{tool.name}</p>
                    <p className="text-[10px] text-muted-foreground font-normal">{tool.description}</p>
                  </div>
                </Button>
              ))}
            </CardContent>
          </Card>

          {/* Quick Regex */}
          <Card className="border-border/50 bg-card/50">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-mono uppercase tracking-wider text-muted-foreground">Quick Search</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <Input placeholder="Enter regex pattern..." className="font-mono text-xs bg-background/50" />
              <div className="flex flex-wrap gap-1">
                {["FLAG\\{.*\\}", "\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}", "[A-Fa-f0-9]{32}", "password|secret|key"].map((pattern) => (
                  <Badge key={pattern} variant="outline" className="font-mono text-[9px] border-border/30 cursor-pointer hover:border-forensic-amber/30">
                    {pattern.length > 20 ? pattern.slice(0, 20) + "..." : pattern}
                  </Badge>
                ))}
              </div>
              <Button variant="outline" className="font-mono text-xs border-forensic-amber/30 text-forensic-amber hover:bg-forensic-amber/10">
                <Search className="size-3 mr-2" />
                Search
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

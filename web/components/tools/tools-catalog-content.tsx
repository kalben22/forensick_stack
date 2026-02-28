"use client"

import * as React from "react"
import {
  Search,
  Play,
  FileText,
  Terminal,
  Cpu,
  Smartphone,
  HardDrive,
  Network,
  BookOpen,
  ChevronRight,
  Copy,
  ExternalLink,
  Info,
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"

interface ToolDoc {
  id: string
  name: string
  version: string
  category: "memory" | "mobile" | "disk" | "metadata" | "network" | "timeline"
  description: string
  longDescription: string
  icon: React.ElementType
  color: string
  supportedInputs: string[]
  usageExamples: { command: string; description: string }[]
  flags: { flag: string; description: string }[]
  limitations: string[]
  outputFormats: string[]
  dockerImage: string
  sampleFile: string
}

const TOOLS: ToolDoc[] = [
  {
    id: "exiftool",
    name: "ExifTool",
    version: "12.97",
    category: "metadata",
    description: "Read, write and edit meta information in a wide variety of files.",
    longDescription: "ExifTool is a platform-independent Perl library plus a command-line application for reading, writing and editing meta information in a wide variety of files. ExifTool supports many different metadata formats including EXIF, GPS, IPTC, XMP, JFIF, GeoTIFF, ICC Profile, Photoshop IRB, FlashPix, AFCP and ID3, as well as the maker notes of many digital cameras.",
    icon: FileText,
    color: "text-forensic-green",
    supportedInputs: [".jpg", ".png", ".pdf", ".docx", ".mp4", ".heic", ".raw", ".tiff"],
    usageExamples: [
      { command: "exiftool image.jpg", description: "Display all metadata of an image" },
      { command: "exiftool -gps* image.jpg", description: "Show only GPS metadata" },
      { command: "exiftool -r -ext jpg /path/to/dir", description: "Recursively process all .jpg files" },
      { command: "exiftool -json image.jpg > meta.json", description: "Export metadata as JSON" },
      { command: "exiftool -AllDates image.jpg", description: "Show all date/time tags" },
    ],
    flags: [
      { flag: "-r", description: "Recursively process subdirectories" },
      { flag: "-json", description: "Output in JSON format" },
      { flag: "-csv", description: "Output in CSV format" },
      { flag: "-ext EXT", description: "Process only files with specified extension" },
      { flag: "-gps*", description: "Show only GPS-related tags" },
      { flag: "-AllDates", description: "Show all date/time tags" },
      { flag: "-a", description: "Allow duplicate tags to be extracted" },
      { flag: "-s", description: "Short output format (tag names instead of descriptions)" },
    ],
    limitations: ["Cannot extract metadata from encrypted files", "Memory usage scales with file size", "Some proprietary formats have limited support"],
    outputFormats: ["text", "json", "csv", "xml", "html"],
    dockerImage: "forensicflow/exiftool:12.97",
    sampleFile: "sample_image.jpg",
  },
  {
    id: "ileapp",
    name: "iLEAPP",
    version: "1.18.6",
    category: "mobile",
    description: "iOS Logs Events And Properties Parser - comprehensive iOS device analysis.",
    longDescription: "iLEAPP (iOS Logs Events And Properties Parser) is an open-source tool that parses iOS device backups, full file system extractions, and iTunes backups. It processes hundreds of artifact types including SMS/iMessage, call logs, location data, browser history, app data, and more. Results are presented as both HTML reports and TSV files.",
    icon: Smartphone,
    color: "text-forensic-cyan",
    supportedInputs: [".tar.gz", ".zip", "iTunes backup dir", "full filesystem extraction"],
    usageExamples: [
      { command: "python ileapp.py -t tar -i backup.tar.gz -o output/", description: "Process a tar.gz iOS backup" },
      { command: "python ileapp.py -t zip -i backup.zip -o output/", description: "Process a zipped backup" },
      { command: "python ileapp.py -t fs -i /path/to/extraction -o output/", description: "Process a filesystem extraction" },
      { command: "python ileapp.py -t itunes -i /path/to/backup -o output/", description: "Process an iTunes backup" },
    ],
    flags: [
      { flag: "-t TYPE", description: "Input type: tar, zip, fs, itunes, gz" },
      { flag: "-i INPUT", description: "Path to input file or directory" },
      { flag: "-o OUTPUT", description: "Path to output directory" },
      { flag: "-p", description: "Generate PDF report" },
      { flag: "--artifact", description: "Process only specified artifact(s)" },
    ],
    limitations: ["Requires Python 3.9+", "Large backups may take 30+ minutes", "Some artifacts require full filesystem extraction", "Does not decrypt encrypted backups"],
    outputFormats: ["html", "tsv", "pdf", "timeline"],
    dockerImage: "forensicflow/ileapp:1.18.6",
    sampleFile: "sample_ios_backup.tar.gz",
  },
  {
    id: "aleapp",
    name: "ALEAPP",
    version: "3.1.9",
    category: "mobile",
    description: "Android Logs Events And Properties Parser for Android device forensics.",
    longDescription: "ALEAPP (Android Logs Events And Properties Parser) is a comprehensive Android forensic artifact parser. It supports Android backups (.ab), tar archives, and full filesystem extractions. ALEAPP parses SMS, call logs, browser history, Wi-Fi connections, installed apps, user accounts, and hundreds of other Android-specific artifacts.",
    icon: Smartphone,
    color: "text-forensic-green",
    supportedInputs: [".ab", ".tar", ".zip", "filesystem extraction"],
    usageExamples: [
      { command: "python aleapp.py -t tar -i backup.tar -o output/", description: "Process a tar Android backup" },
      { command: "python aleapp.py -t ab -i backup.ab -o output/", description: "Process an .ab backup file" },
      { command: "python aleapp.py -t zip -i extraction.zip -o output/", description: "Process a zipped extraction" },
    ],
    flags: [
      { flag: "-t TYPE", description: "Input type: tar, ab, zip, fs" },
      { flag: "-i INPUT", description: "Path to input file or directory" },
      { flag: "-o OUTPUT", description: "Path to output directory" },
      { flag: "-p", description: "Generate PDF report" },
      { flag: "--artifact", description: "Process only specified artifact(s)" },
    ],
    limitations: ["Requires Python 3.9+", "Cannot decrypt encrypted .ab files without password", "App-specific parsers may lag behind app updates"],
    outputFormats: ["html", "tsv", "pdf", "timeline"],
    dockerImage: "forensicflow/aleapp:3.1.9",
    sampleFile: "sample_android_backup.ab",
  },
  {
    id: "volatility3",
    name: "Volatility 3",
    version: "2.5.2",
    category: "memory",
    description: "Advanced memory forensics framework for RAM analysis and malware detection.",
    longDescription: "Volatility 3 is the world's most widely used framework for extracting digital artifacts from volatile memory (RAM) samples. It supports analysis of Windows, Linux, and macOS memory dumps. Key capabilities include process listing, network connections, registry extraction, malware detection, rootkit identification, and code injection analysis.",
    icon: Cpu,
    color: "text-forensic-amber",
    supportedInputs: [".raw", ".vmem", ".dmp", ".lime", "EWF (.E01)"],
    usageExamples: [
      { command: "vol -f memdump.raw windows.pslist", description: "List running processes" },
      { command: "vol -f memdump.raw windows.netscan", description: "Scan for network connections" },
      { command: "vol -f memdump.raw windows.malfind", description: "Find injected/suspicious code" },
      { command: "vol -f memdump.raw windows.cmdline", description: "Show process command lines" },
      { command: "vol -f memdump.raw windows.dlllist --pid 4592", description: "List DLLs for a specific process" },
      { command: "vol -f memdump.raw windows.hashdump", description: "Extract password hashes" },
    ],
    flags: [
      { flag: "-f FILE", description: "Path to memory dump file" },
      { flag: "-o OFFSET", description: "Physical offset for DTB" },
      { flag: "--pid PID", description: "Filter by process ID" },
      { flag: "-r json", description: "Output in JSON format" },
      { flag: "--dump", description: "Dump associated data to files" },
      { flag: "-p PATH", description: "Additional plugin path" },
    ],
    limitations: ["Requires correct symbol tables/ISF files", "Large dumps (32GB+) need significant RAM", "Some plugins are OS-specific", "Profile auto-detection may fail on unusual dumps"],
    outputFormats: ["text", "json", "csv"],
    dockerImage: "forensicflow/volatility3:2.5.2",
    sampleFile: "sample_memdump.raw",
  },
]

const categoryConfig: Record<string, { label: string; color: string; icon: React.ElementType }> = {
  memory: { label: "Memory", color: "text-forensic-amber", icon: Cpu },
  mobile: { label: "Mobile", color: "text-forensic-cyan", icon: Smartphone },
  disk: { label: "Disk", color: "text-forensic-green", icon: HardDrive },
  metadata: { label: "Metadata", color: "text-forensic-green", icon: FileText },
  network: { label: "Network", color: "text-forensic-red", icon: Network },
  timeline: { label: "Timeline", color: "text-forensic-violet", icon: Terminal },
}

function ToolDetailPanel({ tool }: { tool: ToolDoc }) {
  const [copiedIdx, setCopiedIdx] = React.useState<number | null>(null)
  const catConf = categoryConfig[tool.category]

  const handleCopy = (text: string, idx: number) => {
    navigator.clipboard.writeText(text)
    setCopiedIdx(idx)
    setTimeout(() => setCopiedIdx(null), 1500)
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <div className={`flex size-14 items-center justify-center rounded-xl bg-current/10 ${tool.color}`}>
          <tool.icon className={`size-7 ${tool.color}`} />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold font-mono tracking-tight">{tool.name}</h2>
            <Badge variant="outline" className="font-mono text-[10px] border-border/50">v{tool.version}</Badge>
            <Badge variant="outline" className={`font-mono text-[10px] ${catConf.color} border-current/20`}>
              {catConf.label}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-1 leading-relaxed">{tool.longDescription}</p>
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex gap-2">
        <Button className="bg-primary text-primary-foreground font-mono gap-2">
          <Play className="size-4" />
          Run in Sandbox
        </Button>
        <Button variant="outline" className="font-mono gap-2 border-border/50">
          <FileText className="size-4" />
          Try Sample
        </Button>
      </div>

      <Tabs defaultValue="usage" className="flex flex-col gap-3">
        <TabsList className="bg-muted/30 h-auto justify-start">
          <TabsTrigger value="usage" className="font-mono text-xs gap-1"><Terminal className="size-3" /> Usage</TabsTrigger>
          <TabsTrigger value="flags" className="font-mono text-xs gap-1"><Info className="size-3" /> Flags</TabsTrigger>
          <TabsTrigger value="examples" className="font-mono text-xs gap-1"><BookOpen className="size-3" /> Examples</TabsTrigger>
        </TabsList>

        <TabsContent value="usage" className="flex flex-col gap-4">
          {/* Supported Inputs */}
          <Card className="border-border/50 bg-card/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-xs font-mono uppercase tracking-wider text-muted-foreground">Supported Input Formats</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              {tool.supportedInputs.map((input) => (
                <Badge key={input} variant="outline" className="font-mono text-[11px] border-border/50">{input}</Badge>
              ))}
            </CardContent>
          </Card>

          {/* Output Formats */}
          <Card className="border-border/50 bg-card/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-xs font-mono uppercase tracking-wider text-muted-foreground">Output Formats</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              {tool.outputFormats.map((fmt) => (
                <Badge key={fmt} variant="outline" className={`font-mono text-[11px] border-primary/20 ${tool.color}`}>{fmt}</Badge>
              ))}
            </CardContent>
          </Card>

          {/* Limitations */}
          <Card className="border-border/50 bg-card/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-xs font-mono uppercase tracking-wider text-muted-foreground">Limitations</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-1.5">
              {tool.limitations.map((lim, i) => (
                <p key={i} className="text-xs text-muted-foreground flex items-start gap-2">
                  <span className="text-forensic-amber mt-0.5">*</span>
                  {lim}
                </p>
              ))}
            </CardContent>
          </Card>

          {/* Docker */}
          <Card className="border-border/50 bg-card/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-xs font-mono uppercase tracking-wider text-muted-foreground">Docker Image</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2 rounded-md bg-background/80 border border-border/30 px-3 py-2">
                <code className="font-mono text-xs text-primary flex-1">{tool.dockerImage}</code>
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-6 shrink-0"
                  onClick={() => handleCopy(tool.dockerImage, -1)}
                >
                  <Copy className="size-3" />
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="flags">
          <Card className="border-border/50 bg-card/50">
            <CardContent className="p-0">
              <div className="flex flex-col">
                {tool.flags.map((f, i) => (
                  <div key={i} className={`flex items-start gap-4 px-4 py-3 ${i < tool.flags.length - 1 ? "border-b border-border/20" : ""}`}>
                    <code className={`font-mono text-sm font-semibold shrink-0 min-w-[120px] ${tool.color}`}>{f.flag}</code>
                    <p className="text-sm text-muted-foreground">{f.description}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="examples" className="flex flex-col gap-3">
          {tool.usageExamples.map((ex, i) => (
            <Card key={i} className="border-border/50 bg-card/50">
              <CardContent className="p-4 flex flex-col gap-2">
                <p className="text-xs text-muted-foreground">{ex.description}</p>
                <div className="flex items-center gap-2 rounded-md bg-background/80 border border-border/30 px-3 py-2">
                  <code className="font-mono text-xs text-primary flex-1 break-all">{ex.command}</code>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-6 shrink-0"
                    onClick={() => handleCopy(ex.command, i)}
                  >
                    {copiedIdx === i ? (
                      <span className="text-forensic-green text-[10px] font-mono">ok</span>
                    ) : (
                      <Copy className="size-3" />
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </TabsContent>
      </Tabs>
    </div>
  )
}

export function ToolsCatalogContent() {
  const [searchQuery, setSearchQuery] = React.useState("")
  const [selectedTool, setSelectedTool] = React.useState<ToolDoc>(TOOLS[0])

  const filtered = TOOLS.filter((t) =>
    t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    t.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
    t.category.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-bold font-mono tracking-tight">Tools Catalog</h1>
        <p className="text-sm text-muted-foreground font-mono">Documentation, usage and sandbox for forensic tools</p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Tool List (left) */}
        <div className="lg:col-span-4 flex flex-col gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <Input
              placeholder="Search tools..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 font-mono text-sm bg-card/50"
            />
          </div>

          <ScrollArea className="h-[calc(100vh-240px)]">
            <div className="flex flex-col gap-2 pr-3">
              {filtered.map((tool) => {
                const catConf = categoryConfig[tool.category]
                const isSelected = selectedTool.id === tool.id
                return (
                  <Card
                    key={tool.id}
                    className={`cursor-pointer transition-colors ${
                      isSelected
                        ? "border-primary/40 bg-primary/5"
                        : "border-border/50 bg-card/50 hover:border-border"
                    }`}
                    onClick={() => setSelectedTool(tool)}
                  >
                    <CardContent className="p-4 flex items-start gap-3">
                      <div className={`flex size-10 items-center justify-center rounded-lg bg-current/10 shrink-0 ${tool.color}`}>
                        <tool.icon className={`size-5 ${tool.color}`} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-sm font-semibold">{tool.name}</span>
                          <Badge variant="outline" className="font-mono text-[9px] border-border/30">v{tool.version}</Badge>
                        </div>
                        <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{tool.description}</p>
                        <Badge variant="outline" className={`font-mono text-[9px] mt-2 border-current/20 ${catConf.color}`}>
                          {catConf.label}
                        </Badge>
                      </div>
                      <ChevronRight className={`size-4 shrink-0 mt-1 ${isSelected ? "text-primary" : "text-muted-foreground/30"}`} />
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          </ScrollArea>
        </div>

        {/* Tool Detail (right) */}
        <div className="lg:col-span-8">
          <Card className="border-border/50 bg-card/50">
            <CardContent className="p-6">
              <ToolDetailPanel tool={selectedTool} />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

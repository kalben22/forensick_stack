'use client'

import { useState } from 'react'
import {
  FileText,
  Download,
  Plus,
  Clock,
  CheckCircle2,
  Loader2,
  Eye,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { useCases } from '@/lib/hooks/use-cases'
import { mockReports } from '@/lib/mock-data'
import { formatBytes, formatDateTime } from '@/lib/utils'

const FORMAT_COLORS: Record<string, string> = {
  pdf: 'bg-red-500/10 text-red-400 border-red-500/30',
  html: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
  json: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
  stix: 'bg-violet-500/10 text-violet-400 border-violet-500/30',
  csv: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
}

export function ReportsContent() {
  const { data: casesData } = useCases({ limit: 100 })
  const [generating, setGenerating] = useState(false)
  const [selectedCase, setSelectedCase] = useState('')
  const [selectedFormat, setSelectedFormat] = useState('')
  const [dialogOpen, setDialogOpen] = useState(false)

  const handleGenerate = async () => {
    if (!selectedCase || !selectedFormat) return
    setGenerating(true)
    // Backend report generation coming in Phase 2
    await new Promise((r) => setTimeout(r, 1500))
    setGenerating(false)
    setDialogOpen(false)
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Reports</h1>
          <p className="text-sm text-muted-foreground">
            Generate and download investigation reports
          </p>
        </div>

        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Generate Report
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Generate Report</DialogTitle>
              <DialogDescription>
                Export case findings in your preferred format.
              </DialogDescription>
            </DialogHeader>

            <div className="grid gap-4 py-4">
              <div className="space-y-1.5">
                <Label>Case</Label>
                <Select value={selectedCase} onValueChange={setSelectedCase}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a case…" />
                  </SelectTrigger>
                  <SelectContent>
                    {casesData?.cases.map((c) => (
                      <SelectItem key={c.id} value={String(c.id)}>
                        {c.case_number} — {c.title}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <Label>Format</Label>
                <Select value={selectedFormat} onValueChange={setSelectedFormat}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select format…" />
                  </SelectTrigger>
                  <SelectContent>
                    {['PDF', 'HTML', 'JSON', 'STIX', 'CSV'].map((f) => (
                      <SelectItem key={f} value={f}>
                        {f}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <DialogFooter>
              <Button
                onClick={handleGenerate}
                disabled={!selectedCase || !selectedFormat || generating}
              >
                {generating ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Generating…
                  </>
                ) : (
                  'Generate'
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          { label: 'Total Reports', value: mockReports.length },
          { label: 'PDF', value: mockReports.filter((r) => r.format === 'pdf').length },
          { label: 'JSON / CSV', value: mockReports.filter((r) => ['json', 'csv'].includes(r.format)).length },
          { label: 'This Month', value: mockReports.length },
        ].map(({ label, value }) => (
          <Card key={label}>
            <CardHeader className="flex flex-row items-center justify-between pb-2 pt-4">
              <CardTitle className="text-xs font-medium text-muted-foreground">{label}</CardTitle>
              <FileText className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent className="pb-4">
              <p className="text-2xl font-bold">{value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Reports list */}
      <div className="grid gap-3">
        {mockReports.length === 0 ? (
          <Card className="py-16">
            <CardContent className="flex flex-col items-center gap-2 text-center">
              <FileText className="h-10 w-10 text-muted-foreground/40" />
              <p className="font-medium">No reports yet</p>
              <p className="text-sm text-muted-foreground">
                Generate your first report from the button above.
              </p>
            </CardContent>
          </Card>
        ) : (
          mockReports.map((report) => (
            <Card key={report.id} className="group transition-colors hover:bg-accent/30">
              <CardContent className="flex items-center justify-between py-4">
                <div className="flex items-center gap-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
                    <FileText className="h-5 w-5 text-muted-foreground" />
                  </div>
                  <div>
                    <p className="font-medium text-sm">{report.caseName} — {report.template}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <Badge
                        variant="outline"
                        className={`text-xs ${FORMAT_COLORS[report.format] ?? ''}`}
                      >
                        {report.format.toUpperCase()}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {report.size}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  <div className="hidden text-right sm:block">
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                      {report.status === 'ready' ? (
                        <CheckCircle2 className="h-3 w-3 text-emerald-500" />
                      ) : (
                        <Clock className="h-3 w-3 text-amber-500" />
                      )}
                      {report.status}
                    </div>
                    <p className="text-xs text-muted-foreground">{formatDateTime(report.generatedAt)}</p>
                  </div>
                  <div className="flex gap-1">
                    <Button variant="ghost" size="icon" className="h-8 w-8">
                      <Eye className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8">
                      <Download className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      <p className="text-center text-xs text-muted-foreground">
        Report generation backend (PDF/STIX export) coming in Phase 2.
      </p>
    </div>
  )
}

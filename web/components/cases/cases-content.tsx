"use client"

import * as React from "react"
import Link from "next/link"
import { Plus, Search, Filter, RefreshCw, AlertCircle } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { useCases, useCreateCase } from "@/lib/hooks/use-cases"
import { mockCases, type CaseStatus } from "@/lib/mock-data"
import { useToast } from "@/components/ui/use-toast"
import type { CaseResponse } from "@/lib/api/cases"

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { label: string; className: string }> = {
    open: { label: "Open", className: "border-forensic-green/30 text-forensic-green bg-forensic-green/10" },
    closed: { label: "Closed", className: "border-forensic-cyan/30 text-forensic-cyan bg-forensic-cyan/10" },
    archived: { label: "Archived", className: "border-muted-foreground/30 text-muted-foreground bg-muted" },
    in_progress: { label: "In Progress", className: "border-forensic-amber/30 text-forensic-amber bg-forensic-amber/10" },
  }
  const c = config[status] ?? { label: status, className: "text-muted-foreground" }
  return <Badge variant="outline" className={`font-mono text-[10px] ${c.className}`}>{c.label}</Badge>
}

function SkeletonRow() {
  return (
    <TableRow className="border-border/20">
      {Array.from({ length: 6 }).map((_, i) => (
        <TableCell key={i}><Skeleton className="h-4 w-full rounded" /></TableCell>
      ))}
    </TableRow>
  )
}

function CreateCaseDialog({ onCreated }: { onCreated?: () => void }) {
  const [open, setOpen] = React.useState(false)
  const [title, setTitle] = React.useState("")
  const [description, setDescription] = React.useState("")
  const createCase = useCreateCase()
  const { toast } = useToast()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return
    try {
      await createCase.mutateAsync({ title: title.trim(), description: description.trim() || undefined })
      toast({ title: "Case created", description: `"${title}" has been created.` })
      setOpen(false)
      setTitle("")
      setDescription("")
      onCreated?.()
    } catch {
      toast({ title: "Error", description: "Failed to create case.", variant: "destructive" })
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="bg-forensic-cyan text-background hover:bg-forensic-cyan/90 font-mono gap-2">
          <Plus className="size-4" />
          New Case
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Create New Case</DialogTitle>
            <DialogDescription>Add a new forensic investigation case to the platform.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-1.5">
              <Label htmlFor="case-title">Title *</Label>
              <Input
                id="case-title"
                placeholder="e.g. Corporate Espionage Investigation"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                disabled={createCase.isPending}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="case-desc">Description</Label>
              <Textarea
                id="case-desc"
                placeholder="Brief description of the case…"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                disabled={createCase.isPending}
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" disabled={!title.trim() || createCase.isPending}>
              {createCase.isPending ? "Creating…" : "Create Case"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export function CasesContent() {
  const [searchQuery, setSearchQuery] = React.useState("")
  const [statusFilter, setStatusFilter] = React.useState<string>("all")
  const [debouncedSearch, setDebouncedSearch] = React.useState("")

  // Debounce search 300ms
  React.useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(searchQuery), 300)
    return () => clearTimeout(t)
  }, [searchQuery])

  const { data, isLoading, isError, refetch } = useCases({
    limit: 100,
    status: statusFilter !== "all" ? statusFilter : undefined,
  })

  // When API works use real data, otherwise fall back to mock
  const apiCases: CaseResponse[] = data?.cases ?? []
  const usingApi = !isError && !isLoading

  // Filter: apply search on whatever source we're using
  const apiFiltered = apiCases.filter((c) =>
    debouncedSearch === "" ||
    c.title.toLowerCase().includes(debouncedSearch.toLowerCase()) ||
    c.case_number.toLowerCase().includes(debouncedSearch.toLowerCase())
  )

  // Mock fallback (client-side filtering)
  const mockFiltered = mockCases.filter((c) => {
    const matchesSearch =
      c.name.toLowerCase().includes(debouncedSearch.toLowerCase()) ||
      c.id.toLowerCase().includes(debouncedSearch.toLowerCase())
    const matchesStatus = statusFilter === "all" || c.status === statusFilter
    return matchesSearch && matchesStatus
  })

  const totalCount = usingApi ? (data?.total ?? 0) : mockCases.length

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold font-mono tracking-tight">Cases</h1>
          <p className="text-sm text-muted-foreground font-mono">
            {isLoading ? "Loading…" : `${totalCount} total cases`}
            {isError && <span className="text-forensic-amber ml-2">(showing local data)</span>}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" onClick={() => refetch()} title="Refresh">
            <RefreshCw className="size-4" />
          </Button>
          <CreateCaseDialog />
        </div>
      </div>

      {/* Filters */}
      <Card className="border-border/50 bg-card/50">
        <CardContent className="flex flex-wrap items-center gap-3 p-4">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <Input
              placeholder="Search cases…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 font-mono text-sm bg-background/50"
            />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[160px] font-mono text-xs">
              <Filter className="mr-2 size-3" />
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all" className="font-mono text-xs">All Status</SelectItem>
              <SelectItem value="open" className="font-mono text-xs">Open</SelectItem>
              <SelectItem value="closed" className="font-mono text-xs">Closed</SelectItem>
              <SelectItem value="archived" className="font-mono text-xs">Archived</SelectItem>
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {/* Error banner */}
      {isError && (
        <div className="flex items-center gap-2 rounded-lg border border-forensic-amber/30 bg-forensic-amber/10 px-4 py-2 text-sm text-forensic-amber">
          <AlertCircle className="size-4 shrink-0" />
          Backend unreachable — displaying local demo data.
        </div>
      )}

      {/* Cases Table */}
      <Card className="border-border/50 bg-card/50">
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="border-border/30 hover:bg-transparent">
                <TableHead className="font-mono text-xs uppercase tracking-wider">ID</TableHead>
                <TableHead className="font-mono text-xs uppercase tracking-wider">Title</TableHead>
                <TableHead className="font-mono text-xs uppercase tracking-wider">Status</TableHead>
                <TableHead className="font-mono text-xs uppercase tracking-wider">Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} />)
              ) : usingApi ? (
                apiFiltered.length > 0 ? (
                  apiFiltered.map((c) => (
                    <TableRow key={c.id} className="border-border/20 cursor-pointer hover:bg-forensic-cyan/5">
                      <TableCell>
                        <Link href={`/cases/${c.id}`} className="font-mono text-sm text-forensic-cyan hover:underline">
                          {c.case_number}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <Link href={`/cases/${c.id}`} className="text-sm font-medium hover:text-forensic-cyan">
                          {c.title}
                        </Link>
                        {c.description && (
                          <p className="text-xs text-muted-foreground mt-0.5 truncate max-w-xs">{c.description}</p>
                        )}
                      </TableCell>
                      <TableCell><StatusBadge status={c.status} /></TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {new Date(c.created_at).toLocaleDateString()}
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={4} className="py-16 text-center text-muted-foreground">
                      <p className="font-medium">No cases yet</p>
                      <p className="text-sm mt-1">Create your first case using the button above.</p>
                    </TableCell>
                  </TableRow>
                )
              ) : (
                // Mock fallback (7 columns to match original mock table)
                mockFiltered.map((c) => (
                  <TableRow key={c.id} className="border-border/20 cursor-pointer hover:bg-forensic-cyan/5">
                    <TableCell>
                      <Link href={`/cases/${c.id}`} className="font-mono text-sm text-forensic-cyan hover:underline">
                        {c.id}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <Link href={`/cases/${c.id}`} className="text-sm font-medium hover:text-forensic-cyan">
                        {c.name}
                      </Link>
                      <div className="flex gap-1 mt-1">
                        {c.tags.slice(0, 3).map((tag) => (
                          <Badge key={tag} variant="outline" className="font-mono text-[9px] border-border/30 text-muted-foreground">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell><StatusBadge status={c.status} /></TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {new Date(c.createdAt).toLocaleDateString()}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}

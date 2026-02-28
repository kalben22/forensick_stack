"use client"

import {
  FolderOpen,
  Activity,
  Search,
  HardDrive,
  ArrowUpRight,
  ArrowDownRight,
  Upload,
  Plus,
  Flag,
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
} from "lucide-react"
import Link from "next/link"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Skeleton } from "@/components/ui/skeleton"
import {
  mockCases,
  mockJobs,
  mockFindings,
  mockRecentActivity,
  mockSystemServices,
} from "@/lib/mock-data"
import { useCases } from "@/lib/hooks/use-cases"

const jobStatusCounts = {
  queued: mockJobs.filter((j) => j.status === "queued").length,
  running: mockJobs.filter((j) => j.status === "running").length,
  normalizing: mockJobs.filter((j) => j.status === "normalizing").length,
  done: mockJobs.filter((j) => j.status === "done").length,
  failed: mockJobs.filter((j) => j.status === "failed").length,
}

export function DashboardContent() {
  const { data: casesData, isLoading: casesLoading } = useCases({ limit: 100 })

  // Live counts from API, fall back to mock when backend is unreachable
  const activeCasesCount = casesData
    ? casesData.cases.filter((c) => c.status === "open").length
    : mockCases.filter((c) => c.status === "open").length

  const totalCasesCount = casesData?.total ?? mockCases.length

  const stats = [
    {
      title: "Active Cases",
      value: casesLoading ? null : activeCasesCount,
      trend: `${totalCasesCount} total`,
      trendUp: true,
      icon: FolderOpen,
      color: "text-forensic-cyan",
      bgColor: "bg-forensic-cyan/10",
    },
    {
      title: "Running Jobs",
      value: mockJobs.filter((j) => j.status === "running").length,
      trend: `${jobStatusCounts.queued} queued`,
      trendUp: true,
      icon: Activity,
      color: "text-forensic-green",
      bgColor: "bg-forensic-green/10",
    },
    {
      title: "Total Findings",
      value: mockFindings.length,
      trend: "+12",
      trendUp: true,
      icon: Search,
      color: "text-forensic-amber",
      bgColor: "bg-forensic-amber/10",
    },
    {
      title: "Storage Used",
      value: "~154 GB",
      trend: "MinIO",
      trendUp: false,
      icon: HardDrive,
      color: "text-forensic-violet",
      bgColor: "bg-forensic-violet/10",
    },
  ]

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold font-mono tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted-foreground font-mono">ForensicFlow DFIR Platform Overview</p>
        </div>
        <Badge variant="outline" className="border-forensic-cyan/30 text-forensic-cyan font-mono text-xs">
          PRO MODE
        </Badge>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.title} className="border-border/50 bg-card/50">
            <CardContent className="flex items-center gap-4 p-4">
              <div className={`flex size-10 shrink-0 items-center justify-center rounded-lg ${stat.bgColor}`}>
                <stat.icon className={`size-5 ${stat.color}`} />
              </div>
              <div className="flex-1">
                <p className="text-xs text-muted-foreground font-mono uppercase tracking-wider">{stat.title}</p>
                <div className="flex items-baseline gap-2">
                  {stat.value === null ? (
                    <Skeleton className="h-8 w-10 rounded" />
                  ) : (
                    <span className="text-2xl font-bold font-mono">{stat.value}</span>
                  )}
                  <span className={`flex items-center text-xs font-mono ${stat.trendUp ? "text-forensic-green" : "text-muted-foreground"}`}>
                    {stat.trendUp ? <ArrowUpRight className="size-3" /> : <ArrowDownRight className="size-3" />}
                    {stat.trend}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Recent Activity */}
        <Card className="border-border/50 bg-card/50 lg:col-span-2">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-mono uppercase tracking-wider text-muted-foreground">Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col gap-3">
              {mockRecentActivity.map((activity) => (
                <div key={activity.id} className="flex items-center gap-3 rounded-lg border border-border/30 bg-background/50 p-3">
                  <div className={`size-2 shrink-0 rounded-full ${
                    activity.type === "success" ? "bg-forensic-green" :
                    activity.type === "error" ? "bg-forensic-red" :
                    activity.type === "warning" ? "bg-forensic-amber" :
                    "bg-forensic-cyan"
                  }`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{activity.action}</p>
                    <p className="text-xs text-muted-foreground font-mono truncate">{activity.detail}</p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-xs text-muted-foreground">{activity.user}</p>
                    <p className="text-[10px] text-muted-foreground/60 font-mono">{activity.time}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Quick Actions + System Status */}
        <div className="flex flex-col gap-6">
          {/* Quick Actions */}
          <Card className="border-border/50 bg-card/50">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-mono uppercase tracking-wider text-muted-foreground">Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              <Button asChild className="justify-start bg-forensic-cyan/10 text-forensic-cyan hover:bg-forensic-cyan/20 border border-forensic-cyan/20">
                <Link href="/upload">
                  <Upload className="mr-2 size-4" />
                  New Upload
                </Link>
              </Button>
              <Button asChild variant="outline" className="justify-start border-border/50">
                <Link href="/cases">
                  <Plus className="mr-2 size-4" />
                  Create Case
                </Link>
              </Button>
              <Button asChild variant="outline" className="justify-start border-border/50">
                <Link href="/ctf">
                  <Flag className="mr-2 size-4" />
                  Start CTF
                </Link>
              </Button>
            </CardContent>
          </Card>

          {/* System Status */}
          <Card className="border-border/50 bg-card/50">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-mono uppercase tracking-wider text-muted-foreground">System Status</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              {mockSystemServices.map((service) => (
                <div key={service.name} className="flex items-center justify-between rounded-md border border-border/30 bg-background/50 px-3 py-2">
                  <div className="flex items-center gap-2">
                    {service.status === "running" ? (
                      <CheckCircle2 className="size-3 text-forensic-green" />
                    ) : service.status === "error" ? (
                      <XCircle className="size-3 text-forensic-red" />
                    ) : (
                      <AlertTriangle className="size-3 text-forensic-amber" />
                    )}
                    <span className="text-xs font-mono">{service.name}</span>
                  </div>
                  <span className="text-[10px] text-muted-foreground font-mono">v{service.version}</span>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Jobs Overview */}
      <Card className="border-border/50 bg-card/50">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-mono uppercase tracking-wider text-muted-foreground">Jobs Pipeline</CardTitle>
            <Button asChild variant="ghost" size="sm" className="text-xs font-mono text-forensic-cyan">
              <Link href="/jobs">View All</Link>
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-5 gap-3">
            {Object.entries(jobStatusCounts).map(([status, count]) => (
              <div key={status} className="flex flex-col items-center gap-2 rounded-lg border border-border/30 bg-background/50 p-4">
                <div className={`flex size-8 items-center justify-center rounded-full ${
                  status === "queued" ? "bg-muted" :
                  status === "running" ? "bg-forensic-cyan/20" :
                  status === "normalizing" ? "bg-forensic-amber/20" :
                  status === "done" ? "bg-forensic-green/20" :
                  "bg-forensic-red/20"
                }`}>
                  {status === "queued" && <Clock className="size-4 text-muted-foreground" />}
                  {status === "running" && <Activity className="size-4 text-forensic-cyan" />}
                  {status === "normalizing" && <AlertTriangle className="size-4 text-forensic-amber" />}
                  {status === "done" && <CheckCircle2 className="size-4 text-forensic-green" />}
                  {status === "failed" && <XCircle className="size-4 text-forensic-red" />}
                </div>
                <span className="text-2xl font-bold font-mono">{count}</span>
                <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">{status}</span>
              </div>
            ))}
          </div>
          <div className="mt-4">
            <div className="flex items-center justify-between text-xs text-muted-foreground font-mono mb-1">
              <span>Pipeline Progress</span>
              <span>{Math.round((jobStatusCounts.done / mockJobs.length) * 100)}% Complete</span>
            </div>
            <Progress value={Math.round((jobStatusCounts.done / mockJobs.length) * 100)} className="h-1.5" />
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

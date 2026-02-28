'use client'

import * as React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  Shield,
  LayoutDashboard,
  Activity,
  Search,
  Clock,
  HardDrive,
  FileText,
  Settings,
  ChevronDown,
  Wifi,
  LogOut,
  User,
  Brain,
  FileSearch,
  Smartphone,
  Cpu,
} from 'lucide-react'
import { useLogout } from '@/lib/hooks/use-auth'
import { useAuthStore } from '@/lib/stores/auth-store'
import { useListTools } from '@/lib/hooks/use-jobs'
import { Skeleton } from '@/components/ui/skeleton'

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from '@/components/ui/sidebar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import type { AppMode } from '@/lib/mock-data'

// ── Icon per category ─────────────────────────────────────────────────────────

const CATEGORY_ICON: Record<string, React.ElementType> = {
  memory:         Brain,
  metadata:       FileSearch,
  mobile_ios:     Smartphone,
  mobile_android: Smartphone,
  disk:           HardDrive,
}

const CATEGORY_COLOR: Record<string, string> = {
  memory:         'text-forensic-cyan',
  metadata:       'text-forensic-amber',
  mobile_ios:     'text-forensic-green',
  mobile_android: 'text-emerald-400',
}

const TOOL_LABEL: Record<string, string> = {
  volatility: 'Volatility 3',
  exiftool:   'ExifTool',
  ileapp:     'iLEAPP',
  aleapp:     'aLEAPP',
}

// ── Secondary nav ─────────────────────────────────────────────────────────────

const NAV_ANALYSIS = [
  { title: 'Jobs',     href: '/jobs',     icon: Activity },
  { title: 'Findings', href: '/findings', icon: Search },
  { title: 'Timeline', href: '/timeline', icon: Clock },
]

const NAV_SYSTEM = [
  { title: 'Storage', href: '/storage', icon: HardDrive },
  { title: 'Reports', href: '/reports', icon: FileText },
]

const NAV_ADMIN = [
  { title: 'Admin', href: '/admin', icon: Settings },
]

// ── Component ─────────────────────────────────────────────────────────────────

export function AppSidebar() {
  const pathname = usePathname()
  const [mode, setMode] = React.useState<AppMode>('pro')
  const logout = useLogout()
  const user = useAuthStore((s) => s.user)

  const { data: toolsData, isLoading: toolsLoading } = useListTools()
  const tools = toolsData?.tools ?? []

  return (
    <Sidebar collapsible="icon">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <Link href="/">
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-forensic-cyan text-background">
                  <Shield className="size-4" />
                </div>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-semibold font-mono tracking-tight">ForensicStack</span>
                  <span className="truncate text-xs text-muted-foreground">DFIR Platform</span>
                </div>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <SidebarMenuButton className="font-mono text-xs">
                  <div className={`size-2 rounded-full ${mode === 'pro' ? 'bg-forensic-cyan' : 'bg-forensic-amber'}`} />
                  <span>{mode === 'pro' ? 'PRO Mode' : 'CTF Mode'}</span>
                  <ChevronDown className="ml-auto size-3" />
                </SidebarMenuButton>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="w-48">
                <DropdownMenuItem onClick={() => setMode('pro')} className="font-mono text-xs">
                  <div className="size-2 rounded-full bg-forensic-cyan" />
                  PRO Mode — Full DFIR
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setMode('ctf')} className="font-mono text-xs">
                  <div className="size-2 rounded-full bg-forensic-amber" />
                  CTF Mode — Quick Analysis
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>

        {/* ── Dashboard link ──────────────────────────────────────────────── */}
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton asChild isActive={pathname === '/'} tooltip="Dashboard">
                  <Link href="/">
                    <LayoutDashboard />
                    <span>Dashboard</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* ── Tools ──────────────────────────────────────────────────────── */}
        <SidebarGroup>
          <SidebarGroupLabel className="font-mono text-[10px] uppercase tracking-widest">
            Tools
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {toolsLoading && (
                <>
                  {[1, 2, 3, 4].map((i) => (
                    <SidebarMenuItem key={i}>
                      <SidebarMenuButton disabled>
                        <Skeleton className="size-4 rounded" />
                        <Skeleton className="h-3 w-20 rounded" />
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  ))}
                </>
              )}
              {tools.map((tool) => {
                const Icon = CATEGORY_ICON[tool.category] ?? Cpu
                const color = CATEGORY_COLOR[tool.category] ?? 'text-muted-foreground'
                const label = TOOL_LABEL[tool.name] ?? tool.name
                const href = `/tools/${tool.name}`
                const isActive = pathname.startsWith(href)

                return (
                  <SidebarMenuItem key={tool.name}>
                    <SidebarMenuButton asChild isActive={isActive} tooltip={label}>
                      <Link href={href}>
                        <Icon className={isActive ? '' : color} />
                        <span>{label}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                )
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* ── Analysis ───────────────────────────────────────────────────── */}
        <SidebarGroup>
          <SidebarGroupLabel className="font-mono text-[10px] uppercase tracking-widest">
            Analysis
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {NAV_ANALYSIS.map((item) => (
                <SidebarMenuItem key={item.href}>
                  <SidebarMenuButton asChild isActive={pathname === item.href} tooltip={item.title}>
                    <Link href={item.href}>
                      <item.icon />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* ── System ─────────────────────────────────────────────────────── */}
        <SidebarGroup>
          <SidebarGroupLabel className="font-mono text-[10px] uppercase tracking-widest">
            System
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {NAV_SYSTEM.map((item) => (
                <SidebarMenuItem key={item.href}>
                  <SidebarMenuButton asChild isActive={pathname === item.href} tooltip={item.title}>
                    <Link href={item.href}>
                      <item.icon />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* ── Admin ──────────────────────────────────────────────────────── */}
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {NAV_ADMIN.map((item) => (
                <SidebarMenuItem key={item.href}>
                  <SidebarMenuButton asChild isActive={pathname === item.href} tooltip={item.title}>
                    <Link href={item.href}>
                      <item.icon />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

      </SidebarContent>

      {/* ── Footer ─────────────────────────────────────────────────────────── */}
      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton className="font-mono text-[10px]" tooltip="System status">
              <Wifi className="size-3 text-forensic-green" />
              <span className="text-forensic-green">All Systems Operational</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
          <SidebarMenuItem>
            <SidebarMenuButton
              onClick={logout}
              tooltip="Sign out"
              className="font-mono text-[10px] text-muted-foreground hover:text-destructive hover:bg-destructive/10"
            >
              <User className="size-3" />
              <span className="flex-1 truncate">{user?.username ?? 'User'}</span>
              <LogOut className="size-3 ml-auto" />
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>

      <SidebarRail />
    </Sidebar>
  )
}

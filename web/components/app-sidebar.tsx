"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  Shield,
  LayoutDashboard,
  Upload,
  FolderOpen,
  Flag,
  Activity,
  Search,
  Clock,
  Puzzle,
  HardDrive,
  FileText,
  Settings,
  ChevronDown,
  Wifi,
  BookOpen,
  LogOut,
  User,
} from "lucide-react"
import { useLogout } from "@/lib/hooks/use-auth"
import { useAuthStore } from "@/lib/stores/auth-store"

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import type { AppMode } from "@/lib/mock-data"

const NAV_ITEMS_COMMON = [
  { title: "Dashboard", href: "/", icon: LayoutDashboard },
  { title: "Upload & Analyze", href: "/upload", icon: Upload },
  { title: "Tools Catalog", href: "/tools", icon: BookOpen },
]

const NAV_ITEMS_PRO = [
  { title: "Cases", href: "/cases", icon: FolderOpen },
]

const NAV_ITEMS_CTF = [
  { title: "CTF Workspace", href: "/ctf", icon: Flag },
]

const NAV_ITEMS_ANALYSIS = [
  { title: "Jobs", href: "/jobs", icon: Activity, badge: 4 },
  { title: "Findings", href: "/findings", icon: Search },
  { title: "Timeline", href: "/timeline", icon: Clock },
]

const NAV_ITEMS_INFRA = [
  { title: "Plugins", href: "/plugins", icon: Puzzle },
  { title: "Storage", href: "/storage", icon: HardDrive },
  { title: "Reports", href: "/reports", icon: FileText },
]

const NAV_ITEMS_ADMIN = [
  { title: "Admin", href: "/admin", icon: Settings },
]

export function AppSidebar() {
  const pathname = usePathname()
  const [mode, setMode] = React.useState<AppMode>("pro")
  const logout = useLogout()
  const user = useAuthStore((s) => s.user)

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <Link href="/">
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-forensic-cyan text-background">
                  <Shield className="size-4" />
                </div>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-semibold font-mono tracking-tight">ForensicFlow</span>
                  <span className="truncate text-xs text-muted-foreground">DFIR Platform</span>
                </div>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <SidebarMenuButton className="font-mono text-xs">
                  <div className={`size-2 rounded-full ${mode === "pro" ? "bg-forensic-cyan" : "bg-forensic-amber"}`} />
                  <span>{mode === "pro" ? "PRO Mode" : "CTF Mode"}</span>
                  <ChevronDown className="ml-auto size-3" />
                </SidebarMenuButton>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="w-48">
                <DropdownMenuItem onClick={() => setMode("pro")} className="font-mono text-xs">
                  <div className="size-2 rounded-full bg-forensic-cyan" />
                  PRO Mode - Full DFIR
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setMode("ctf")} className="font-mono text-xs">
                  <div className="size-2 rounded-full bg-forensic-amber" />
                  CTF Mode - Quick Analysis
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        {/* Main Navigation */}
        <SidebarGroup>
          <SidebarGroupLabel className="font-mono text-[10px] uppercase tracking-widest">Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {NAV_ITEMS_COMMON.map((item) => (
                <SidebarMenuItem key={item.href}>
                  <SidebarMenuButton asChild isActive={pathname === item.href} tooltip={item.title}>
                    <Link href={item.href}>
                      <item.icon />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
              {mode === "pro" && NAV_ITEMS_PRO.map((item) => (
                <SidebarMenuItem key={item.href}>
                  <SidebarMenuButton asChild isActive={pathname.startsWith(item.href)} tooltip={item.title}>
                    <Link href={item.href}>
                      <item.icon />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
              {NAV_ITEMS_CTF.map((item) => (
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

        {/* Analysis */}
        <SidebarGroup>
          <SidebarGroupLabel className="font-mono text-[10px] uppercase tracking-widest">Analysis</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {NAV_ITEMS_ANALYSIS.map((item) => (
                <SidebarMenuItem key={item.href}>
                  <SidebarMenuButton asChild isActive={pathname === item.href} tooltip={item.title}>
                    <Link href={item.href}>
                      <item.icon />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                  {item.badge && (
                    <SidebarMenuBadge className="bg-forensic-cyan/20 text-forensic-cyan text-[10px] font-mono">
                      {item.badge}
                    </SidebarMenuBadge>
                  )}
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Infrastructure */}
        <SidebarGroup>
          <SidebarGroupLabel className="font-mono text-[10px] uppercase tracking-widest">Infrastructure</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {NAV_ITEMS_INFRA.map((item) => (
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

        {/* Admin */}
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {NAV_ITEMS_ADMIN.map((item) => (
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

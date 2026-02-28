"use client"

import { usePathname } from "next/navigation"
import Link from "next/link"
import { ChevronRight } from "lucide-react"

const PATH_LABELS: Record<string, string> = {
  "": "Dashboard",
  upload: "Upload & Analyze",
  cases: "Cases",
  ctf: "CTF Workspace",
  jobs: "Jobs Pipeline",
  findings: "Findings Explorer",
  timeline: "Timeline",
  plugins: "Plugins",
  tools: "Tools Catalog",
  storage: "Storage Browser",
  reports: "Reports",
  admin: "Admin",
}

export function Breadcrumbs() {
  const pathname = usePathname()
  const segments = pathname.split("/").filter(Boolean)

  if (segments.length === 0) {
    return <span className="font-mono text-xs text-muted-foreground">Dashboard</span>
  }

  return (
    <nav className="flex items-center gap-1 text-xs font-mono" aria-label="Breadcrumb">
      <Link href="/" className="text-muted-foreground hover:text-foreground transition-colors">
        Home
      </Link>
      {segments.map((segment, i) => {
        const href = "/" + segments.slice(0, i + 1).join("/")
        const label = PATH_LABELS[segment] || segment
        const isLast = i === segments.length - 1
        return (
          <span key={href} className="flex items-center gap-1">
            <ChevronRight className="size-3 text-muted-foreground/50" />
            {isLast ? (
              <span className="text-foreground">{label}</span>
            ) : (
              <Link href={href} className="text-muted-foreground hover:text-foreground transition-colors">
                {label}
              </Link>
            )}
          </span>
        )
      })}
    </nav>
  )
}

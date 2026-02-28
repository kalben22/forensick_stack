"use client"

import { useEffect } from "react"
import { AlertTriangle, RefreshCw, Home } from "lucide-react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    // Log error to monitoring in production
    console.error("[Dashboard Error]", error)
  }, [error])

  return (
    <div className="flex min-h-[60vh] items-center justify-center p-6">
      <Card className="w-full max-w-md border-destructive/30 bg-destructive/5">
        <CardContent className="flex flex-col items-center gap-6 py-10 text-center">
          <div className="flex size-16 items-center justify-center rounded-full bg-destructive/20">
            <AlertTriangle className="size-8 text-destructive" />
          </div>

          <div>
            <h2 className="text-xl font-bold font-mono tracking-tight">Something went wrong</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              An unexpected error occurred while loading this page.
            </p>
            {error.digest && (
              <p className="mt-2 font-mono text-xs text-muted-foreground/60">
                Error ID: {error.digest}
              </p>
            )}
          </div>

          <div className="flex gap-3">
            <Button onClick={reset} variant="outline" className="gap-2">
              <RefreshCw className="size-4" />
              Try again
            </Button>
            <Button asChild>
              <Link href="/" className="gap-2">
                <Home className="size-4" />
                Go home
              </Link>
            </Button>
          </div>

          {process.env.NODE_ENV === "development" && (
            <details className="w-full rounded-lg bg-muted p-3 text-left">
              <summary className="cursor-pointer font-mono text-xs text-muted-foreground">
                Error details (dev only)
              </summary>
              <pre className="mt-2 overflow-auto font-mono text-[11px] text-destructive whitespace-pre-wrap">
                {error.message}
                {error.stack && `\n\n${error.stack}`}
              </pre>
            </details>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

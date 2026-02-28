import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Sign In – ForensicStack',
}

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative flex min-h-svh flex-col items-center justify-center bg-background">
      {/* Subtle forensic grid background */}
      <div
        className="pointer-events-none fixed inset-0 opacity-[0.03]"
        style={{
          backgroundImage:
            'linear-gradient(rgba(0,255,170,1) 1px, transparent 1px), linear-gradient(90deg, rgba(0,255,170,1) 1px, transparent 1px)',
          backgroundSize: '40px 40px',
        }}
      />
      {/* Header logo */}
      <div className="mb-8 flex flex-col items-center gap-2">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            className="h-7 w-7 text-primary"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
            />
          </svg>
        </div>
        <div className="text-center">
          <h1 className="text-xl font-semibold tracking-tight text-foreground">ForensicStack</h1>
          <p className="text-sm text-muted-foreground">DFIR Analysis Platform</p>
        </div>
      </div>

      {children}

      <p className="mt-8 text-center text-xs text-muted-foreground/60">
        Secure access · All sessions are logged
      </p>
    </div>
  )
}

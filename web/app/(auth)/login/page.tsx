import { Suspense } from 'react'
import type { Metadata } from 'next'
import { LoginForm } from '@/components/auth/login-form'
import { Loader2 } from 'lucide-react'

export const metadata: Metadata = {
  title: 'Sign In – ForensicStack',
}

export default function LoginPage() {
  return (
    <Suspense fallback={<Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />}>
      <LoginForm />
    </Suspense>
  )
}

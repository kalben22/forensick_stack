import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

const PUBLIC_PATHS = ['/login']

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const isPublic = PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(p + '/'))
  const token = request.cookies.get('auth-token')?.value

  // Unauthenticated → redirect to /login
  if (!isPublic && !token) {
    const loginUrl = new URL('/login', request.url)

    // Anti-open-redirect: only allow relative paths
    const redirectTo = pathname !== '/' ? pathname : undefined
    if (redirectTo && !redirectTo.startsWith('//')) {
      loginUrl.searchParams.set('redirect', redirectTo)
    }

    return NextResponse.redirect(loginUrl)
  }

  // Already authenticated → redirect away from /login
  if (isPublic && token) {
    return NextResponse.redirect(new URL('/', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * Match all request paths EXCEPT:
     * - _next/static (static files)
     * - _next/image  (image optimisation)
     * - favicon.ico, robots.txt
     */
    '/((?!_next/static|_next/image|favicon\\.ico|robots\\.txt).*)',
  ],
}

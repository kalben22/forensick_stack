'use client'

import { useState } from 'react'
import {
  Users,
  Server,
  ScrollText,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Clock,
  Shield,
  Activity,
} from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useMe } from '@/lib/hooks/use-auth'
import { mockAuditLog, mockSystemServices, mockUsers } from '@/lib/mock-data'
import { formatDateTime } from '@/lib/utils'

const STATUS_ICON = {
  running: <CheckCircle2 className="h-4 w-4 text-emerald-500" />,
  stopped: <XCircle className="h-4 w-4 text-destructive" />,
  error: <AlertCircle className="h-4 w-4 text-amber-500" />,
}

const ROLE_COLOR: Record<string, string> = {
  admin: 'bg-violet-500/15 text-violet-400 border-violet-500/30',
  analyst: 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30',
}

export function AdminContent() {
  const { data: me } = useMe()
  const [activeTab, setActiveTab] = useState('users')

  const isAdmin = me?.role === 'admin'

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Administration</h1>
          <p className="text-sm text-muted-foreground">
            Platform management · Users, system health, and audit trails
          </p>
        </div>
        {isAdmin && (
          <Badge variant="outline" className="border-violet-500/30 bg-violet-500/10 text-violet-400">
            <Shield className="mr-1 h-3 w-3" />
            Admin
          </Badge>
        )}
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          { label: 'Total Users', value: mockUsers.length, icon: Users },
          {
            label: 'Active Users',
            value: mockUsers.filter((u) => u.status === 'active').length,
            icon: Activity,
          },
          {
            label: 'Services Online',
            value: mockSystemServices.filter((s) => s.status === 'running').length,
            icon: Server,
          },
          { label: 'Audit Events', value: mockAuditLog.length, icon: ScrollText },
        ].map(({ label, value, icon: Icon }) => (
          <Card key={label}>
            <CardHeader className="flex flex-row items-center justify-between pb-2 pt-4">
              <CardTitle className="text-xs font-medium text-muted-foreground">{label}</CardTitle>
              <Icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent className="pb-4">
              <p className="text-2xl font-bold">{value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="users">
            <Users className="mr-1.5 h-3.5 w-3.5" />
            Users
          </TabsTrigger>
          <TabsTrigger value="system">
            <Server className="mr-1.5 h-3.5 w-3.5" />
            System
          </TabsTrigger>
          <TabsTrigger value="audit">
            <ScrollText className="mr-1.5 h-3.5 w-3.5" />
            Audit Log
          </TabsTrigger>
        </TabsList>

        {/* Users tab */}
        <TabsContent value="users" className="mt-4">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">Platform Users</CardTitle>
                <Button size="sm" disabled={!isAdmin}>
                  Invite User
                </Button>
              </div>
              <CardDescription>
                Manage analyst and admin accounts. Requires admin privileges.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Username</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Last Login</TableHead>
                    <TableHead />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {mockUsers.map((user) => (
                    <TableRow key={user.id}>
                      <TableCell className="font-medium">{user.name}</TableCell>
                      <TableCell className="text-muted-foreground">{user.email}</TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={ROLE_COLOR[user.role] ?? 'text-muted-foreground'}
                        >
                          {user.role}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {user.status === 'active' ? (
                          <span className="flex items-center gap-1 text-emerald-500 text-xs">
                            <CheckCircle2 className="h-3 w-3" /> Active
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-destructive text-xs">
                            <XCircle className="h-3 w-3" /> Inactive
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="text-muted-foreground text-xs">
                        {formatDateTime(user.lastLogin)}
                      </TableCell>
                      <TableCell>
                        <Button variant="ghost" size="sm" disabled={!isAdmin}>
                          Edit
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* System tab */}
        <TabsContent value="system" className="mt-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Service Health</CardTitle>
              <CardDescription>Real-time status of infrastructure components.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3 sm:grid-cols-2">
              {mockSystemServices.map((svc) => (
                <div
                  key={svc.name}
                  className="flex items-center justify-between rounded-lg border border-border/50 bg-card/50 p-4"
                >
                  <div className="flex items-center gap-3">
                    {STATUS_ICON[svc.status as keyof typeof STATUS_ICON] ?? (
                      <Clock className="h-4 w-4 text-muted-foreground" />
                    )}
                    <div>
                      <p className="text-sm font-medium">{svc.name}</p>
                      <p className="text-xs text-muted-foreground">{svc.version ?? 'Unknown'}</p>
                    </div>
                  </div>
                  <Badge
                    variant="outline"
                    className={
                      svc.status === 'running'
                        ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
                        : svc.status === 'stopped'
                          ? 'border-destructive/30 bg-destructive/10 text-destructive'
                          : 'border-amber-500/30 bg-amber-500/10 text-amber-400'
                    }
                  >
                    {svc.status}
                  </Badge>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Audit log tab */}
        <TabsContent value="audit" className="mt-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Audit Log</CardTitle>
              <CardDescription>All platform actions recorded for compliance.</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Timestamp</TableHead>
                    <TableHead>User</TableHead>
                    <TableHead>Action</TableHead>
                    <TableHead>Resource</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {mockAuditLog.map((entry) => (
                    <TableRow key={entry.id}>
                      <TableCell className="text-xs text-muted-foreground font-mono">
                        {formatDateTime(entry.timestamp)}
                      </TableCell>
                      <TableCell className="text-sm">{entry.user}</TableCell>
                      <TableCell>
                        <Badge variant="secondary" className="text-xs">
                          {entry.action}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground font-mono">
                        {entry.target}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

'use client'

import { useState } from 'react'
import {
  Folder,
  FolderOpen,
  FileText,
  HardDrive,
  Copy,
  Check,
  ChevronRight,
  Database,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { mockStorageTree } from '@/lib/mock-data'

type StorageNode = {
  id: string
  name: string
  type: 'folder' | 'file'
  size?: string
  modified?: string
  children?: StorageNode[]
  mimeType?: string
}

function FileIcon({ type, name }: { type: string; name: string }) {
  if (type === 'folder') return <Folder className="h-4 w-4 text-amber-400" />
  if (name.endsWith('.dmp') || name.endsWith('.raw') || name.endsWith('.mem'))
    return <Database className="h-4 w-4 text-cyan-400" />
  return <FileText className="h-4 w-4 text-muted-foreground" />
}

function TreeNode({
  node,
  depth = 0,
  onSelect,
  selected,
}: {
  node: StorageNode
  depth?: number
  onSelect: (n: StorageNode) => void
  selected: string | null
}) {
  const [open, setOpen] = useState(depth === 0)
  const hasChildren = node.children && node.children.length > 0

  return (
    <div>
      <button
        onClick={() => {
          if (hasChildren) setOpen((v) => !v)
          onSelect(node)
        }}
        className={`flex w-full items-center gap-1.5 rounded px-2 py-1 text-left text-sm transition-colors hover:bg-accent/50 ${
          selected === node.id ? 'bg-accent text-accent-foreground' : 'text-foreground/80'
        }`}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
      >
        {hasChildren ? (
          <ChevronRight
            className={`h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform ${open ? 'rotate-90' : ''}`}
          />
        ) : (
          <span className="w-3.5" />
        )}
        {hasChildren && open ? (
          <FolderOpen className="h-4 w-4 shrink-0 text-amber-400" />
        ) : (
          <FileIcon type={node.type} name={node.name} />
        )}
        <span className="truncate">{node.name}</span>
        {node.size !== undefined && (
          <span className="ml-auto shrink-0 text-xs text-muted-foreground">
            {node.size}
          </span>
        )}
      </button>
      {open && hasChildren && (
        <div>
          {node.children!.map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              depth={depth + 1}
              onSelect={onSelect}
              selected={selected}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export function StorageContent() {
  const [selected, setSelected] = useState<StorageNode | null>(null)
  const [copied, setCopied] = useState(false)

  const totalFileCount = mockStorageTree.reduce(
    (acc, n) => acc + (n.children?.length ?? 0),
    0
  )

  const handleCopyName = () => {
    if (!selected?.name) return
    navigator.clipboard.writeText(selected.name)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Storage Browser</h1>
        <p className="text-sm text-muted-foreground">
          Browse MinIO artifact storage — evidence files, analysis outputs, reports
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Total Used', value: '~154 GB', icon: HardDrive },
          { label: 'Buckets', value: mockStorageTree.length, icon: Folder },
          { label: 'Total Items', value: totalFileCount, icon: FileText },
        ].map(({ label, value, icon: Icon }) => (
          <Card key={label}>
            <CardHeader className="flex flex-row items-center justify-between pb-2 pt-4">
              <CardTitle className="text-xs font-medium text-muted-foreground">{label}</CardTitle>
              <Icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent className="pb-4">
              <p className="text-xl font-bold">{value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Explorer */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[300px_1fr]">
        {/* Tree */}
        <Card>
          <CardHeader className="pb-2 pt-4">
            <CardTitle className="text-sm">File Tree</CardTitle>
          </CardHeader>
          <Separator />
          <CardContent className="p-0">
            <ScrollArea className="h-[400px]">
              <div className="py-2">
                {mockStorageTree.map((node) => (
                  <TreeNode
                    key={node.id}
                    node={node as StorageNode}
                    onSelect={setSelected}
                    selected={selected?.id ?? null}
                  />
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Detail panel */}
        <Card>
          <CardHeader className="pb-2 pt-4">
            <CardTitle className="text-sm">Details</CardTitle>
          </CardHeader>
          <Separator />
          <CardContent className="pt-4">
            {selected ? (
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <FileIcon type={selected.type} name={selected.name} />
                  <div>
                    <p className="font-medium">{selected.name}</p>
                    <Badge variant="secondary" className="text-xs mt-0.5">
                      {selected.type}
                    </Badge>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 rounded-lg border border-border/50 bg-muted/30 p-3 text-sm">
                  {selected.size !== undefined && (
                    <>
                      <span className="text-muted-foreground">Size</span>
                      <span className="font-mono">{selected.size}</span>
                    </>
                  )}
                  {selected.mimeType && (
                    <>
                      <span className="text-muted-foreground">MIME</span>
                      <span className="font-mono text-xs">{selected.mimeType}</span>
                    </>
                  )}
                  {selected.modified && (
                    <>
                      <span className="text-muted-foreground">Modified</span>
                      <span className="font-mono text-xs">{selected.modified}</span>
                    </>
                  )}
                </div>

                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={handleCopyName}>
                    {copied ? (
                      <Check className="mr-1.5 h-3.5 w-3.5 text-emerald-500" />
                    ) : (
                      <Copy className="mr-1.5 h-3.5 w-3.5" />
                    )}
                    {copied ? 'Copied!' : 'Copy Name'}
                  </Button>
                  {selected.type === 'file' && (
                    <Button size="sm" disabled>
                      Download
                      <span className="ml-1.5 text-xs opacity-60">(Phase 2)</span>
                    </Button>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex h-48 flex-col items-center justify-center gap-2 text-center text-muted-foreground">
                <Folder className="h-8 w-8 opacity-30" />
                <p className="text-sm">Select a file or folder to see details</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

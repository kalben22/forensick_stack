import type { Metadata } from 'next'
import { ToolDetailPage } from '@/components/tools/tool-detail-page'

interface Props {
  params: { slug: string }
}

export function generateMetadata({ params }: Props): Metadata {
  const label =
    params.slug === 'volatility' ? 'Volatility 3' :
    params.slug === 'exiftool'   ? 'ExifTool' :
    params.slug === 'ileapp'     ? 'iLEAPP' :
    params.slug === 'aleapp'     ? 'aLEAPP' :
    params.slug

  return { title: `${label} — ForensicStack` }
}

export default function Page({ params }: Props) {
  return <ToolDetailPage slug={params.slug} />
}

import type { Metadata } from 'next'
import { ToolDetailPage } from '@/components/tools/tool-detail-page'

interface Props {
  params: Promise<{ slug: string }>
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params
  const label =
    slug === 'volatility' ? 'Volatility 3' :
    slug === 'exiftool'   ? 'ExifTool' :
    slug === 'ileapp'     ? 'iLEAPP' :
    slug === 'aleapp'     ? 'aLEAPP' :
    slug

  return { title: `${label} — ForensicStack` }
}

export default async function Page({ params }: Props) {
  const { slug } = await params
  return <ToolDetailPage slug={slug} />
}

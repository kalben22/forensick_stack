import { CaseDetailContent } from "@/components/cases/case-detail-content"

export default async function CaseDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  return <CaseDetailContent caseId={id} />
}

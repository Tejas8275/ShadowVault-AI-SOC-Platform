import type { CaseRecord } from './contracts.ts'

export interface ReportRecord {
  citation: string; evidence_id: string | null; fields: Record<string, string | number | null>
}
export interface CaseReportDraft {
  schema_version: 1; status: 'draft'; generated_at: string; case: CaseRecord; scope: string
  summary: Record<string, number>; sections: {title: string; records: ReportRecord[]}[]; limitations: string[]
}
export const reportLabel = (key: string) => key.replaceAll('_', ' ')
export const reportValue = (value: string | number | null | undefined) => value == null ? 'Not recorded' : String(value)

// An inert text artifact, not Markdown/HTML that interprets investigator text.
export function reportText(report: CaseReportDraft): string {
  const lines = ['ShadowVault AI — Investigation report draft', `Case: ${report.case.title}`,
    `Case citation: incident:${report.case.id}`, `Generated (UTC): ${report.generated_at}`, report.scope,
    '', 'CASE DETAILS', ...Object.entries(report.case).map(([key,value])=>`${reportLabel(key)}: ${reportValue(value)}`),
    '', 'INVESTIGATION SUMMARY', ...Object.entries(report.summary).map(([key,count])=>`${key}: ${count}`)]
  for (const section of report.sections) {
    lines.push('', section.title.toUpperCase())
    if (!section.records.length) lines.push('No authorized records recorded in this snapshot.')
    for (const row of section.records) lines.push(`Source citation: ${row.citation}`,
      ...(row.evidence_id ? [`Source evidence: evidence:${row.evidence_id}`] : []),
      ...Object.entries(row.fields).map(([key,value])=>`${reportLabel(key)}: ${reportValue(value)}`), '')
  }
  lines.push('', 'SCOPE AND LIMITATIONS', ...report.limitations)
  return lines.join('\n')
}

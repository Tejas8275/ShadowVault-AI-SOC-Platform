export type CaseStatus = 'open' | 'investigating' | 'closed'
export type CaseSeverity = 'low' | 'medium' | 'high' | 'critical'
export interface CaseDraft { title: string; description: string; severity: CaseSeverity }
export interface CaseRecord extends CaseDraft {
  id: string; status: CaseStatus; created_by_id: string; created_at: string; updated_at?: string | null; revision: number
}
export interface CasePage { items: CaseRecord[]; total: number; next_cursor: string | null }
export interface CaseHistoryEvent {
  id: string; incident_id: string; revision: number; event_type: 'baseline_registered' | 'case_created' | 'case_updated';
  actor_label: string; source: 'api' | 'trusted_cli' | 'migration'; recorded_at: string;
  changes: Record<string, {before: string | null; after: string}>;
}
export interface CaseHistoryPage {
  items: CaseHistoryEvent[]; tracking_started: boolean; tracking_started_revision: number | null; next_revision: number | null;
}
export const transitions: Record<CaseStatus, CaseStatus[]> = {
  open: ['open', 'investigating'], investigating: ['investigating', 'closed'], closed: ['closed', 'investigating'],
}

export interface CaseIntelligence {
  evidence_count: number; timeline_count: number; history_revision_count: number;
  history_started_revision: number | null; latest_activity_at: string;
}
export interface CaseIntelligenceRecord extends CaseRecord { intelligence?: CaseIntelligence | null }

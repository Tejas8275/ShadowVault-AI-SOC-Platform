export type ReviewState = 'unreviewed' | 'in_review' | 'reviewed'
export type IntegrityResult = 'not_checked' | 'matches' | 'mismatch' | 'missing' | 'unavailable'
export interface Evidence {
  id: string; incident_id: string; collection_job_id: string | null; collection_item_id: string | null
  filename: string; display_title: string | null; source_path: string | null; media_type: string
  size_bytes: number; sha256: string; created_at: string; collected_at: string | null
  initial_verification_status: string; initial_verified_at: string | null
  review_state: ReviewState; metadata_revision: number; tags: string[]
  integrity_result: IntegrityResult; integrity_checked_at: string | null; custody_started: boolean
}
export interface EvidenceDetails extends Evidence {
  collected_by_user_id: string; requested_by_user_id: string | null; agent_id: string | null
  custody_sequence: number; custody_head_hash: string | null; note_count: number
}
export interface SearchPage { items: Evidence[]; total: number; next_cursor: string | null }
export interface Note { id: string; evidence_id: string; author_id: string; author_label: string; body: string; created_at: string }
export interface NotesPage { items: Note[]; next_cursor: string | null }
export interface CustodyEvent {
  id: string; evidence_id: string; sequence: number; event_type: string; actor_type: string
  actor_label: string; actor_user_id: string | null; actor_agent_id: string | null; system_actor: string | null
  recorded_at: string; source_at: string | null; operation_id: string; schema_version: number
  details: Record<string, unknown>; previous_hash: string | null; event_hash: string
}
export interface CustodyPage { items: CustodyEvent[]; tracking_started: boolean; head_sequence: number; head_hash: string | null; next_sequence: number | null }
export interface Annotations { expected_revision: number; display_title?: string | null; review_state?: ReviewState; tags?: string[] }
export type Filters = Record<string, string>

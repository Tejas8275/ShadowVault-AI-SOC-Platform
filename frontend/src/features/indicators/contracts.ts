export type IndicatorKind = 'sha256' | 'ip' | 'domain' | 'filename'
export interface IndicatorSubmission {
 kind: IndicatorKind
 source_kind: 'manual' | 'evidence_sha256' | 'evidence_filename'
 raw_value?: string
 source_locator?: string
 submission_id: string
 supersedes_id?: string
}
export interface IndicatorObservation {
 id: string; incident_id: string; evidence_id: string; kind: IndicatorKind
 raw_value: string; normalized_value: string; source_kind: string; source_locator: string | null
 created_by_id: string; actor_label: string; created_at: string; schema_version: number; supersedes_id: string | null; superseded_by_id?: string | null
}
export interface IndicatorPage { items: IndicatorObservation[]; next_cursor: string | null }

export interface IndicatorFilters { kind?: IndicatorKind | ''; value?: string; evidence_id?: string; observation_id?: string }
export interface EvidenceIndicatorContext { id: string; filename: string; action: 'view' | 'add'; sequence: number }

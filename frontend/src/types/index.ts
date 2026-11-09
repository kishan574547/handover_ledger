export type DemoRole = 'departing' | 'lead' | 'developer' | 'coordinator';

export type ClaimStatus = 'verified' | 'inferred' | 'conflicting' | 'missing' | 'restricted';

export type ClaimType =
  | 'decision'
  | 'open_work'
  | 'owner'
  | 'risk'
  | 'dependency'
  | 'contact'
  | 'recurring_problem'
  | 'next_action'
  | 'change'
  | 'restricted';

export type ReviewState = 'pending' | 'approved' | 'rejected';

export interface ProjectInfo {
  id: string;
  name: string;
  description: string;
  departing_member: string;
  lead_name: string;
  successor_name: string;
  coordinator_name: string;
  handover_status: 'draft' | 'in_review' | 'approved' | 'sent_back';
  updated_at?: string;
}

export interface ImportReport {
  repository: string;
  commits_imported: number;
  issues_imported: number;
  prs_imported: number;
  comments_imported: number;
  docs_imported: number;
  total_chunks: number;
  items_skipped: number;
  warnings: string[];
}

export interface SourceItem {
  id: string;
  name: string;
  kind: 'github' | 'notes' | 'chat';
  clearance: number;
  item_count: number;
  masked_count: number;
  content_hash?: string;
  added_at: string;
  import_report?: ImportReport;
}

export interface EvidenceItem {
  id: string;
  claim_id: string;
  chunk_id?: string;
  source_name?: string;
  location_label?: string;
  surrounding_text?: string;
  quote: string;
  match_score: number;
  support: 'supported' | 'partial' | 'not_supported';
  reason?: string;
}

export interface CommentItem {
  id: string;
  claim_id: string;
  role: string;
  text: string;
  created_at: string;
}

export interface ConflictLinkItem {
  id: string;
  claim_a_id: string;
  claim_b_id: string;
  resolution?: string;
  conflicting_claim_text?: string;
}

export interface ClaimItem {
  id: string;
  type: ClaimType;
  text: string;
  status: ClaimStatus;
  clearance: number;
  owner_name?: string | null;
  event_date?: string | null;
  subject_key: string;
  review_state: ReviewState;
  created_by: 'system' | 'leaver';
  evidence_count: number;
  is_hidden?: boolean;
}

export interface ClaimDetail extends ClaimItem {
  evidence: EvidenceItem[];
  comments: CommentItem[];
  conflict_link?: ConflictLinkItem | null;
  conflicting_claim?: ClaimItem | null;
}

export interface QuestionItem {
  id: string;
  text: string;
  why_we_ask: string;
  claim_id?: string;
  priority: 'high' | 'medium' | 'low';
  state: 'open' | 'answered' | 'skipped' | 'unknown';
  answer?: string | null;
  linked_quote?: string;
  linked_source?: string;
}

export interface TimelineItem {
  id: string;
  date: string;
  type: string;
  title: string;
  status: ClaimStatus;
  clearance: number;
  owner_name?: string;
  is_unresolved: boolean;
  review_state: string;
  evidence_count: number;
  evidence_snippet?: string;
  source_label?: string;
  subject_key: string;
}

export interface HandoverVersionItem {
  id: string;
  number: number;
  note?: string;
  status: 'draft' | 'approved' | 'sent_back';
  created_at: string;
}

export interface CitationItem {
  claim_id: string;
  text: string;
  quote?: string;
  source_name?: string;
  location_label?: string;
}

export interface HandoverSection {
  title: string;
  key: string;
  claims: ClaimItem[];
  hidden_count: number;
  citations: CitationItem[];
}

export interface HandoverViewData {
  role: string;
  clearance_level: number;
  handover_status: string;
  project_name: string;
  departing_member: string;
  successor_name: string;
  sections: Record<string, HandoverSection>;
  total_visible_claims: number;
  total_hidden_claims: number;
  released_at?: string;
  acknowledged: boolean;
  acknowledged_at?: string;
  acknowledged_by?: string;
}

export interface LeakCheckResult {
  passed: boolean;
  findings: string[];
  total_findings: number;
}

export interface StepProgress {
  name: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  percent: number;
  details?: string;
}

export interface AnalysisStatusData {
  is_running: boolean;
  current_step: string;
  percent: number;
  error?: string;
  error_details?: string;
  steps: StepProgress[];
}

export interface AIHealthData {
  ok: boolean;
  model_in_use: string | null;
  fallback_used: boolean;
  error_type: string | null;
}

export interface BackendHealthData {
  status: string;
  app: string;
  database: 'sqlite' | 'postgresql';
  service?: string;
  version?: string;
}

export interface GitHubHealthData {
  reachable: boolean;
  token_configured: boolean;
  remaining_rate_limit: number | null;
  reset_time: string | null;
  rate_limit_low?: boolean;
}

export interface ActivityItem {
  id: string;
  role: string;
  action: string;
  target: string;
  at: string;
}

export interface DashboardData {
  handover_status: string;
  readiness_percent: number;
  status_counts: {
    verified: number;
    inferred: number;
    conflicting: number;
    missing: number;
    total: number;
  };
  open_conflicts_count: number;
  unanswered_questions_count: number;
  top_risks: ClaimItem[];
  next_actions: ClaimItem[];
  ownership_breakdown: { owner_name: string; count: number }[];
  recent_activity: ActivityItem[];
  has_analysis: boolean;
}

export interface ReviewSummary {
  readiness_percent: number;
  is_ready_for_release: boolean;
  handover_status: string;
  checklist: {
    id: string;
    title: string;
    passed: boolean;
    count: number;
    message: string;
    fix_link: string;
  }[];
  metrics: {
    total_claims: number;
    approved_claims: number;
    pending_claims: number;
    rejected_claims: number;
    unresolved_conflicts: number;
    total_conflicts: number;
    open_high_priority_questions: number;
    answered_questions: number;
    total_questions: number;
    confidential_claims: number;
  };
  version_count: number;
}

// --- Ask the Handover Types ---
export interface CitedClaimItem {
  id: string;
  status: ClaimStatus;
  short_text: string;
}

export interface SentenceCitationItem {
  text: string;
  claim_ids: string[];
}

export interface AskResponseData {
  found: boolean;
  answer: string;
  sentences: SentenceCitationItem[];
  cited_claims: CitedClaimItem[];
  verification_summary: string;
  restricted_notice?: string | null;
  question_created_id?: string | null;
}

// --- Project Meta Types ---
export type ProjectMode = 'demo' | 'own' | 'empty';

export interface ProjectData {
  mode: ProjectMode;
  display_name: string | null;
  leaver_name: string | null;
  id: string;
  name: string;
  description?: string;
  departing_member?: string | null;
  lead_name?: string | null;
  successor_name?: string | null;
  coordinator_name?: string | null;
  handover_status: string;
  updated_at?: string | null;
}


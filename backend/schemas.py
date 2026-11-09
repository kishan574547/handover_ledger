from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict

# --- Sources ---
class SourceBase(BaseModel):
    name: str
    kind: str
    clearance: int = 1

class SourceOut(SourceBase):
    id: str
    item_count: int
    masked_count: int
    content_hash: Optional[str] = None
    added_at: datetime
    model_config = ConfigDict(from_attributes=True)

class SourceCreateGithub(BaseModel):
    url: str

class SourceUpdateClearance(BaseModel):
    clearance: int = Field(..., ge=1, le=3)

# --- Chunks ---
class ChunkOut(BaseModel):
    id: str
    source_id: str
    location_label: str
    text: str
    model_config = ConfigDict(from_attributes=True)

# --- Evidence ---
class EvidenceOut(BaseModel):
    id: str
    claim_id: str
    chunk_id: Optional[str] = None
    source_name: Optional[str] = None
    location_label: Optional[str] = None
    surrounding_text: Optional[str] = None
    quote: str
    match_score: float
    support: str
    reason: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

# --- Comments ---
class CommentOut(BaseModel):
    id: str
    claim_id: str
    role: str
    text: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class CommentCreate(BaseModel):
    text: str

# --- Conflicts ---
class ConflictLinkOut(BaseModel):
    id: str
    claim_a_id: str
    claim_b_id: str
    resolution: Optional[str] = None
    conflicting_claim_text: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

# --- Claims ---
class ClaimOut(BaseModel):
    id: str
    type: str
    text: str
    status: str
    clearance: int
    owner_name: Optional[str] = None
    event_date: Optional[str] = None
    subject_key: str
    review_state: str
    created_by: str
    evidence_count: int = 0
    is_hidden: bool = False  # For masked placeholder rows above clearance
    model_config = ConfigDict(from_attributes=True)

class ClaimDetailOut(ClaimOut):
    evidence: List[EvidenceOut] = []
    comments: List[CommentOut] = []
    conflict_link: Optional[ConflictLinkOut] = None
    conflicting_claim: Optional[ClaimOut] = None

class ClaimUpdate(BaseModel):
    text: Optional[str] = None
    review_state: Optional[str] = None  # pending, approved, rejected
    note: Optional[str] = None

class ClaimResolveConflict(BaseModel):
    choice: str = Field(..., description="keep_a, keep_b, keep_both, or custom")
    text: Optional[str] = None

# --- Questions ---
class QuestionOut(BaseModel):
    id: str
    text: str
    why_we_ask: str
    claim_id: Optional[str] = None
    priority: str
    state: str
    answer: Optional[str] = None
    linked_quote: Optional[str] = None
    linked_source: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class QuestionAnswer(BaseModel):
    answer: str

# --- Handover Versions ---
class HandoverVersionOut(BaseModel):
    id: str
    number: int
    note: Optional[str] = None
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class HandoverVersionCreate(BaseModel):
    note: Optional[str] = None

class HandoverDiffOut(BaseModel):
    version_a: int
    version_b: int
    added_claims: List[ClaimOut]
    removed_claims: List[ClaimOut]
    changed_claims: List[Dict[str, Any]]

class HandoverApproveRequest(BaseModel):
    note: Optional[str] = None
    accept_open_items: bool = False

class HandoverSendBackRequest(BaseModel):
    note: str

# --- Handover View ---
class CitationItem(BaseModel):
    claim_id: str
    text: str
    quote: Optional[str] = None
    source_name: Optional[str] = None
    location_label: Optional[str] = None

class HandoverSection(BaseModel):
    title: str
    key: str
    claims: List[ClaimOut] = []
    hidden_count: int = 0
    citations: List[CitationItem] = []

class HandoverViewOut(BaseModel):
    role: str
    clearance_level: int
    handover_status: str
    project_name: str
    departing_member: str
    successor_name: str
    sections: Dict[str, HandoverSection]
    total_visible_claims: int
    total_hidden_claims: int
    released_at: Optional[datetime] = None
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None

# --- Leak Check ---
class LeakFinding(BaseModel):
    type: str  # clearance_violation, secret_pattern, unmasked_pii
    detail: str
    location: str

class LeakCheckResult(BaseModel):
    passed: bool
    findings: List[str]
    total_findings: int

# --- Acknowledgement ---
class AcknowledgementCreate(BaseModel):
    name: str

class AcknowledgementOut(BaseModel):
    id: str
    role: str
    name: str
    version_id: Optional[str] = None
    at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- Activity Log ---
class ActivityLogOut(BaseModel):
    id: str
    role: str
    action: str
    target: str
    at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- Dashboard ---
class StatusCount(BaseModel):
    verified: int
    inferred: int
    conflicting: int
    missing: int
    total: int

class OwnerClaimCount(BaseModel):
    owner_name: str
    count: int

class DashboardOut(BaseModel):
    handover_status: str
    readiness_percent: int
    status_counts: StatusCount
    open_conflicts_count: int
    unanswered_questions_count: int
    top_risks: List[ClaimOut]
    next_actions: List[ClaimOut]
    ownership_breakdown: List[OwnerClaimCount]
    recent_activity: List[ActivityLogOut]
    has_analysis: bool

# --- Analysis Status ---
class StepProgress(BaseModel):
    name: str
    status: str  # pending, in_progress, completed, failed
    percent: int
    details: Optional[str] = None

class AnalysisStatusOut(BaseModel):
    is_running: bool
    current_step: str
    percent: int
    error: Optional[str] = None
    error_details: Optional[str] = None
    steps: List[StepProgress]

# --- AI Extraction Schemas (Gemini Structured Output) ---
class ExtractedClaimItem(BaseModel):
    type: str = Field(description="decision | open_work | owner | risk | dependency | contact | recurring_problem | next_action | change")
    text: str = Field(description="The reconstructed factual claim sentence")
    owner_name: Optional[str] = Field(default=None, description="Person responsible or mentioned")
    event_date: Optional[str] = Field(default=None, description="Date or time string mentioned or inferred")
    subject_key: str = Field(description="Topic identifier for grouping e.g. api_timeout, payment_gateway, deployment_host")
    quote: str = Field(description="Exact verbatim excerpt from the chunk that evidences this claim")
    chunk_location: Optional[str] = Field(default=None, description="Chunk location label")

class ExtractedClaimsBatch(BaseModel):
    claims: List[ExtractedClaimItem]

class VerifierJudgement(BaseModel):
    support: str = Field(description="supported | partial | not_supported")
    reason: str = Field(description="One-line objective reasoning for the judgement")

# --- Ask the Handover Schemas ---
class AskRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=1000)

class CitedClaim(BaseModel):
    id: str
    status: str
    short_text: str

class SentenceCitation(BaseModel):
    text: str
    claim_ids: List[str]

class AskResponse(BaseModel):
    found: bool
    answer: str
    sentences: List[SentenceCitation] = []
    cited_claims: List[CitedClaim] = []
    verification_summary: str = "No evidence found"
    restricted_notice: Optional[str] = None
    question_created_id: Optional[str] = None

class CreateQuestionFromAsk(BaseModel):
    question: str
    why_we_ask: Optional[str] = None



import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, Text, DateTime, ForeignKey, Enum as SQLEnum, select
)
from sqlalchemy.orm import relationship
from backend.database import Base

def gen_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class Project(Base):
    """Singleton/Active project state tracker."""
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default="default")
    name = Column(String(255), default="Campus Connect")
    description = Column(Text, default="A college club mobile & web application")
    departing_member = Column(String(255), default="Arjun Mehta (Tech Lead)")
    lead_name = Column(String(255), default="Priya Nair (Club President)")
    successor_name = Column(String(255), default="Rahul Verma (Successor Developer)")
    coordinator_name = Column(String(255), default="Sneha Iyer (Club Coordinator)")
    handover_status = Column(String(50), default="draft")  # not_started, draft, in_review, approved, sent_back
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

class Source(Base):
    __tablename__ = "sources"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False)
    kind = Column(String(50), nullable=False)  # github, notes, chat
    clearance = Column(Integer, default=1)  # 1: General, 2: Technical, 3: Confidential
    raw_text = Column(Text, nullable=True)
    item_count = Column(Integer, default=0)
    masked_count = Column(Integer, default=0)
    content_hash = Column(String(64), nullable=True, index=True)
    added_at = Column(DateTime, default=utc_now)

    chunks = relationship("Chunk", back_populates="source", cascade="all, delete-orphan")

class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    source_id = Column(String(36), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    location_label = Column(String(255), nullable=False)  # e.g. "Issue #14", "Commit a1b2c3d", "notes lines 20-31"
    text = Column(Text, nullable=False)

    source = relationship("Source", back_populates="chunks")
    evidence_items = relationship("Evidence", back_populates="chunk", cascade="all, delete-orphan")

class Claim(Base):
    __tablename__ = "claims"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    type = Column(String(50), nullable=False)  # decision, open_work, owner, risk, dependency, contact, recurring_problem, next_action, change
    text = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="inferred")  # verified, inferred, conflicting, missing
    clearance = Column(Integer, default=1)  # 1, 2, 3
    owner_name = Column(String(255), nullable=True)
    event_date = Column(String(50), nullable=True)
    subject_key = Column(String(100), nullable=False, index=True)
    review_state = Column(String(50), default="pending")  # pending, approved, rejected
    created_by = Column(String(50), default="system")  # system, leaver

    evidence = relationship("Evidence", back_populates="claim", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="claim", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="claim")

class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    claim_id = Column(String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)
    chunk_id = Column(String(36), ForeignKey("chunks.id", ondelete="SET NULL"), nullable=True)
    quote = Column(Text, nullable=False)
    match_score = Column(Float, default=0.0)
    support = Column(String(50), default="partial")  # supported, partial, not_supported
    reason = Column(Text, nullable=True)

    claim = relationship("Claim", back_populates="evidence")
    chunk = relationship("Chunk", back_populates="evidence_items")

class ConflictLink(Base):
    __tablename__ = "conflict_links"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    claim_a_id = Column(String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)
    claim_b_id = Column(String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)
    resolution = Column(Text, nullable=True)  # keep_a, keep_b, keep_both, or custom description

    claim_a = relationship("Claim", foreign_keys=[claim_a_id])
    claim_b = relationship("Claim", foreign_keys=[claim_b_id])

class Question(Base):
    __tablename__ = "questions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    text = Column(Text, nullable=False)
    why_we_ask = Column(Text, nullable=False)
    claim_id = Column(String(36), ForeignKey("claims.id", ondelete="SET NULL"), nullable=True)
    priority = Column(String(50), default="medium")  # high, medium, low
    state = Column(String(50), default="open")  # open, answered, skipped, unknown
    answer = Column(Text, nullable=True)

    claim = relationship("Claim", back_populates="questions")

class Comment(Base):
    __tablename__ = "comments"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    claim_id = Column(String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    claim = relationship("Claim", back_populates="comments")

class HandoverVersion(Base):
    __tablename__ = "handover_versions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    number = Column(Integer, nullable=False)
    note = Column(Text, nullable=True)
    snapshot_json = Column(Text, nullable=False)
    status = Column(String(50), default="draft")  # draft, approved, sent_back
    created_at = Column(DateTime, default=utc_now)

class Acknowledgement(Base):
    __tablename__ = "acknowledgements"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    role = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    version_id = Column(String(36), ForeignKey("handover_versions.id", ondelete="SET NULL"), nullable=True)
    at = Column(DateTime, default=utc_now)

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    role = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False)
    target = Column(String(255), nullable=False)
    at = Column(DateTime, default=utc_now)


# Database query layer clearance enforcement
def query_claims_with_clearance(db, max_clearance: int):
    """
    Enforces clearance filtering at the database query layer.
    Never returns any claim with clearance > max_clearance.
    """
    return db.query(Claim).filter(Claim.clearance <= max_clearance)


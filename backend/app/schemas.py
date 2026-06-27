from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class InvestigationStep(BaseModel):
    focus: str
    key_questions: list[str] = Field(default_factory=list)
    search_query: str


class TimelineEvent(BaseModel):
    agent: str
    stage: Literal["planning", "retrieval", "reading", "critique", "synthesis", "retry", "system"]
    status: Literal["working", "complete", "retry", "error", "pending"]
    title: str
    detail: str
    pass_index: int = 1
    timestamp: str = Field(default_factory=utcnow_iso)


class SourceRecord(BaseModel):
    id: str
    title: str
    abstract: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    url: str | None = None
    pdf_url: str | None = None
    provider: Literal["semantic_scholar", "arxiv", "crossref", "simulated"]
    citation_count: int | None = None
    relevance_score: float = 0.0
    simulated: bool = False


class EvidenceCard(BaseModel):
    source_id: str
    source_title: str
    provider: str
    claim: str
    methodology: str
    findings: str
    limitations: list[str] = Field(default_factory=list)
    stance: Literal["supports", "mixed", "questions", "neutral"] = "neutral"
    evidence_strength: Literal["high", "moderate", "preliminary"] = "preliminary"
    highlight: str


class ContradictionCard(BaseModel):
    summary: str
    explanation: str
    severity: Literal["high", "medium", "low"] = "medium"
    source_ids: list[str] = Field(default_factory=list)


class VerdictPayload(BaseModel):
    final_verdict: str
    confidence_score: float
    supporting_evidence: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)
    sources: list[SourceRecord] = Field(default_factory=list)
    evidence_cards: list[EvidenceCard] = Field(default_factory=list)
    contradiction_cards: list[ContradictionCard] = Field(default_factory=list)
    mode: str = "live"
    simulated_research: bool = False
    council_summary: str = ""
    passes_completed: int = 1
    # Gap-Finder fields
    research_gaps: list[str] = Field(default_factory=list)
    gap_summary: str = ""
    has_critical_gaps: bool = False
    # Archivist fields
    formatted_citations: list[str] = Field(default_factory=list)
    previous_related_queries: list[str] = Field(default_factory=list)


class QueryRequest(BaseModel):
    question: str = Field(min_length=12, max_length=500)
    confidence_threshold: float | None = Field(default=None, ge=0.35, le=0.95)
    max_passes: int | None = Field(default=None, ge=1, le=3)


class QueryCreatedResponse(BaseModel):
    id: str
    status: str
    created_at: str


class QueryStatusResponse(BaseModel):
    id: str
    question: str
    status: str
    current_stage: str
    current_message: str
    created_at: str
    updated_at: str
    pass_count: int
    max_passes: int
    confidence_threshold: float
    confidence_score: float | None = None
    mode: str = "pending"
    simulated_research: bool = False
    timeline: list[TimelineEvent] = Field(default_factory=list)
    investigation_plan: list[InvestigationStep] = Field(default_factory=list)
    sources: list[SourceRecord] = Field(default_factory=list)
    evidence_cards: list[EvidenceCard] = Field(default_factory=list)
    contradiction_cards: list[ContradictionCard] = Field(default_factory=list)


class QueryResultEnvelope(BaseModel):
    id: str
    status: str
    ready: bool
    error_message: str | None = None
    result: VerdictPayload | None = None

"""
Core Domain Models and Pydantic Contracts with Citation Validation.
Inspired by Instructor's CitationMixin pattern to ensure 100% traceability and zero hallucination.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field, model_validator, ValidationInfo


class CitationMixin(BaseModel):
    """
    Enforces that evidence quotes or surface words exist verbatim inside the raw source text.
    Prevents hallucinated extraction spans.
    """
    evidence_quote: str = Field(description="Verbatim substring quoted from raw text as evidence")
    span_start: int = Field(default=-1, description="Start character index in raw text")
    span_end: int = Field(default=-1, description="End character index in raw text")

    @model_validator(mode="after")
    def validate_citation_against_context(self, info: ValidationInfo) -> "CitationMixin":
        if info.context and "raw_text" in info.context:
            raw_text = info.context["raw_text"]
            if self.evidence_quote and self.evidence_quote not in raw_text:
                raise ValueError(
                    f"Citation violation: '{self.evidence_quote}' does not exist inside raw text."
                )
            if self.evidence_quote and self.span_start >= 0 and self.span_end > self.span_start:
                expected = raw_text[self.span_start:self.span_end]
                if expected != self.evidence_quote:
                    # Auto-correct span if found elsewhere
                    idx = raw_text.find(self.evidence_quote)
                    if idx >= 0:
                        self.span_start = idx
                        self.span_end = idx + len(self.evidence_quote)
        return self


class RawDocument(BaseModel):
    document_id: str = Field(description="Unique document/review identifier")
    source: str = Field(description="Source dataset e.g. AI_HUB, SMARTSTORE_ANUA")
    raw_text: str = Field(description="Immutable original review text")
    rating: Optional[int] = Field(default=None, description="Numeric star rating 1-5")
    created_at: Optional[datetime] = Field(default=None)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SemanticExtraction(CitationMixin):
    extraction_id: str = Field(description="Unique extraction item ID")
    document_id: str = Field(description="FK pointing to RawDocument")
    surface_text: str = Field(description="Original surface wording or slang")
    concept_id: str = Field(description="Standardized canonical concept ID")
    aspect: str = Field(description="Aspect category e.g. 보습력, 발림성, 트러블/자극, 가격/반품")
    sentiment: str = Field(description="POSITIVE, NEUTRAL, or NEGATIVE")
    intensity: str = Field(default="MODERATE", description="MILD, MODERATE, or STRONG")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    method: str = Field(default="HYBRID_V01", description="Extraction method e.g. FASTPATH_TRIE, EMBEDDING, LLM")


class ConceptRegistry(BaseModel):
    concept_id: str = Field(description="Unique standard concept ID")
    canonical_label: str = Field(description="Human readable standard label")
    domain: str = Field(default="K_BEAUTY")
    parent_concept_id: Optional[str] = Field(default=None)
    aliases: List[str] = Field(default_factory=list, description="Synonyms, slangs, typo variants")
    status: str = Field(default="APPROVED", description="APPROVED, CANDIDATE, or REJECTED")
    version: str = Field(default="0.1.0")


class EvalAuditLog(BaseModel):
    eval_id: str
    testbed_name: str
    evaluated_at: datetime = Field(default_factory=datetime.now)
    pairwise_precision: float
    pairwise_f1: float
    oov_recall: float
    aggregate_count_error: float
    text_to_sql_accuracy: float
    token_reduction_rate: float
    passed_gates_count: int

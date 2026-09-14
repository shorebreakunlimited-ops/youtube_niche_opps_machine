"""Typed case ledger records."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .scoring import candidate_score, count_poison_signals, youtube_is_verified


@dataclass
class CaseSource:
    case_id: str
    source_type: str
    source_url: str
    source_title: str
    provenance_class: str = ""
    acquisition_notes: str = ""
    notes: str = ""


@dataclass
class CaseRecord:
    case_id: str
    ledger: str
    case_name: str
    working_title: str
    jurisdiction: str
    incident_date: str
    release_date: str
    parent_case_id: str
    relationship: str
    is_child: bool
    evidence_available: str
    has_bodycam: bool
    has_interrogation: bool
    has_911_audio: bool
    has_court_records: bool
    has_sentencing_or_outcome: bool
    novelty: Optional[int]
    evidence: Optional[int]
    decision_chain: Optional[int]
    aftermath: Optional[int]
    packaging: Optional[int]
    production_fit: Optional[int]
    safety: Optional[int]
    candidate_score: Optional[int]
    verdict: str
    poison_five_plus_over_500k: bool
    poison_covered_by_major_creator: bool
    poison_name_famous: bool
    poison_heavily_clipped: bool
    poison_no_new_update: bool
    poison_heavily_politicized: bool
    poison_needs_psych_claims: bool
    poison_poor_footage: bool
    poison_signal_count: int
    verified_at: Optional[str]
    search_queries: str
    videos_reviewed: Optional[int]
    videos_over_500k: Optional[int]
    top_video_views: Optional[int]
    top_video_url: Optional[str]
    major_creator_matches: str
    data_source: str
    youtube_verified: bool
    fresh_angle: str
    production_burden: str
    risk_level: str
    notes: str
    sources: list[CaseSource] = field(default_factory=list)

    @property
    def recomputed_score(self) -> int:
        if self.novelty is None:
            raise ValueError(f"{self.case_id}: no score axes on poisoned-only rows")
        payload = {
            "novelty": self.novelty,
            "evidence": self.evidence,
            "decision_chain": self.decision_chain,
            "aftermath": self.aftermath,
            "packaging": self.packaging,
            "production_fit": self.production_fit,
            "safety": self.safety,
        }
        return candidate_score(payload)

    @property
    def recomputed_poison_count(self) -> int:
        return count_poison_signals(self)

    @property
    def is_youtube_verified(self) -> bool:
        return youtube_is_verified(self)

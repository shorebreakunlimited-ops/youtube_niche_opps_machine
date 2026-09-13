"""Case ledger models for poisoned vs candidate production research."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


VERDICTS = frozenset({"avoid", "maybe", "strong"})


@dataclass(frozen=True)
class CaseRecord:
    case_name: str
    working_title: str
    source_url: str
    jurisdiction: str
    incident_date: str
    release_date: str
    evidence_available: str
    has_bodycam: str
    has_interrogation: str
    has_911_audio: str
    has_court_records: str
    has_sentencing_or_outcome: str
    youtube_existing_video_count: str
    youtube_top_video_views: str
    covered_by_major_creator: str
    fresh_angle: str
    decision_chain_score: int
    production_burden: str
    risk_level: str
    candidate_score: int
    verdict: str
    notes: str
    ledger: str  # poisoned_cases | candidate_cases

    @property
    def is_launch_ready(self) -> bool:
        return self.ledger == "candidate_cases" and self.verdict == "strong"

    @property
    def has_usable_bodycam(self) -> bool:
        return self.has_bodycam.strip().lower() in {"yes", "partial"}


def compute_candidate_score(
    novelty: int,
    evidence: int,
    decision_chain: int,
    aftermath: int,
    packaging: int,
    production_fit: int,
    risk: int,
) -> int:
    """Brutal weighted first-pass score on 0-10 axes -> 0-100.

    Risk axis is inverted quality: higher risk score means safer/lower risk.
    """
    for name, value in {
        "novelty": novelty,
        "evidence": evidence,
        "decision_chain": decision_chain,
        "aftermath": aftermath,
        "packaging": packaging,
        "production_fit": production_fit,
        "risk": risk,
    }.items():
        if not 0 <= value <= 10:
            raise ValueError(f"{name} must be 0-10, got {value}")

    raw = (
        0.20 * novelty
        + 0.20 * evidence
        + 0.15 * decision_chain
        + 0.15 * aftermath
        + 0.15 * packaging
        + 0.10 * production_fit
        + 0.05 * risk
    )
    return int(round(raw * 10))


def verdict_from_score(score: int, poison_signal_count: int = 0) -> str:
    if poison_signal_count >= 2:
        return "avoid"
    if score >= 75:
        return "strong"
    if score >= 60:
        return "maybe"
    return "avoid"


def count_poison_signals(
    *,
    youtube_top_video_views: Optional[int],
    youtube_existing_video_count: Optional[int],
    covered_by_major_creator: str,
    name_famous: bool,
    heavily_clipped: bool,
    no_new_update: bool,
    heavily_politicized: bool,
    needs_psych_claims: bool,
    poor_footage: bool,
) -> list[str]:
    """Return triggered poison signal labels."""
    hits: list[str] = []
    if (youtube_existing_video_count or 0) >= 5 and (youtube_top_video_views or 0) >= 500_000:
        hits.append("5+_major_breakdowns_500k")
    if covered_by_major_creator.strip().lower() == "yes":
        hits.append("covered_by_major_creator")
    if name_famous:
        hits.append("name_driven_famous")
    if heavily_clipped:
        hits.append("heavily_clipped")
    if no_new_update:
        hits.append("no_new_update")
    if heavily_politicized:
        hits.append("heavily_politicized")
    if needs_psych_claims:
        hits.append("requires_psych_claims")
    if poor_footage:
        hits.append("poor_or_fragmented_footage")
    return hits

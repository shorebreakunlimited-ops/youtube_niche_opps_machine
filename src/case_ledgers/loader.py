"""Load and validate case ledger CSVs."""

from __future__ import annotations

from csv import DictReader
from pathlib import Path
from typing import Iterable, Optional, Sequence

from .models import CaseRecord
from .scoring import (
    LedgerValidationError,
    assert_score_and_verdict_match,
    count_poison_signals,
    verdict_from_score,
    youtube_is_verified,
)
from .sources import assert_strong_sources, load_case_sources

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "case_ledgers"

CANDIDATE_SCORE_FIELDS = (
    "novelty",
    "evidence",
    "decision_chain",
    "aftermath",
    "packaging",
    "production_fit",
    "safety",
    "candidate_score",
    "verdict",
    "poison_signal_count",
)

POISON_BOOL_FIELDS = (
    "poison_five_plus_over_500k",
    "poison_covered_by_major_creator",
    "poison_name_famous",
    "poison_heavily_clipped",
    "poison_no_new_update",
    "poison_heavily_politicized",
    "poison_needs_psych_claims",
    "poison_poor_footage",
)

REQUIRED_FIELDS = (
    "case_id",
    "case_name",
    "working_title",
    "verdict",
    "poison_signal_count",
    "verified_at",
    "search_queries",
    "videos_reviewed",
    "videos_over_500k",
    "top_video_views",
    "top_video_url",
    "major_creator_matches",
    "data_source",
    *POISON_BOOL_FIELDS,
)


def _parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _parse_optional_int(value: str) -> Optional[int]:
    text = (value or "").strip()
    if text == "" or text.lower() in {"unknown", "null", "none", "n/a"}:
        return None
    if "est" in text.lower():
        raise LedgerValidationError(f"Estimated values are not allowed: {value!r}")
    return int(float(text.replace(",", "")))


def _parse_optional_str(value: str) -> Optional[str]:
    text = (value or "").strip()
    if text == "" or text.lower() in {"unknown", "null", "none", "n/a"}:
        return None
    if text.lower().startswith("est"):
        raise LedgerValidationError(f"Estimated values are not allowed: {value!r}")
    return text


def _tri_state_bool(value: str) -> bool:
    text = (value or "").strip().lower()
    return text in {"1", "true", "yes", "y", "partial"}


def _poison_payload(row: dict[str, str]) -> dict:
    return {field: _parse_bool(row.get(field, "")) for field in POISON_BOOL_FIELDS}


def _youtube_fields(row: dict[str, str]) -> dict:
    videos_reviewed = _parse_optional_int(row.get("videos_reviewed", ""))
    videos_over_500k = _parse_optional_int(row.get("videos_over_500k", ""))
    data_source = (row.get("data_source") or "unknown").strip() or "unknown"
    explicit = row.get("youtube_verified", "").strip()
    if explicit:
        youtube_verified = _parse_bool(explicit)
    else:
        youtube_verified = data_source.lower() not in {"", "unknown", "none", "null"} and (
            videos_reviewed is not None and videos_over_500k is not None
        )
    return {
        "verified_at": _parse_optional_str(row.get("verified_at", "")),
        "search_queries": row.get("search_queries", "") or "",
        "videos_reviewed": videos_reviewed,
        "videos_over_500k": videos_over_500k,
        "top_video_views": _parse_optional_int(row.get("top_video_views", "")),
        "top_video_url": _parse_optional_str(row.get("top_video_url", "")),
        "major_creator_matches": row.get("major_creator_matches", "") or "",
        "data_source": data_source,
        "youtube_verified": youtube_verified,
    }


def _base_record(
    row: dict[str, str],
    *,
    ledger: str,
    sources_by_case: dict,
    novelty: Optional[int],
    evidence: Optional[int],
    decision_chain: Optional[int],
    aftermath: Optional[int],
    packaging: Optional[int],
    production_fit: Optional[int],
    safety: Optional[int],
    candidate_score_value: Optional[int],
) -> CaseRecord:
    relationship = (row.get("relationship") or "").strip().lower()
    parent_case_id = (row.get("parent_case_id") or "").strip()
    is_child = relationship == "child" or bool(parent_case_id)
    poison = _poison_payload(row)
    yt = _youtube_fields(row)
    poison_count = count_poison_signals(poison)
    stored_poison = int(row["poison_signal_count"])
    if stored_poison != poison_count:
        raise LedgerValidationError(
            f"{row['case_id']}: poison_signal_count {stored_poison} != calculated {poison_count}"
        )

    return CaseRecord(
        case_id=row["case_id"],
        ledger=ledger,
        case_name=row["case_name"],
        working_title=row["working_title"],
        jurisdiction=row.get("jurisdiction", ""),
        incident_date=row.get("incident_date", ""),
        release_date=row.get("release_date", ""),
        parent_case_id=parent_case_id,
        relationship=relationship or ("child" if is_child else "standalone"),
        is_child=is_child,
        evidence_available=row.get("evidence_available", ""),
        has_bodycam=_tri_state_bool(row.get("has_bodycam", "")),
        has_interrogation=_tri_state_bool(row.get("has_interrogation", "")),
        has_911_audio=_tri_state_bool(row.get("has_911_audio", "")),
        has_court_records=_tri_state_bool(row.get("has_court_records", "")),
        has_sentencing_or_outcome=_tri_state_bool(row.get("has_sentencing_or_outcome", "")),
        novelty=novelty,
        evidence=evidence,
        decision_chain=decision_chain,
        aftermath=aftermath,
        packaging=packaging,
        production_fit=production_fit,
        safety=safety,
        candidate_score=candidate_score_value,
        verdict=row["verdict"].strip().lower(),
        poison_signal_count=poison_count,
        fresh_angle=row.get("fresh_angle", ""),
        production_burden=row.get("production_burden", ""),
        risk_level=row.get("risk_level", ""),
        notes=row.get("notes", ""),
        sources=list(sources_by_case.get(row["case_id"], [])),
        **poison,
        **yt,
    )


def _load_candidate_row(row: dict[str, str], sources_by_case: dict) -> CaseRecord:
    missing = [f for f in CANDIDATE_SCORE_FIELDS if f not in row or str(row.get(f, "")).strip() == ""]
    if missing:
        raise LedgerValidationError(f"{row.get('case_id')}: missing candidate fields {missing}")

    score_payload = {
        "case_id": row["case_id"],
        "novelty": int(row["novelty"]),
        "evidence": int(row["evidence"]),
        "decision_chain": int(row["decision_chain"]),
        "aftermath": int(row["aftermath"]),
        "packaging": int(row["packaging"]),
        "production_fit": int(row["production_fit"]),
        "safety": int(row["safety"]),
        "candidate_score": int(row["candidate_score"]),
        "poison_signal_count": int(row["poison_signal_count"]),
        "verdict": row["verdict"],
        **_poison_payload(row),
    }
    assert_score_and_verdict_match(score_payload)

    record = _base_record(
        row,
        ledger="candidate_cases",
        sources_by_case=sources_by_case,
        novelty=int(row["novelty"]),
        evidence=int(row["evidence"]),
        decision_chain=int(row["decision_chain"]),
        aftermath=int(row["aftermath"]),
        packaging=int(row["packaging"]),
        production_fit=int(row["production_fit"]),
        safety=int(row["safety"]),
        candidate_score_value=int(row["candidate_score"]),
    )

    if record.verdict == "strong":
        assert_strong_sources(record.case_id, record.sources)
        if not youtube_is_verified(record):
            raise LedgerValidationError(
                f"{record.case_id}: strong verdict requires verified YouTube metrics (no unknown/est.)"
            )
        if record.is_child:
            raise LedgerValidationError(
                f"{record.case_id}: child/subcase cannot carry independent strong launch verdict"
            )
    return record


def _load_poisoned_row(row: dict[str, str], sources_by_case: dict) -> CaseRecord:
    record = _base_record(
        row,
        ledger="poisoned_cases",
        sources_by_case=sources_by_case,
        novelty=None,
        evidence=None,
        decision_chain=None,
        aftermath=None,
        packaging=None,
        production_fit=None,
        safety=None,
        candidate_score_value=None,
    )
    if record.poison_signal_count < 2:
        raise LedgerValidationError(
            f"{record.case_id}: poisoned ledger requires >=2 poison signals, got {record.poison_signal_count}"
        )
    if record.verdict != "avoid":
        raise LedgerValidationError(
            f"{record.case_id}: poisoned ledger verdict must be avoid, got {record.verdict!r}"
        )
    return record


def load_csv(path: Path, ledger: str, sources_by_case: dict) -> list[CaseRecord]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(DictReader(handle))
    if ledger == "candidate_cases":
        return [_load_candidate_row(row, sources_by_case) for row in rows]
    if ledger == "poisoned_cases":
        return [_load_poisoned_row(row, sources_by_case) for row in rows]
    raise LedgerValidationError(f"Unknown ledger {ledger!r}")


def load_ledger(name: str, data_dir: Path | None = None) -> list[CaseRecord]:
    root = data_dir or DEFAULT_DATA_DIR
    sources_by_case = load_case_sources(root / "case_sources.csv")
    if name in {"candidate_cases", "candidates"}:
        return load_csv(root / "candidate_cases.csv", "candidate_cases", sources_by_case)
    if name in {"poisoned_cases", "poisoned"}:
        return load_csv(root / "poisoned_cases.csv", "poisoned_cases", sources_by_case)
    raise LedgerValidationError(f"Unknown ledger name {name!r}")


def load_all(data_dir: Path | None = None) -> dict[str, list[CaseRecord]]:
    root = data_dir or DEFAULT_DATA_DIR
    sources_by_case = load_case_sources(root / "case_sources.csv")
    return {
        "candidate_cases": load_csv(root / "candidate_cases.csv", "candidate_cases", sources_by_case),
        "poisoned_cases": load_csv(root / "poisoned_cases.csv", "poisoned_cases", sources_by_case),
    }


def rank_candidates(
    *,
    min_score: int = 0,
    verdicts: Optional[Sequence[str]] = None,
    include_children: bool = False,
    data_dir: Path | None = None,
) -> list[CaseRecord]:
    rows = load_ledger("candidate_cases", data_dir=data_dir)
    out: list[CaseRecord] = []
    allowed = {v.lower() for v in verdicts} if verdicts else None
    for case in rows:
        if not include_children and case.is_child:
            continue
        if case.candidate_score is None or case.candidate_score < min_score:
            continue
        if allowed is not None and case.verdict not in allowed:
            continue
        out.append(case)
    return sorted(out, key=lambda c: (-(c.candidate_score or 0), c.case_id))


def launch_shortlist(
    candidates: Iterable[CaseRecord] | None = None,
    *,
    min_score: int = 75,
    max_poison: int = 1,
    exclude_children: bool = True,
    data_dir: Path | None = None,
) -> list[CaseRecord]:
    """Independent launch gate — does not trust CSV verdict alone."""
    rows = list(candidates) if candidates is not None else load_ledger("candidate_cases", data_dir=data_dir)
    out: list[CaseRecord] = []
    for case in rows:
        if exclude_children and case.is_child:
            continue
        poison_count = case.recomputed_poison_count
        if poison_count >= 2:
            continue
        if poison_count > max_poison:
            continue
        try:
            score = case.recomputed_score
        except ValueError:
            continue
        if score < min_score:
            continue
        if not case.is_youtube_verified:
            continue
        try:
            assert_strong_sources(case.case_id, case.sources)
        except LedgerValidationError:
            continue
        if verdict_from_score(score, poison_count) != "strong":
            continue
        # Final launch shortlist is intentionally empty until aftermath +
        # raw-footage acquisition are locked. Provisional research cases
        # (including former launch picks) are exposed via provisional_candidates().
        if "provisional" in (case.notes or "").lower():
            continue
        out.append(case)
    return sorted(out, key=lambda c: (-c.recomputed_score, c.case_id))


def provisional_candidates(
    candidates: Iterable[CaseRecord] | None = None,
    *,
    min_score: int = 60,
    max_poison: int = 1,
    exclude_children: bool = True,
    data_dir: Path | None = None,
) -> list[CaseRecord]:
    """Research slate of provisional candidates — not a final launch shortlist.

    Includes strong/maybe cases that survive basic poison and child filters.
    Final launch approval is intentionally separate and currently empty.
    """
    rows = list(candidates) if candidates is not None else load_ledger("candidate_cases", data_dir=data_dir)
    out: list[CaseRecord] = []
    for case in rows:
        if exclude_children and case.is_child:
            continue
        poison_count = case.recomputed_poison_count
        if poison_count >= 2 or poison_count > max_poison:
            continue
        try:
            score = case.recomputed_score
        except ValueError:
            continue
        if score < min_score:
            continue
        if case.verdict not in {"strong", "maybe"}:
            continue
        out.append(case)
    return sorted(out, key=lambda c: (-c.recomputed_score, c.case_id))

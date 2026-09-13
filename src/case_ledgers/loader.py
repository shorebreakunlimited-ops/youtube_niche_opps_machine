"""Load and query poisoned_cases / candidate_cases ledgers."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, List, Optional

from src.case_ledgers.models import CaseRecord

ROOT = Path(__file__).resolve().parents[2]
LEDGER_DIR = ROOT / "data" / "case_ledgers"

REQUIRED_FIELDS = [
    "case_name",
    "working_title",
    "source_url",
    "jurisdiction",
    "incident_date",
    "release_date",
    "evidence_available",
    "has_bodycam",
    "has_interrogation",
    "has_911_audio",
    "has_court_records",
    "has_sentencing_or_outcome",
    "youtube_existing_video_count",
    "youtube_top_video_views",
    "covered_by_major_creator",
    "fresh_angle",
    "decision_chain_score",
    "production_burden",
    "risk_level",
    "candidate_score",
    "verdict",
    "notes",
]


def _parse_int(value: str, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _row_to_record(row: dict, ledger: str) -> CaseRecord:
    missing = [f for f in REQUIRED_FIELDS if f not in row]
    if missing:
        raise ValueError(f"{ledger} missing fields: {missing}")
    return CaseRecord(
        case_name=row["case_name"].strip(),
        working_title=row["working_title"].strip(),
        source_url=row["source_url"].strip(),
        jurisdiction=row["jurisdiction"].strip(),
        incident_date=row["incident_date"].strip(),
        release_date=row["release_date"].strip(),
        evidence_available=row["evidence_available"].strip(),
        has_bodycam=row["has_bodycam"].strip(),
        has_interrogation=row["has_interrogation"].strip(),
        has_911_audio=row["has_911_audio"].strip(),
        has_court_records=row["has_court_records"].strip(),
        has_sentencing_or_outcome=row["has_sentencing_or_outcome"].strip(),
        youtube_existing_video_count=row["youtube_existing_video_count"].strip(),
        youtube_top_video_views=row["youtube_top_video_views"].strip(),
        covered_by_major_creator=row["covered_by_major_creator"].strip(),
        fresh_angle=row["fresh_angle"].strip(),
        decision_chain_score=_parse_int(row["decision_chain_score"]),
        production_burden=row["production_burden"].strip(),
        risk_level=row["risk_level"].strip(),
        candidate_score=_parse_int(row["candidate_score"]),
        verdict=row["verdict"].strip().lower(),
        notes=row["notes"].strip(),
        ledger=ledger,
    )


def load_ledger(name: str, ledger_dir: Optional[Path] = None) -> List[CaseRecord]:
    if name not in {"poisoned_cases", "candidate_cases"}:
        raise ValueError("name must be poisoned_cases or candidate_cases")
    path = (ledger_dir or LEDGER_DIR) / f"{name}.csv"
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [_row_to_record(row, name) for row in reader]


def load_all(ledger_dir: Optional[Path] = None) -> dict[str, List[CaseRecord]]:
    return {
        "poisoned_cases": load_ledger("poisoned_cases", ledger_dir),
        "candidate_cases": load_ledger("candidate_cases", ledger_dir),
    }


def rank_candidates(
    records: Optional[Iterable[CaseRecord]] = None,
    *,
    min_score: int = 0,
    verdicts: Optional[Iterable[str]] = None,
) -> List[CaseRecord]:
    rows = list(records) if records is not None else load_ledger("candidate_cases")
    allowed = set(verdicts) if verdicts is not None else {"strong", "maybe", "avoid"}
    filtered = [r for r in rows if r.candidate_score >= min_score and r.verdict in allowed]
    return sorted(filtered, key=lambda r: (-r.candidate_score, r.case_name.lower()))


def launch_shortlist(min_score: int = 75) -> List[CaseRecord]:
    return rank_candidates(min_score=min_score, verdicts=["strong"])

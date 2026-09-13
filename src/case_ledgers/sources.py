"""Load case_sources.csv keyed by case_id."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

from .models import CaseSource
from .scoring import LedgerValidationError, STRONG_SOURCE_TYPES, required_source_types_present

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCES_PATH = ROOT / "data" / "case_ledgers" / "case_sources.csv"

SOURCE_FIELDS = (
    "case_id",
    "source_type",
    "source_url",
    "source_title",
    "notes",
)


def load_case_sources(path: Optional[Path] = None) -> Dict[str, List[CaseSource]]:
    csv_path = path or DEFAULT_SOURCES_PATH
    grouped: Dict[str, List[CaseSource]] = defaultdict(list)
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in SOURCE_FIELDS if c not in (reader.fieldnames or [])]
        if missing:
            raise LedgerValidationError(f"case_sources.csv missing columns: {missing}")
        for row in reader:
            case_id = row["case_id"].strip()
            source_type = row["source_type"].strip().lower()
            source_url = row["source_url"].strip()
            if not case_id or not source_type or not source_url:
                raise LedgerValidationError(f"Invalid case_sources row: {row}")
            if not source_url.startswith("http"):
                raise LedgerValidationError(f"source_url must be http(s): {source_url}")
            grouped[case_id].append(
                CaseSource(
                    case_id=case_id,
                    source_type=source_type,
                    source_url=source_url,
                    source_title=row["source_title"].strip(),
                    notes=row.get("notes", "").strip(),
                )
            )
    return dict(grouped)


def assert_strong_sources(case_id: str, sources: List[CaseSource]) -> None:
    types = [s.source_type for s in sources]
    if not required_source_types_present(types):
        raise LedgerValidationError(
            f"{case_id} verdict=strong requires source types {STRONG_SOURCE_TYPES}; "
            f"has {sorted(set(types))}"
        )

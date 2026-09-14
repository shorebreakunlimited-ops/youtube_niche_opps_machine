"""Load case_sources.csv keyed by case_id with provenance validation."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Sequence
from urllib.parse import urlparse

from .models import CaseSource
from .scoring import LedgerValidationError, STRONG_SOURCE_TYPES, required_source_types_present

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCES_PATH = ROOT / "data" / "case_ledgers" / "case_sources.csv"

SOURCE_FIELDS = (
    "case_id",
    "source_type",
    "source_url",
    "source_title",
    "provenance_class",
    "acquisition_notes",
    "notes",
)

# bodycam_raw must be direct footage or a documented acquisition path — not a news article.
BODYCAM_RAW_PROVENANCE = frozenset(
    {
        "direct_video",
        "agency_release",
        "court_exhibit",
        "public_record_file",
        "acquisition_location",
    }
)

# court_police_record must be an official court/police document or docket.
COURT_POLICE_PROVENANCE = frozenset(
    {
        "court_docket",
        "police_document",
        "court_exhibit",
        "public_record_file",
        "agency_release",
    }
)

# Types that cannot share one secondary URL with each other.
NONSHAREABLE_SECONDARY_TYPES = frozenset(
    {
        "court_police_record",
        "independent_reporting",
        "legal_outcome",
    }
)

NEWS_HOST_HINTS = (
    "news",
    "times",
    "post",
    "tribune",
    "herald",
    "gazette",
    "journal",
    "komo",
    "wsbtv",
    "8newsnow",
    "reviewjournal",
    "cnn.com",
    "fox",
    "abc",
    "cbs",
    "nbc",
    "apnews",
    "reuters",
)


def _host(url: str) -> str:
    return (urlparse(url).netloc or "").lower()


def _looks_like_news_article(url: str, provenance_class: str) -> bool:
    if provenance_class in {"news_article", "secondary_article"}:
        return True
    host = _host(url)
    path = (urlparse(url).path or "").lower()
    if any(h in host for h in NEWS_HOST_HINTS) and provenance_class not in BODYCAM_RAW_PROVENANCE | COURT_POLICE_PROVENANCE:
        return True
    if "/news/" in path or "/local-news/" in path:
        return True
    return False


def validate_source_provenance(source: CaseSource) -> None:
    """Validate provenance rules for a single source row."""
    st = source.source_type.strip().lower()
    pc = (source.provenance_class or "").strip().lower()
    if not pc:
        raise LedgerValidationError(
            f"{source.case_id}/{st}: provenance_class is required"
        )

    if st == "bodycam_raw":
        if pc not in BODYCAM_RAW_PROVENANCE:
            raise LedgerValidationError(
                f"{source.case_id}/bodycam_raw: provenance_class={pc!r} must be one of "
                f"{sorted(BODYCAM_RAW_PROVENANCE)} (news articles are not sufficient)"
            )
        if _looks_like_news_article(source.source_url, pc) and pc not in {
            "direct_video",
            "agency_release",
            "court_exhibit",
            "public_record_file",
            "acquisition_location",
        }:
            raise LedgerValidationError(
                f"{source.case_id}/bodycam_raw: news article URL is not a valid bodycam_raw source"
            )
        if pc == "acquisition_location" and not (source.acquisition_notes or "").strip():
            raise LedgerValidationError(
                f"{source.case_id}/bodycam_raw: acquisition_location requires acquisition_notes"
            )

    if st == "court_police_record":
        if pc not in COURT_POLICE_PROVENANCE:
            raise LedgerValidationError(
                f"{source.case_id}/court_police_record: provenance_class={pc!r} must be one of "
                f"{sorted(COURT_POLICE_PROVENANCE)}"
            )
        host = _host(source.source_url)
        looks_gov_or_court = any(token in host for token in ("gov", "court", "uscourts", "state."))
        if pc in {"news_article", "secondary_article"} or (
            any(h in host for h in NEWS_HOST_HINTS) and not looks_gov_or_court
        ):
            raise LedgerValidationError(
                f"{source.case_id}/court_police_record: must point to an official court/police "
                "document or docket, not a secondary article"
            )


def assert_no_shared_secondary_urls(case_id: str, sources: Sequence[CaseSource]) -> None:
    """One secondary URL may not satisfy court, independent, and legal_outcome together."""
    url_to_types: dict[str, set[str]] = defaultdict(set)
    for source in sources:
        st = source.source_type.strip().lower()
        if st in NONSHAREABLE_SECONDARY_TYPES:
            url_to_types[source.source_url.strip()].add(st)
    for url, types in url_to_types.items():
        if len(types) > 1:
            raise LedgerValidationError(
                f"{case_id}: URL may not satisfy multiple of "
                f"{sorted(NONSHAREABLE_SECONDARY_TYPES)} simultaneously: {url} -> {sorted(types)}"
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
            source = CaseSource(
                case_id=case_id,
                source_type=source_type,
                source_url=source_url,
                source_title=row["source_title"].strip(),
                provenance_class=(row.get("provenance_class") or "").strip().lower(),
                acquisition_notes=(row.get("acquisition_notes") or "").strip(),
                notes=row.get("notes", "").strip(),
            )
            validate_source_provenance(source)
            grouped[case_id].append(source)
    for case_id, sources in grouped.items():
        assert_no_shared_secondary_urls(case_id, sources)
    return dict(grouped)


def assert_strong_sources(case_id: str, sources: List[CaseSource]) -> None:
    types = [s.source_type for s in sources]
    if not required_source_types_present(types):
        raise LedgerValidationError(
            f"{case_id} verdict=strong requires source types {STRONG_SOURCE_TYPES}; "
            f"has {sorted(set(types))}"
        )
    for source in sources:
        validate_source_provenance(source)
    assert_no_shared_secondary_urls(case_id, sources)

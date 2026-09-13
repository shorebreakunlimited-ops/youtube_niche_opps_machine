"""Tests for reproducible case-ledger scoring, poison rules, and launch gates."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from src.case_ledgers.loader import (
    launch_shortlist,
    load_all,
    load_csv,
    rank_candidates,
)
from src.case_ledgers.models import CaseRecord, CaseSource
from src.case_ledgers.scoring import (
    LedgerValidationError,
    assert_score_and_verdict_match,
    candidate_score,
    count_poison_signals,
    verdict_from_score,
    youtube_is_verified,
)
from src.case_ledgers.sources import assert_strong_sources, load_case_sources


DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "case_ledgers"


def _axes(**overrides):
    base = {
        "novelty": 9,
        "evidence": 9,
        "decision_chain": 9,
        "aftermath": 9,
        "packaging": 9,
        "production_fit": 8,
        "safety": 8,
    }
    base.update(overrides)
    return base


def _empty_poison(**overrides):
    base = {
        "poison_five_plus_over_500k": False,
        "poison_covered_by_major_creator": False,
        "poison_name_famous": False,
        "poison_heavily_clipped": False,
        "poison_no_new_update": False,
        "poison_heavily_politicized": False,
        "poison_needs_psych_claims": False,
        "poison_poor_footage": False,
    }
    base.update(overrides)
    return base


def _strong_sources(case_id: str = "X001") -> list[CaseSource]:
    return [
        CaseSource(case_id, "bodycam_raw", "https://example.com/bodycam", "bodycam"),
        CaseSource(case_id, "court_police_record", "https://example.com/court", "court"),
        CaseSource(case_id, "independent_reporting", "https://example.com/news", "news"),
        CaseSource(case_id, "legal_outcome", "https://example.com/outcome", "outcome"),
    ]


def test_score_recomputation_matches_formula():
    axes = _axes()
    score = candidate_score(axes)
    assert score == 88
    assert verdict_from_score(score, 0) == "strong"
    assert verdict_from_score(70, 0) == "maybe"
    assert verdict_from_score(50, 0) == "avoid"


def test_score_and_verdict_mismatch_rejected():
    row = {
        "case_id": "X001",
        **_axes(),
        **_empty_poison(),
        "candidate_score": 99,
        "poison_signal_count": 0,
        "verdict": "strong",
    }
    with pytest.raises(LedgerValidationError, match="candidate_score"):
        assert_score_and_verdict_match(row)

    row["candidate_score"] = candidate_score(row)
    row["verdict"] = "maybe"
    with pytest.raises(LedgerValidationError, match="verdict"):
        assert_score_and_verdict_match(row)


def test_automatic_poison_disqualification():
    row = {
        "case_id": "X002",
        **_axes(),
        **_empty_poison(
            poison_five_plus_over_500k=True,
            poison_covered_by_major_creator=True,
        ),
    }
    poison = count_poison_signals(row)
    assert poison == 2
    score = candidate_score(row)
    assert score >= 75
    assert verdict_from_score(score, poison) == "avoid"

    row["candidate_score"] = score
    row["poison_signal_count"] = poison
    row["verdict"] = "strong"
    with pytest.raises(LedgerValidationError):
        assert_score_and_verdict_match(row)

    poisoned_strongish = CaseRecord(
        case_id="X002",
        ledger="candidate_cases",
        case_name="Poisoned Strongish",
        working_title="Should Never Launch",
        jurisdiction="",
        incident_date="",
        release_date="",
        parent_case_id="",
        relationship="standalone",
        is_child=False,
        evidence_available="bodycam",
        has_bodycam=True,
        has_interrogation=False,
        has_911_audio=False,
        has_court_records=True,
        has_sentencing_or_outcome=True,
        novelty=9,
        evidence=9,
        decision_chain=9,
        aftermath=9,
        packaging=9,
        production_fit=8,
        safety=8,
        candidate_score=88,
        verdict="strong",
        poison_signal_count=2,
        verified_at="2026-09-13T00:00:00Z",
        search_queries="test",
        videos_reviewed=1,
        videos_over_500k=0,
        top_video_views=1000,
        top_video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        major_creator_matches="",
        data_source="youtube_data_api_v3",
        youtube_verified=True,
        fresh_angle="x",
        production_burden="low",
        risk_level="low",
        notes="",
        sources=_strong_sources("X002"),
        **_empty_poison(
            poison_five_plus_over_500k=True,
            poison_covered_by_major_creator=True,
        ),
    )
    assert launch_shortlist([poisoned_strongish]) == []


def test_missing_source_rejection_for_strong_candidates(tmp_path: Path):
    with (DATA_DIR / "candidate_cases.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0].keys())
    c001 = [r for r in rows if r["case_id"] == "C001"][0]
    cand_path = tmp_path / "candidate_cases.csv"
    with cand_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(c001)

    empty_sources = tmp_path / "case_sources.csv"
    with empty_sources.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["case_id", "source_type", "source_url", "source_title", "notes"],
        )
        writer.writeheader()

    empty_map = load_case_sources(empty_sources)
    with pytest.raises(LedgerValidationError, match="source types"):
        load_csv(cand_path, "candidate_cases", empty_map)

    with pytest.raises(LedgerValidationError, match="source types"):
        assert_strong_sources("C001", [])


def test_unknown_youtube_cannot_produce_launch_ready_status():
    unknown_yt = CaseRecord(
        case_id="X003",
        ledger="candidate_cases",
        case_name="Unknown YT",
        working_title="Looks Strong But Unverified",
        jurisdiction="",
        incident_date="",
        release_date="",
        parent_case_id="",
        relationship="standalone",
        is_child=False,
        evidence_available="bodycam",
        has_bodycam=True,
        has_interrogation=False,
        has_911_audio=False,
        has_court_records=True,
        has_sentencing_or_outcome=True,
        novelty=9,
        evidence=9,
        decision_chain=9,
        aftermath=9,
        packaging=9,
        production_fit=8,
        safety=8,
        candidate_score=88,
        verdict="strong",
        poison_signal_count=0,
        verified_at=None,
        search_queries="",
        videos_reviewed=None,
        videos_over_500k=None,
        top_video_views=None,
        top_video_url=None,
        major_creator_matches="",
        data_source="unknown",
        youtube_verified=False,
        fresh_angle="x",
        production_burden="low",
        risk_level="low",
        notes="",
        sources=_strong_sources("X003"),
        **_empty_poison(),
    )
    assert youtube_is_verified(unknown_yt) is False
    assert launch_shortlist([unknown_yt]) == []


def test_duplicate_parent_child_handling():
    data = load_all()
    candidates = {c.case_id: c for c in data["candidate_cases"]}
    assert candidates["C003"].is_child is True
    assert candidates["C003"].parent_case_id == "C002"
    assert candidates["C003"].verdict != "strong"

    shortlist_ids = [c.case_id for c in launch_shortlist()]
    assert "C002" in shortlist_ids
    assert "C003" not in shortlist_ids

    ranked_without_children = rank_candidates()
    assert all(not c.is_child for c in ranked_without_children)
    ranked_with_children = rank_candidates(include_children=True)
    assert any(c.case_id == "C003" for c in ranked_with_children)


def test_ledgers_load_and_poisoned_are_avoid():
    data = load_all()
    assert len(data["candidate_cases"]) >= 5
    assert len(data["poisoned_cases"]) >= 10
    for row in data["poisoned_cases"]:
        assert row.verdict == "avoid"
        assert row.poison_signal_count >= 2
        assert row.recomputed_poison_count == row.poison_signal_count

    for row in data["candidate_cases"]:
        assert row.recomputed_score == row.candidate_score
        assert (
            verdict_from_score(row.recomputed_score, row.recomputed_poison_count)
            == row.verdict
        )


def test_launch_shortlist_requires_verified_metrics_and_sources():
    shortlist = launch_shortlist()
    assert {c.case_id for c in shortlist} == {"C001", "C002", "C004"}
    for case in shortlist:
        assert case.youtube_verified is True
        assert case.data_source != "unknown"
        assert case.videos_reviewed is not None
        assert case.videos_over_500k is not None
        assert case.poison_signal_count < 2
        assert case.is_child is False
        types = {s.source_type for s in case.sources}
        assert types >= {
            "bodycam_raw",
            "court_police_record",
            "independent_reporting",
            "legal_outcome",
        }


def test_estimated_youtube_values_rejected(tmp_path: Path):
    with (DATA_DIR / "candidate_cases.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0].keys())
    c004 = dict([r for r in rows if r["case_id"] == "C004"][0])
    c004["top_video_views"] = "est. 3000"
    path = tmp_path / "candidate_cases.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(c004)
    sources_by_case = load_case_sources(DATA_DIR / "case_sources.csv")
    with pytest.raises(LedgerValidationError, match="Estimated|est"):
        load_csv(path, "candidate_cases", sources_by_case)

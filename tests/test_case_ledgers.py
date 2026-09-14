"""Tests for reproducible case-ledger scoring, poison rules, sources, and YouTube audits."""

from __future__ import annotations

import csv
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.case_ledgers.loader import (
    launch_shortlist,
    load_all,
    load_csv,
    provisional_candidates,
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
from src.case_ledgers.sources import (
    assert_strong_sources,
    load_case_sources,
    validate_source_provenance,
)
from src.case_ledgers.youtube_metrics import (
    YouTubeAuditError,
    audit_case_on_youtube,
    mock_youtube_audit_result,
)
from src.collectors.youtube_client import YouTubeClient


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
        CaseSource(
            case_id,
            "bodycam_raw",
            "https://www.youtube.com/watch?v=aaaaaaaaaaa",
            "direct bodycam upload",
            provenance_class="direct_video",
        ),
        CaseSource(
            case_id,
            "court_police_record",
            "https://courts.example.gov/docket/123",
            "official docket",
            provenance_class="court_docket",
        ),
        CaseSource(
            case_id,
            "independent_reporting",
            "https://news.example.com/story-a",
            "news a",
            provenance_class="news_article",
        ),
        CaseSource(
            case_id,
            "legal_outcome",
            "https://news.example.com/story-b",
            "news b outcome",
            provenance_class="news_article",
        ),
    ]


def test_score_recomputation_matches_formula():
    score = candidate_score(_axes())
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
    assert verdict_from_score(score, poison) == "avoid"
    row["candidate_score"] = score
    row["poison_signal_count"] = poison
    row["verdict"] = "strong"
    with pytest.raises(LedgerValidationError):
        assert_score_and_verdict_match(row)


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
            fieldnames=[
                "case_id",
                "source_type",
                "source_url",
                "source_title",
                "provenance_class",
                "acquisition_notes",
                "notes",
            ],
        )
        writer.writeheader()

    empty_map = load_case_sources(empty_sources)
    with pytest.raises(LedgerValidationError, match="source types"):
        load_csv(cand_path, "candidate_cases", empty_map)


def test_bodycam_raw_rejects_news_article_provenance():
    bad = CaseSource(
        "X010",
        "bodycam_raw",
        "https://komonews.com/news/local/example",
        "news writeup",
        provenance_class="news_article",
    )
    with pytest.raises(LedgerValidationError, match="bodycam_raw"):
        validate_source_provenance(bad)


def test_court_police_record_rejects_news_article_provenance():
    bad = CaseSource(
        "X011",
        "court_police_record",
        "https://www.seattletimes.com/seattle-news/example",
        "news writeup",
        provenance_class="news_article",
    )
    with pytest.raises(LedgerValidationError, match="court_police_record"):
        validate_source_provenance(bad)


def test_shared_secondary_url_rejected_for_strong_sources():
    shared = "https://courts.example.gov/docket/same-story"
    sources = [
        CaseSource("X012", "bodycam_raw", "https://www.youtube.com/watch?v=bbbbbbbbbbb", "vid", provenance_class="direct_video"),
        CaseSource("X012", "court_police_record", shared, "docket as court", provenance_class="court_docket"),
        CaseSource("X012", "independent_reporting", shared, "same url as reporting", provenance_class="news_article"),
        CaseSource("X012", "legal_outcome", shared, "same url as outcome", provenance_class="news_article"),
    ]
    with pytest.raises(LedgerValidationError, match="multiple"):
        assert_strong_sources("X012", sources)


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


def test_mock_data_source_is_not_youtube_verified():
    row = {
        "data_source": "mock",
        "videos_reviewed": 3,
        "videos_over_500k": 0,
        "verified_at": "2026-09-13T23:20:00Z",
        "youtube_verified": True,
    }
    assert youtube_is_verified(row) is False


def test_duplicate_parent_child_handling():
    data = load_all()
    candidates = {c.case_id: c for c in data["candidate_cases"]}
    assert candidates["C003"].is_child is True
    assert candidates["C003"].parent_case_id == "C002"
    assert candidates["C003"].verdict != "strong"

    provisional_ids = [c.case_id for c in provisional_candidates()]
    assert "C002" in provisional_ids
    assert "C003" not in provisional_ids

    ranked_with_children = rank_candidates(include_children=True)
    assert any(c.case_id == "C003" for c in ranked_with_children)


def test_c004_demoted_to_maybe_and_not_final_launch():
    data = load_all()
    by_id = {c.case_id: c for c in data["candidate_cases"]}
    assert by_id["C004"].verdict == "maybe"
    assert by_id["C004"].candidate_score < 75
    assert "C004" in {c.case_id for c in provisional_candidates()}
    assert launch_shortlist() == []


def test_provisional_not_final_launch_shortlist():
    """C001/C002/C004 are provisional research candidates, not a final launch slate."""
    provisional_ids = {c.case_id for c in provisional_candidates()}
    assert {"C001", "C002", "C004"} <= provisional_ids
    assert launch_shortlist() == []


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


def test_audit_rejects_missing_api_key(monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    client = YouTubeClient(api_key="", use_mock=False)
    # empty key forces use_mock True inside client
    assert client.use_mock is True
    with pytest.raises(YouTubeAuditError, match="use_mock|API key|live"):
        audit_case_on_youtube(["test query"], ["test"], client=client)


def test_audit_rejects_explicit_mock_mode():
    client = YouTubeClient(api_key="fake-key", use_mock=True)
    assert client.use_mock is True
    with pytest.raises(YouTubeAuditError, match="use_mock"):
        audit_case_on_youtube(["test query"], ["test"], client=client)


def test_audit_api_error_does_not_fallback_to_mock():
    client = YouTubeClient(api_key="fake-key", use_mock=False)
    assert client.use_mock is False

    with patch.object(client, "search_videos", side_effect=RuntimeError("YouTube search API error: 403")):
        with pytest.raises(YouTubeAuditError, match="YouTube audit failed"):
            audit_case_on_youtube(["test query"], ["test"], client=client)


def test_audit_live_client_success_sets_verified_fields():
    client = YouTubeClient(api_key="fake-key", use_mock=False)
    video = MagicMock()
    video.video_id = "abc123xyz00"
    video.title = "Howard McCay bodycam welfare check"
    video.channel_id = "ch1"
    video.views = 12000
    channel = MagicMock()
    channel.title = "Local News"

    with patch.object(client, "search_videos", return_value=([video], {"ch1": channel}, [])):
        result = audit_case_on_youtube(
            ["Howard McCay bodycam"],
            ["McCay", "bodycam"],
            client=client,
        )
    assert result.data_source == "youtube_data_api_v3"
    assert result.youtube_verified is True
    assert result.verified_at
    assert result.videos_reviewed == 1
    assert result.top_video_views == 12000


def test_mock_audit_helper_never_marks_verified():
    result = mock_youtube_audit_result(["q"], videos_reviewed=2, videos_over_500k=1)
    assert result.data_source == "mock"
    assert result.youtube_verified is False
    assert result.verified_at is None

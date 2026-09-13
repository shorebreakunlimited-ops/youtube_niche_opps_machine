"""Tests for the two-ledger case research system."""

from __future__ import annotations

from src.case_ledgers.loader import REQUIRED_FIELDS, launch_shortlist, load_all, load_ledger, rank_candidates
from src.case_ledgers.models import compute_candidate_score, count_poison_signals, verdict_from_score


def test_ledgers_load_with_required_fields():
    data = load_all()
    assert len(data["poisoned_cases"]) >= 10
    assert len(data["candidate_cases"]) >= 5
    for ledger, rows in data.items():
        for row in rows:
            assert row.verdict in {"avoid", "maybe", "strong"}
            assert row.case_name
            assert row.working_title
            assert row.source_url.startswith("http")
            assert row.ledger == ledger


def test_poisoned_cases_are_all_avoid():
    rows = load_ledger("poisoned_cases")
    assert all(r.verdict == "avoid" for r in rows)
    names = " ".join(r.case_name.lower() for r in rows)
    assert "watts" in names
    assert "floyd" in names or "chauvin" in names
    assert "petito" in names


def test_candidates_ranked_strong_first():
    ranked = rank_candidates()
    assert ranked[0].candidate_score >= ranked[-1].candidate_score
    strong = [r for r in ranked if r.verdict == "strong"]
    assert strong, "expected at least one strong launch candidate"
    assert all(r.has_usable_bodycam for r in strong)
    assert all(r.covered_by_major_creator.lower() != "yes" for r in strong)


def test_launch_shortlist_excludes_famous_names():
    shortlist = launch_shortlist()
    blob = " ".join(r.case_name.lower() for r in shortlist)
    for banned in ["watts", "boone", "brooks", "floyd", "petito", "timberlake", "franke"]:
        assert banned not in blob
    assert shortlist, "expected a non-empty launch shortlist"


def test_scoring_helpers():
    score = compute_candidate_score(
        novelty=9,
        evidence=9,
        decision_chain=9,
        aftermath=9,
        packaging=9,
        production_fit=8,
        risk=8,
    )
    assert score >= 75
    assert verdict_from_score(score) == "strong"
    assert verdict_from_score(50) == "avoid"
    assert verdict_from_score(90, poison_signal_count=2) == "avoid"

    hits = count_poison_signals(
        youtube_top_video_views=2_000_000,
        youtube_existing_video_count=8,
        covered_by_major_creator="yes",
        name_famous=True,
        heavily_clipped=True,
        no_new_update=True,
        heavily_politicized=False,
        needs_psych_claims=False,
        poor_footage=False,
    )
    assert len(hits) >= 2


def test_required_fields_match_schema_contract():
    assert "fresh_angle" in REQUIRED_FIELDS
    assert "has_sentencing_or_outcome" in REQUIRED_FIELDS
    assert "source_url" in REQUIRED_FIELDS
    assert "verdict" in REQUIRED_FIELDS

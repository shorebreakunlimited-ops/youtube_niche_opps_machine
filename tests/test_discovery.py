"""Tests for Mode A discovery expansion, deduplication, and pure market ranking."""

from src.collectors.browseract_adapter import BrowserActAdapter
from src.collectors.youtube_client import YouTubeClient
from src.discovery.niche_extractor import NicheExtractor
from src.discovery.query_expander import QueryExpander
from src.discovery.semantic_deduper import SemanticDeduper
from src.storage.cache import SQLiteCache
from src.storage.database import NicheDatabase
from src.validation.niche_validator import NicheValidator


def test_query_expander_axes_and_probes():
    expander = QueryExpander()
    queries = expander.expand_seed_across_15_axes("docker")
    assert len(queries) >= 15
    axes_seen = {q["axis_id"] for q in queries}
    assert len(axes_seen) == 15

    alphabet = expander.generate_autocomplete_alphabet_probes("docker")
    assert len(alphabet) == 26
    assert alphabet[0] == "docker a"
    assert alphabet[-1] == "docker z"

    questions = expander.generate_interrogative_probes("docker")
    assert len(questions) >= 5


def test_semantic_deduper():
    candidates = [
        "python for beginners",
        "python for beginners tutorial",  # High token overlap
        "docker setup",
        "python for beginners",  # Duplicate
        "docker setup tutorial",  # High overlap
        "kubernetes clean architecture",
    ]
    deduped = SemanticDeduper.deduplicate_candidates(candidates, similarity_threshold=0.60)
    assert len(deduped) < len(candidates)
    assert "python for beginners" in deduped
    assert "kubernetes clean architecture" in deduped


def test_discovery_ranks_on_pure_content_opportunity_not_creator_adjusted(tmp_path):
    """Verify Discovery Leaderboard strictly ranks on Content Opportunity + Confidence gating."""
    cache = SQLiteCache(db_path=str(tmp_path / "cache.db"))
    db = NicheDatabase(db_path=str(tmp_path / "niche.db"))

    yt_client = YouTubeClient(cache=cache, db=db, use_mock=True)
    browser = BrowserActAdapter(cache=cache)
    validator = NicheValidator(youtube_client=yt_client, browser_adapter=browser, db=db, cache=cache)

    extractor = NicheExtractor(validator=validator)

    leaderboard = extractor.discover_subniches(
        seed_topic="agentic workflows",
        max_candidates=4,
        min_confidence_gate=10.0,
        creator_profile={"production": {"research_burden": 25.0, "camera_footage_need": 25.0}},
    )

    assert len(leaderboard) >= 1
    # Verify ranking monotonicity by content_opportunity_score
    co_scores = [entry["content_opportunity_score"] for entry in leaderboard]
    assert co_scores == sorted(co_scores, reverse=True)

    # Verify that creator_adjusted_opportunity is reported but not used to disrupt ranking
    for entry in leaderboard:
        assert "creator_adjusted_opportunity" in entry
        assert "content_opportunity_score" in entry
        assert entry["creator_adjusted_opportunity"] <= entry["content_opportunity_score"]

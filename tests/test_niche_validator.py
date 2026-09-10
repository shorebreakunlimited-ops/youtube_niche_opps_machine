"""Tests for Mode B Deep Niche Validator."""

from src.collectors.browseract_adapter import BrowserActAdapter
from src.collectors.youtube_client import YouTubeClient
from src.storage.cache import SQLiteCache
from src.storage.database import NicheDatabase
from src.validation.niche_validator import NicheValidator


def test_niche_validator_mock_end_to_end(tmp_path):
    cache = SQLiteCache(db_path=str(tmp_path / "cache.db"))
    db = NicheDatabase(db_path=str(tmp_path / "niche.db"))

    yt_client = YouTubeClient(cache=cache, db=db, use_mock=True)
    browser = BrowserActAdapter(cache=cache)

    validator = NicheValidator(
        youtube_client=yt_client,
        browser_adapter=browser,
        db=db,
        cache=cache,
    )

    result = validator.validate_niche("autonomous ai agents", max_videos=20)

    # 1. Decoupled scores check
    assert 0.0 <= result.content_opportunity_score <= 100.0
    assert 0.0 <= result.creator_adjusted_opportunity <= 100.0
    assert 0.0 <= result.commercial_attractiveness_score <= 100.0
    assert 0.0 <= result.production_feasibility <= 100.0
    assert 0.0 <= result.rights_safety <= 100.0
    assert 0.0 <= result.confidence_score <= 100.0

    # 2. Check relationship: Creator-adjusted opportunity <= Content opportunity
    assert result.creator_adjusted_opportunity <= result.content_opportunity_score

    # 3. Check recommendation is valid deterministic state
    valid_states = {
        "STRONG OPPORTUNITY",
        "PROMISING",
        "HIGH POTENTIAL (RISKY)",
        "SATURATED",
        "WEAK DEMAND",
        "VIRAL OUTLIER",
        "HIGH RIGHTS RISK",
        "HIGH PRODUCTION RISK",
        "INSUFFICIENT EVIDENCE",
        "WATCHLIST",
    }
    assert result.recommendation in valid_states

    # 4. Check breakdown items
    assert len(result.reasoning) > 0
    assert len(result.top_competitors) > 0
    assert len(result.video_ideas) > 0
    assert result.sample_size == 20

    # 5. Check database snapshot persistence
    history = db.get_validation_history(result.niche_id)
    assert len(history) == 1
    assert history[0]["content_opportunity_score"] == result.content_opportunity_score

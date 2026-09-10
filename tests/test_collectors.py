"""Tests for YouTube Data API client and BrowserAct observation adapter."""

import pytest
from src.collectors.browseract_adapter import BrowserActAdapter
from src.collectors.youtube_client import QuotaExceededError, YouTubeClient
from src.storage.cache import SQLiteCache
from src.storage.database import NicheDatabase


def test_youtube_client_mock_search_and_quota_accounting(tmp_path):
    cache = SQLiteCache(db_path=str(tmp_path / "cache.db"))
    db = NicheDatabase(db_path=str(tmp_path / "niche.db"))

    client = YouTubeClient(
        cache=cache,
        db=db,
        search_list_daily_limit=5,
        videos_batch_daily_limit=20,
        use_mock=True,
    )

    status = client.get_quota_status()
    assert status["search_list"]["used"] == 0
    assert status["search_list"]["limit"] == 5
    assert status["mock_mode"] is True

    # Perform mock search
    videos, channels, observations = client.search_videos("cursor ai workflows", max_results=15)
    assert len(videos) == 15
    assert len(channels) > 0
    assert len(observations) == 15

    # Check database persistence
    db_videos = db.get_videos_by_channel(list(channels.keys())[0])
    assert len(db_videos) >= 1

    # Check cache hit on repeat call
    videos_cached, channels_cached, _ = client.search_videos("cursor ai workflows", max_results=15)
    assert len(videos_cached) == 15


def test_youtube_client_quota_exceeded_error():
    client = YouTubeClient(
        search_list_daily_limit=2,
        use_mock=False,
        api_key="dummy_key",
    )

    # Manually consume quota
    client._search_calls_used = 2
    with pytest.raises(QuotaExceededError):
        client._consume_search_quota()


def test_youtube_client_duration_parsing():
    assert YouTubeClient._parse_iso_duration("PT1H2M10S") == 3730
    assert YouTubeClient._parse_iso_duration("PT4M30S") == 270
    assert YouTubeClient._parse_iso_duration("PT55S") == 55
    assert YouTubeClient._parse_iso_duration("P1DT2H") == 93600
    assert YouTubeClient._parse_iso_duration("invalid") == 0


def test_browseract_adapter_suggestions(tmp_path):
    cache = SQLiteCache(db_path=str(tmp_path / "cache.db"))
    adapter = BrowserActAdapter(cache=cache)

    suggestions = adapter.get_autocomplete_suggestions("python tutorial")
    assert isinstance(suggestions, list)
    assert len(suggestions) > 0

    tree = adapter.expand_autocomplete_tree("python", prefixes=["how to", "best"], include_alphabet=False)
    assert "_seed" in tree
    assert "how to" in tree
    assert "best" in tree

    layout = adapter.observe_page_layout("python tutorial")
    assert "adapter" in layout

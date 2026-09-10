"""Unit tests for normalized SQLite storage and provenance tracking."""

from datetime import datetime, timezone, timedelta
import pytest
from src.models import (
    Channel,
    ChannelMetricSnapshot,
    Niche,
    NicheVideoDiscovery,
    NicheVideoMembership,
    SearchRankObservation,
    ValidationResult,
    Video,
    VideoMetricSnapshot,
)
from src.storage.database import Database
from src.storage.cache import RequestCache


@pytest.fixture
def db():
    database = Database(db_path=":memory:")
    yield database
    database.close()


def test_niche_persistence(db):
    niche = Niche(
        niche_id="niche-123",
        name="Engineering Disasters",
        market="Technology",
        subniche="Failures",
        format="Documentary",
    )
    db.save_niche(niche)

    retrieved = db.get_niche("niche-123")
    assert retrieved is not None
    assert retrieved.name == "Engineering Disasters"
    assert retrieved.market == "Technology"


def test_split_provenance_and_memberships(db):
    """Test that split provenance preserves multiple discovery paths without overwriting."""
    niche = Niche(niche_id="n1", name="Dam Failures")
    db.save_niche(niche)

    channel = Channel(channel_id="c1", title="Disaster Analytics")
    db.save_channel(channel)

    video = Video(
        video_id="v1",
        channel_id="c1",
        title="Vajont Dam Disaster",
        published_at="2026-01-01T00:00:00Z",
        views=150000,
    )
    db.save_video(video)

    # 1. Record Membership
    mem = NicheVideoMembership(
        niche_id="n1",
        video_id="v1",
        relevance_score=0.95,
        primary_cluster_id="cluster_hydraulic",
    )
    db.record_membership(mem)

    # 2. Record Multiple Discoveries for the same video in the same niche
    d1 = NicheVideoDiscovery(
        run_id="run-001",
        niche_id="n1",
        video_id="v1",
        discovery_method="seed_search",
        originating_query="dam disaster documentary",
        rank_position=1,
    )
    d2 = NicheVideoDiscovery(
        run_id="run-002",
        niche_id="n1",
        video_id="v1",
        discovery_method="suggest_expansion",
        originating_query="worst dam failures in history",
        rank_position=3,
    )
    id1 = db.record_discovery(d1)
    id2 = db.record_discovery(d2)

    assert id1 != id2

    # Check database rows
    cur = db.conn.cursor()
    cur.execute("SELECT COUNT(*) FROM niche_video_discoveries WHERE video_id = 'v1'")
    count = cur.fetchone()[0]
    assert count == 2


def test_normalized_snapshots_and_delta_velocity(db):
    """Test video_metric_snapshots and real snapshot delta velocity computation."""
    c = Channel(channel_id="c1", title="Test Channel")
    db.save_channel(c)
    v = Video(
        video_id="v1",
        channel_id="c1",
        title="Test Video",
        published_at="2026-01-01T00:00:00Z",
        views=1000,
    )
    db.save_video(v)

    # Initial snapshot at t1
    t1 = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    s1 = VideoMetricSnapshot(video_id="v1", observed_at=t1, views=10000, likes=500)
    db.save_video_snapshot(s1)

    # Single snapshot cannot compute delta velocity
    assert db.compute_snapshot_delta_velocity("v1") is None

    # Second snapshot at t2 (10 days later, +5,000 views)
    t2 = t1 + timedelta(days=10)
    s2 = VideoMetricSnapshot(video_id="v1", observed_at=t2, views=15000, likes=750)
    db.save_video_snapshot(s2)

    # Delta velocity = (15000 - 10000) / 10 = 500 views/day
    vel = db.compute_snapshot_delta_velocity("v1")
    assert vel is not None
    assert pytest.approx(vel, 0.1) == 500.0


def test_search_rank_observations(db):
    """Test recording of controlled, reproducible search rank positions."""
    obs = SearchRankObservation(
        run_id="run-101",
        query="bridge collapses",
        video_id="vid-xyz",
        rank_position=4,
        region="US",
        language="en",
        order_param="relevance",
        device_context="desktop",
        search_context="browser_stealth",
    )
    row_id = db.record_search_rank(obs)
    assert row_id > 0

    cur = db.conn.cursor()
    cur.execute("SELECT * FROM search_rank_observations WHERE id = ?", (row_id,))
    row = dict(cur.fetchone())
    assert row["rank_position"] == 4
    assert row["search_context"] == "browser_stealth"


def test_validation_snapshots_and_watchlist(db):
    """Test validation snapshot persistence and watchlist tracking."""
    niche = Niche(niche_id="n-99", name="Ancient City Reconstructions")
    db.save_niche(niche)

    res = ValidationResult(
        niche_id="n-99",
        niche_name="Ancient City Reconstructions",
        content_opportunity_score=82.5,
        creator_adjusted_opportunity=78.0,
        commercial_attractiveness_score=65.0,
        production_feasibility=70.0,
        rights_safety=88.0,
        confidence_score=75.0,
        demand_score=80.0,
        supply_scarcity=76.0,
        acceleration_score=84.0,
        breakout_score=85.0,
        repeatability_score=90.0,
        durability_score=80.0,
        outlier_risk_score=5.0,
        production_risk_score=30.0,
        rights_risk_score=12.0,
        recommendation="STRONG OPPORTUNITY",
    )
    snap_id = db.save_validation_snapshot(res)
    assert snap_id > 0

    history = db.get_validation_history("n-99")
    assert len(history) == 1
    assert history[0]["recommendation"] == "STRONG OPPORTUNITY"

    # Watchlist
    db.add_to_watchlist("n-99", threshold=80.0)
    wl = db.get_watchlist()
    assert len(wl) == 1
    assert wl[0]["niche_name"] == "Ancient City Reconstructions"


def test_request_cache():
    cache = RequestCache(cache_db=":memory:", default_ttl_seconds=60)
    key = cache.generate_key("test_api", {"param1": "foo", "param2": 123})
    assert cache.get(key) is None

    cache.set(key, {"result": [1, 2, 3]})
    cached = cache.get(key)
    assert cached == {"result": [1, 2, 3]}

    # Expired key
    cache.set(key, {"result": "expired"}, ttl_seconds=-1)
    assert cache.get(key) is None
    cache.close()

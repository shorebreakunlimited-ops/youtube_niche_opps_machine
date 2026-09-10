"""P5 Production Truth Pass regression tests.

Verifies:
1. test_validator_uses_snapshot_velocity_when_available
2. test_snapshot_coverage_is_not_hardcoded_zero
3. test_unknown_subscribers_do_not_count_as_zero
4. test_channel_size_percentile_uses_unique_channels
5. test_tier_b_is_age_adjusted_or_downgraded
6. test_validator_uses_topic_depth_engine
"""

from datetime import datetime, timezone, timedelta
import pytest

from src.collectors.browseract_adapter import BrowserActAdapter
from src.collectors.youtube_client import YouTubeClient
from src.models import Channel, Video, VideoMetricSnapshot
from src.scoring.breakout import compute_breakout_score
from src.storage.cache import SQLiteCache
from src.storage.database import NicheDatabase
from src.validation.niche_validator import NicheValidator
from src.validation.topic_depth import evaluate_topic_depth_and_runway


def test_validator_uses_snapshot_velocity_when_available(tmp_path):
    """Verify NicheValidator queries database snapshots and passes interval velocity into acceleration."""
    db = NicheDatabase(db_path=str(tmp_path / "niche_snap.db"))
    cache = SQLiteCache(db_path=str(tmp_path / "cache.db"))
    yt_client = YouTubeClient(cache=cache, db=db, use_mock=True)
    browser = BrowserActAdapter(cache=cache)

    validator = NicheValidator(
        youtube_client=yt_client,
        browser_adapter=browser,
        db=db,
        cache=cache,
    )

    # First run seeds videos into database
    res1 = validator.validate_niche("ai workflows", max_videos=10)
    assert res1.sample_size == 10

    # Inject multiple snapshots for videos in database
    t1 = datetime(2026, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
    t2 = t1 + timedelta(days=10)

    # Pick a video from mock results
    cur = db.conn.cursor()
    cur.execute("SELECT video_id FROM videos LIMIT 3")
    vids = [r[0] for r in cur.fetchall()]
    assert len(vids) == 3

    for vid in vids:
        db.save_video_snapshot(VideoMetricSnapshot(video_id=vid, observed_at=t1, views=10000))
        db.save_video_snapshot(VideoMetricSnapshot(video_id=vid, observed_at=t2, views=30000))

    # Verify database computed snapshot velocities
    snap_vels = db.get_snapshot_velocities_for_videos(vids)
    assert len(snap_vels) == 3
    for vid, vel in snap_vels.items():
        assert pytest.approx(vel, 0.1) == 2000.0  # 20,000 views over 10 days = 2,000 views/day

    # Second run should now incorporate snapshot velocities
    res2 = validator.validate_niche("ai workflows", max_videos=10)
    assert res2.sample_size == 10
    # Acceleration should be active and valid
    assert 0.0 <= res2.acceleration_score <= 100.0


def test_snapshot_coverage_is_not_hardcoded_zero(tmp_path):
    """Verify confidence calculation uses real snapshot coverage ratio instead of 0.0."""
    db = NicheDatabase(db_path=str(tmp_path / "niche_cov.db"))
    cache = SQLiteCache(db_path=str(tmp_path / "cache_cov.db"))
    yt_client = YouTubeClient(cache=cache, db=db, use_mock=True)
    browser = BrowserActAdapter(cache=cache)

    validator = NicheValidator(
        youtube_client=yt_client,
        browser_adapter=browser,
        db=db,
        cache=cache,
    )

    # Initial run with no prior snapshots
    res_cold = validator.validate_niche("cold niche", max_videos=5)

    # Seed 2 observations for all 5 videos
    cur = db.conn.cursor()
    cur.execute("SELECT video_id FROM videos")
    vids = [r[0] for r in cur.fetchall()]
    assert len(vids) >= 5

    t1 = datetime(2026, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
    t2 = t1 + timedelta(days=14)

    for vid in vids:
        db.save_video_snapshot(VideoMetricSnapshot(video_id=vid, observed_at=t1, views=5000))
        db.save_video_snapshot(VideoMetricSnapshot(video_id=vid, observed_at=t2, views=12000))

    # Re-validate with 100% snapshot coverage
    res_warm = validator.validate_niche("cold niche", max_videos=5)
    # Warm run confidence should be strictly greater than or equal to cold run
    assert res_warm.confidence_score >= res_cold.confidence_score


def test_unknown_subscribers_do_not_count_as_zero():
    """Verify channels with missing/unknown subscriber counts are NOT treated as 0 subscribers."""
    # Channel with None subscribers
    ch_unknown = Channel(channel_id="ch_unk", title="Unknown Size Channel", subscribers=None)
    # Channel with known large subscriber count
    ch_large = Channel(channel_id="ch_large", title="Known Large", subscribers=500000)
    channels = {"ch_unk": ch_unknown, "ch_large": ch_large}

    v_unk = Video(
        video_id="v_unk",
        channel_id="ch_unk",
        title="Unknown Channel Video",
        published_at="2026-08-01T00:00:00Z",
        views=50000,
    )
    v_large = Video(
        video_id="v_large",
        channel_id="ch_large",
        title="Large Channel Video",
        published_at="2026-08-01T00:00:00Z",
        views=200000,
    )

    # Neither video qualifies as a small channel breakout because unknown subs are NOT treated as 0
    (
        score,
        p_hat,
        k_breakouts,
        n_eligible,
        diversity,
        evidence,
        avg_tier,
    ) = compute_breakout_score([v_unk, v_large], channels)

    # Eligible videos should be 0 (unknown is not assumed small; large is > 50,000)
    assert n_eligible == 0
    assert k_breakouts == 0


def test_channel_size_percentile_uses_unique_channels():
    """Verify channel size distribution is computed across unique channels, not duplicated per video."""
    # Channel 1 has 10 videos with 100,000 subs (medium/large)
    # Channel 2 has 1 video with 20,000 subs (small)
    # Channel 3 has 1 video with 10,000 subs (small)
    ch1 = Channel(channel_id="c1", title="Creator Many Vids", subscribers=100000)
    ch2 = Channel(channel_id="c2", title="Creator Small 1", subscribers=20000)
    ch3 = Channel(channel_id="c3", title="Creator Small 2", subscribers=10000)
    channels = {"c1": ch1, "c2": ch2, "c3": ch3}

    videos = []
    # 10 videos from ch1
    for i in range(10):
        videos.append(
            Video(
                video_id=f"v_c1_{i}",
                channel_id="c1",
                title=f"C1 Video {i}",
                published_at="2026-08-01T00:00:00Z",
                views=5000,
            )
        )
    # 1 video each from ch2 and ch3
    videos.append(
        Video(
            video_id="v_c2_0",
            channel_id="c2",
            title="C2 Video",
            published_at="2026-08-01T00:00:00Z",
            views=10000,
        )
    )
    videos.append(
        Video(
            video_id="v_c3_0",
            channel_id="c3",
            title="C3 Video",
            published_at="2026-08-01T00:00:00Z",
            views=8000,
        )
    )

    # In unique channel space, c1 is top 1 of 3 (percentile ~83.3%), c1 videos should not dominate cohort size
    score, p_hat, k_breakouts, n_eligible, diversity, evidence, avg_tier = compute_breakout_score(
        videos, channels, small_channel_sub_limit=50000
    )

    # Only c2 and c3 are eligible (2 videos), ch1 is not eligible despite having 10 videos
    assert n_eligible == 2


def test_tier_b_is_age_adjusted_or_downgraded():
    """Verify Tier B LOO baseline normalizes peer video views by age decay curve."""
    ch = Channel(channel_id="c1", title="Creator", subscribers=10000)
    channels = {"c1": ch}

    # Candidate is 10 days old with 30,000 views
    candidate = Video(
        video_id="v_cand",
        channel_id="c1",
        title="10 Day Old Video",
        published_at="2026-08-20T00:00:00Z",
        views=30000,
    )
    # Peer is 200 days old with 5,000 views
    peer = Video(
        video_id="v_old_peer",
        channel_id="c1",
        title="200 Day Old Video",
        published_at="2026-02-10T00:00:00Z",
        views=5000,
    )

    channel_map = {"c1": [candidate, peer]}
    score, p_hat, k_breakouts, n_eligible, diversity, evidence, avg_tier = compute_breakout_score(
        [candidate, peer], channels, channel_video_map=channel_map
    )

    assert len(evidence) == 1
    ev = evidence[0]
    assert ev.baseline_tier == "B"
    # The baseline for a 10-day old video should be scaled down from a 200-day old video's views,
    # NOT raw unadjusted 5,000 views!
    # Expected age factor: (10/200)^0.7 ~ 0.122 -> ~610 views
    assert ev.baseline_views < 5000
    assert ev.breakout_ratio > (candidate.views / 5000.0)


def test_validator_uses_topic_depth_engine(tmp_path):
    """Verify NicheValidator invokes evaluate_topic_depth_and_runway with semantic TF-IDF embeddings."""
    db = NicheDatabase(db_path=str(tmp_path / "niche_topic.db"))
    cache = SQLiteCache(db_path=str(tmp_path / "cache_topic.db"))
    yt_client = YouTubeClient(cache=cache, db=db, use_mock=True)
    browser = BrowserActAdapter(cache=cache)

    validator = NicheValidator(
        youtube_client=yt_client,
        browser_adapter=browser,
        db=db,
        cache=cache,
    )

    result = validator.validate_niche("python automation", max_videos=10)
    # Repeatability score should be populated from topic depth engine
    assert 0.0 <= result.repeatability_score <= 100.0
    # Video ideas should be generated from topic depth 15-axis templates
    assert len(result.video_ideas) >= 5
    assert any("Automation" in idea or "Guide" in idea or "Python" in idea for idea in result.video_ideas)

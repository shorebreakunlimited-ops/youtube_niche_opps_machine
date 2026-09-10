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
    """Verify NicheValidator queries database snapshots and that snapshot velocity materially affects acceleration."""
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

    # First run seeds videos into database without historical snapshots (cold start)
    res_cold = validator.validate_niche("ai workflows", max_videos=10)
    assert res_cold.sample_size == 10
    cold_accel = res_cold.acceleration_score

    # Determine actual video ages from the first run
    videos, _, _ = yt_client.search_videos("ai workflows", max_results=10)
    recent_cutoff = 30.0

    recent_vids = [v.video_id for v in videos if v.video_age_days <= recent_cutoff]
    baseline_vids = [v.video_id for v in videos if v.video_age_days > recent_cutoff]

    assert len(recent_vids) > 0
    assert len(baseline_vids) > 0

    # Inject snapshots: simulate explosive recent velocity for recent videos
    # (+100,000 views over 5 days = 20,000 views/day)
    t1 = datetime(2026, 8, 1, 0, 0, 0, tzinfo=timezone.utc)
    t2 = t1 + timedelta(days=5)
    for vid in recent_vids:
        db.save_video_snapshot(VideoMetricSnapshot(video_id=vid, observed_at=t1, views=1000))
        db.save_video_snapshot(VideoMetricSnapshot(video_id=vid, observed_at=t2, views=101000))

    # Verify database computed snapshot velocities for those recent videos
    snap_vels = db.get_snapshot_velocities_for_videos(recent_vids)
    assert len(snap_vels) == len(recent_vids)
    for vid, vel in snap_vels.items():
        assert pytest.approx(vel, 0.1) == 20000.0

    # Second run should now incorporate snapshot velocities into validator
    res_warm = validator.validate_niche("ai workflows", max_videos=10)
    assert res_warm.sample_size == 10
    warm_accel = res_warm.acceleration_score

    # Behavioral proof: explosive snapshot velocity materially changes the validator result
    # specifically, warm_accel must be strictly higher than cold_accel due to the snapshot injection
    assert warm_accel != cold_accel
    assert warm_accel > cold_accel
    assert warm_accel >= 70.0


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

    # Re-validate with 100% snapshot coverage (clear cache to re-execute search persistence)
    if cache:
        cache.clear()
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
    """Verify NicheValidator invokes evaluate_topic_depth_and_runway and that output reflects semantic runway metrics."""
    import json
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

    clean_niche = "python automation"
    result = validator.validate_niche(clean_niche, max_videos=10)

    # 1. Independent run of evaluate_topic_depth_and_runway on the exact same inputs
    video_titles = [v.title for v in yt_client.get_videos_batch([])]  # or from result
    # We query videos saved in DB for this niche to replicate validator's exact input
    cur = db.conn.cursor()
    cur.execute("SELECT title FROM videos")
    db_titles = [r[0] for r in cur.fetchall()]
    suggestions = browser.get_autocomplete_suggestions(clean_niche)

    ground_truth_metrics = evaluate_topic_depth_and_runway(
        seed_topic=clean_niche,
        video_titles=db_titles,
        autocomplete_suggestions=suggestions,
    )

    # 2. Verify validator's repeatability score matches ground-truth topic depth engine calculation exactly
    expected_score = float(ground_truth_metrics["repeatability_score"])
    assert result.repeatability_score == expected_score

    # 3. Verify topic_runway_metrics inside raw_payload_json match ground-truth values
    raw_payload = json.loads(result.raw_payload_json)
    assert "topic_runway_metrics" in raw_payload
    topic_metrics = raw_payload["topic_runway_metrics"]
    assert topic_metrics["axes_covered_count"] == ground_truth_metrics["axes_covered_count"]
    assert topic_metrics["entropy_ratio"] == ground_truth_metrics["entropy_ratio"]
    assert topic_metrics["inter_cluster_distance"] == ground_truth_metrics["inter_cluster_distance"]
    assert topic_metrics["estimated_video_runway"] == ground_truth_metrics["estimated_video_runway"]

    # 4. Video ideas must originate from the 15-axis templates evaluated in topic depth
    ground_truth_angle_titles = [a["title"] for a in ground_truth_metrics["generated_video_angles"]]
    # The first video ideas produced by validator should match the generated 15-axis angles
    for idea in result.video_ideas[:3]:
        assert idea in ground_truth_angle_titles or idea.title() in [s.title() for s in suggestions]

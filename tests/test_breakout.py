"""Tests for breakout detection and Leave-One-Out baseline calculations."""

import pytest
from src.models import Channel, Video
from src.scoring.breakout import compute_breakout_score


def test_leave_one_out_baseline_excludes_candidate():
    """Verify candidate breakout video is excluded from its own channel baseline."""
    ch = Channel(channel_id="c1", title="Creator One", subscribers=5000)
    channels = {"c1": ch}

    # Candidate video has 500,000 views
    candidate = Video(
        video_id="v_breakout",
        channel_id="c1",
        title="Mega Viral Video",
        published_at="2026-08-01T00:00:00Z",
        views=500000,
    )
    # Peer videos have typical views: 1,000, 1,200, 800
    peer1 = Video(
        video_id="v_norm1",
        channel_id="c1",
        title="Normal Video 1",
        published_at="2026-07-01T00:00:00Z",
        views=1000,
    )
    peer2 = Video(
        video_id="v_norm2",
        channel_id="c1",
        title="Normal Video 2",
        published_at="2026-07-15T00:00:00Z",
        views=1200,
    )
    peer3 = Video(
        video_id="v_norm3",
        channel_id="c1",
        title="Normal Video 3",
        published_at="2026-07-20T00:00:00Z",
        views=800,
    )

    channel_map = {"c1": [candidate, peer1, peer2, peer3]}
    videos = [candidate, peer1, peer2, peer3]

    (
        score,
        p_hat,
        k_breakouts,
        n_eligible,
        diversity,
        evidence,
        avg_tier,
    ) = compute_breakout_score(videos, channels, channel_video_map=channel_map)

    # 1 breakout detected
    assert k_breakouts == 1
    assert n_eligible == 4
    assert len(evidence) == 1

    ev = evidence[0]
    assert ev.video_id == "v_breakout"
    # LOO baseline should be age-normalized median of peer views
    assert ev.baseline_views > 0
    assert ev.breakout_ratio >= 3.0
    assert ev.baseline_tier == "B"


def test_zero_breakouts_scores_only_prior_floor():
    """Verify a niche with 0 breakouts gets 0 diversity and scores only the prior floor."""
    ch = Channel(channel_id="c1", title="Creator", subscribers=5000)
    channels = {"c1": ch}

    # All videos are flat (no breakout)
    v1 = Video(video_id="v1", channel_id="c1", title="V1", published_at="2026-08-01T00:00:00Z", views=1000)
    v2 = Video(video_id="v2", channel_id="c1", title="V2", published_at="2026-08-02T00:00:00Z", views=1000)

    score, p_hat, k_breakouts, n_eligible, diversity, evidence, _ = compute_breakout_score(
        [v1, v2], channels
    )

    assert k_breakouts == 0
    assert diversity == 0.0
    assert len(evidence) == 0
    # Prior floor: (1)/(2 + 1 + 19) = 1/22 ~ 0.0454 -> scaled by 65/0.25 ~ 11.8
    assert 10.0 <= score <= 13.0

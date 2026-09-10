"""Tests for continuous outlier detection and distribution quantiles."""

from src.models import Video
from src.validation.outlier_analysis import analyze_outliers


def test_analyze_outliers_healthy_niche():
    """Verify that a healthy, evenly distributed niche incurs minimal penalty."""
    videos = [
        Video(video_id=f"v{i}", channel_id=f"c{i}", title=f"Video {i}", published_at="2026-08-01T00:00:00Z", views=10000 + i * 500)
        for i in range(20)
    ]
    penalty, top1, top3, is_viral, quantiles = analyze_outliers(videos)
    assert penalty < 2.0
    assert not is_viral
    assert top1 < 0.15
    assert quantiles["median"] > 10000


def test_analyze_outliers_viral_anomaly():
    """Verify that a single viral hit dominating >65% of views triggers VIRAL OUTLIER."""
    # 1 video with 1,000,000 views, 19 videos with 500 views
    videos = [
        Video(video_id="v_viral", channel_id="c_top", title="Viral", published_at="2026-08-01T00:00:00Z", views=1000000)
    ] + [
        Video(video_id=f"v{i}", channel_id=f"c{i}", title=f"Small {i}", published_at="2026-08-01T00:00:00Z", views=500)
        for i in range(19)
    ]

    penalty, top1, top3, is_viral, quantiles = analyze_outliers(videos)
    assert top1 > 0.90
    assert is_viral
    assert penalty > 35.0
    assert quantiles["median"] == 500

"""Demand score calculator for audience velocity and engagement."""

import numpy as np
from typing import List, Optional
from src.models import Video
from src.scoring.statistics import safe_ratio


def compute_demand_score(
    videos: List[Video],
    target_median_velocity: float = 1000.0,
    target_p75_velocity: float = 5000.0,
) -> float:
    """Compute normalized audience demand score in [0, 100].
    
    Combines:
    - Median daily view velocity (40%)
    - Upper-quartile (P75) velocity (30%)
    - Recent successful video density (15%)
    - Engagement intensity (likes/comments per 1k views) (15%)
    """
    if not videos:
        return 0.0

    velocities = [v.lifetime_proxy_velocity for v in videos]
    median_vel = float(np.median(velocities))
    p75_vel = float(np.percentile(velocities, 75))

    # Normalized velocity scores in [0, 100]
    med_score = min(100.0, (median_vel / max(target_median_velocity, 1.0)) * 100.0)
    p75_score = min(100.0, (p75_vel / max(target_p75_velocity, 1.0)) * 100.0)

    # Recent successful videos (>10k views, published in last 90 days)
    recent_successful = sum(
        1 for v in videos if v.views >= 10000 and v.video_age_days <= 90
    )
    success_ratio = min(1.0, recent_successful / max(len(videos) * 0.25, 1.0))
    success_score = success_ratio * 100.0

    # Engagement intensity: average likes & comments per 1k views
    engagement_rates = [
        v.likes_per_1000_views + 2.0 * v.comments_per_1000_views
        for v in videos
        if v.views >= 500
    ]
    avg_eng = float(np.mean(engagement_rates)) if engagement_rates else 20.0
    # 40 per 1k views is standard healthy engagement
    eng_score = min(100.0, (avg_eng / 40.0) * 100.0)

    raw_demand = (
        0.40 * med_score
        + 0.30 * p75_score
        + 0.15 * success_score
        + 0.15 * eng_score
    )
    return float(min(100.0, max(0.0, raw_demand)))

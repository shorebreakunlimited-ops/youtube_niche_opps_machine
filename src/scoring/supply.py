"""Supply scarcity and competition analyzer with porous incumbent interaction."""

from typing import Dict, List, Tuple
from collections import defaultdict
import numpy as np

from src.models import Channel, Video
from src.scoring.statistics import incumbent_friction_factor


def compute_supply_scarcity_score(
    videos: List[Video],
    channels: Dict[str, Channel],
    p_hat_breakout: float,
    p_neutralize: float = 0.20,
    incumbent_sub_threshold: int = 250000,
) -> Tuple[float, float, float, float]:
    """Compute Supply Scarcity score in [0, 100] with breakout-neutralized incumbent friction.
    
    Returns:
    (supply_scarcity_score, hhi_index, incumbent_share, gamma_friction)
    """
    if not videos:
        return 50.0, 0.0, 0.0, 1.0

    total_views = sum(max(1, v.views) for v in videos)
    channel_views = defaultdict(int)
    recent_uploads_30d = 0
    baseline_uploads_90d = 0

    for v in videos:
        channel_views[v.channel_id] += v.views
        if v.video_age_days <= 30:
            recent_uploads_30d += 1
        elif v.video_age_days <= 90:
            baseline_uploads_90d += 1

    # 1. HHI Concentration
    shares = [views / total_views for views in channel_views.values()]
    hhi = sum(s ** 2 for s in shares)  # Range ~ [1/N, 1.0]
    hhi_norm = min(1.0, max(0.0, hhi))

    # 2. Incumbent View Share (>250k subscribers)
    incumbent_views = sum(
        channel_views[ch_id]
        for ch_id in channel_views
        if ch_id in channels
        and channels[ch_id].subscribers is not None
        and channels[ch_id].subscribers >= incumbent_sub_threshold
    )
    incumbent_share = min(1.0, incumbent_views / total_views)

    # 3. Supply Density Components
    # Creator density: channels per video ratio (higher ratio = more creators competing)
    creator_ratio = len(channel_views) / max(len(videos), 1)
    # Creator density norm: 0.5+ channels per video indicates dense competition
    d_creator_norm = min(1.0, creator_ratio / 0.8)

    # Cadence norm: active publishing rate
    cadence_norm = min(1.0, (recent_uploads_30d / max(len(videos) * 0.4, 1.0)))

    # Supply growth velocity: 30d uploads annualized vs 90d baseline
    expected_30d_from_90d = baseline_uploads_90d / 2.0
    supply_growth = (
        (recent_uploads_30d - expected_30d_from_90d) / max(expected_30d_from_90d, 1.0)
        if baseline_uploads_90d > 0
        else 0.0
    )
    supply_growth_norm = min(1.0, max(0.0, (supply_growth + 1.0) / 2.0))

    supply_density = (
        0.40 * d_creator_norm
        + 0.35 * cadence_norm
        + 0.25 * supply_growth_norm
    )
    base_scarcity = 100.0 * (1.0 - supply_density)

    # 4. Incumbent Friction Factor Gamma with Configurable Neutralization Threshold
    gamma = incumbent_friction_factor(p_hat_breakout, p_neutralize=p_neutralize)

    # 5. Final Supply Scarcity Score
    concentration_penalty = gamma * (25.0 * hhi_norm + 20.0 * incumbent_share)
    scarcity_score = base_scarcity - concentration_penalty

    return (
        float(min(100.0, max(0.0, scarcity_score))),
        float(hhi),
        float(incumbent_share),
        float(gamma),
    )

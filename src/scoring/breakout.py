"""Small-channel breakout detector with Bayesian shrinkage and LOO baselines."""

from typing import Dict, List, Optional, Tuple
import numpy as np

from src.models import BreakoutEvidence, Channel, Video
from src.scoring.statistics import (
    beta_binomial_shrinkage,
    breakout_diversity_factor,
    percentile_ranks,
)


def compute_breakout_score(
    videos: List[Video],
    channels: Dict[str, Channel],
    channel_video_map: Optional[Dict[str, List[Video]]] = None,
    snapshot_baselines: Optional[Dict[str, float]] = None,
    small_channel_sub_limit: int = 50000,
    small_channel_percentile_cutoff: float = 25.0,
    performance_percentile_cutoff: float = 75.0,
    breakout_multiplier_threshold: float = 3.0,
    baseline_floor: float = 100.0,
    prior_alpha: float = 1.0,
    prior_beta: float = 19.0,
    target_breakout_rate: float = 0.25,
) -> Tuple[float, float, int, int, float, List[BreakoutEvidence], float]:
    """Compute Bayesian-shrunk small-channel breakout score and structured evidence.
    
    Returns:
    (breakout_score, p_hat_breakout, k_breakouts, n_eligible, diversity, evidence_list, avg_tier_confidence)
    """
    if not videos:
        return 0.0, 0.0, 0, 0, 0.0, [], 0.5

    # If no external channel_video_map is provided, construct one from the cohort videos
    if channel_video_map is None:
        channel_video_map = {}
        for vid in videos:
            channel_video_map.setdefault(vid.channel_id, []).append(vid)

    # 1. Compute cohort percentiles for channel size and video performance
    video_velocities = [v.lifetime_proxy_velocity for v in videos]
    perf_percentiles = percentile_ranks(video_velocities)

    # Calculate channel size percentiles across UNIQUE channels with KNOWN subscriber counts
    unique_channel_ids = list({v.channel_id for v in videos})
    known_channels = [
        cid for cid in unique_channel_ids
        if cid in channels and channels[cid].subscribers is not None
    ]
    known_subs = [channels[cid].subscribers for cid in known_channels]
    subs_ranks = percentile_ranks(known_subs) if known_subs else []
    
    # Map channel_id -> unique channel size percentile (None if subscriber count unknown)
    size_percentiles: Dict[str, Optional[float]] = {}
    for cid, rank in zip(known_channels, subs_ranks):
        size_percentiles[cid] = rank
    for cid in unique_channel_ids:
        if cid not in size_percentiles:
            size_percentiles[cid] = None

    eligible_videos = 0
    breakout_videos = []
    breakout_channels = set()
    evidence_list: List[BreakoutEvidence] = []
    tier_confidences = []

    for i, v in enumerate(videos):
        ch = channels.get(v.channel_id)
        subs = ch.subscribers if ch else None
        size_pct = size_percentiles.get(v.channel_id)
        perf_pct = perf_percentiles[i]

        # Dual Small Channel check:
        # A channel qualifies if subs is known and <= small_channel_sub_limit,
        # OR if its unique-channel percentile is <= small_channel_percentile_cutoff.
        # Channels with unknown subscribers are NOT assumed small by default;
        # they must have known subscribers or clear channel size percentile.
        is_small = False
        if subs is not None and 0 <= subs <= small_channel_sub_limit:
            is_small = True
        elif size_pct is not None and size_pct <= small_channel_percentile_cutoff:
            is_small = True

        if not is_small:
            continue

        eligible_videos += 1

        # 2. Compute Leave-One-Out (LOO) Baseline & Tier
        baseline_views = baseline_floor
        tier = "C"
        tier_conf = 0.5

        if snapshot_baselines and v.video_id in snapshot_baselines:
            # Tier A: Snapshot-derived age-matched baseline
            baseline_views = max(snapshot_baselines[v.video_id], baseline_floor)
            tier = "A"
            tier_conf = 1.0
        elif channel_video_map and v.channel_id in channel_video_map:
            # Tier B: Historical LOO baseline with age & velocity decay normalization
            # Rather than raw unadjusted lifetime views, scale peer views to candidate's age
            # using power-law decay curve: ExpectedViews(t) ~ t^0.7
            peer_vids = [
                peer for peer in channel_video_map[v.channel_id]
                if peer.video_id != v.video_id
            ]
            if peer_vids:
                cand_age = max(1.0, float(v.video_age_days))
                age_normalized_views = []
                for peer in peer_vids:
                    peer_age = max(1.0, float(peer.video_age_days))
                    # Scale peer views to candidate age: views * (cand_age / peer_age)^0.7
                    age_scaling_factor = (cand_age / peer_age) ** 0.70
                    # Clamp scaling factor to avoid extreme extrapolation ([0.1, 10.0])
                    clamped_factor = max(0.1, min(10.0, age_scaling_factor))
                    age_normalized_views.append(peer.views * clamped_factor)
                
                baseline_views = max(float(np.median(age_normalized_views)), baseline_floor)
                tier = "B"
                tier_conf = 0.8
            elif ch and ch.median_recent_views:
                baseline_views = max(ch.median_recent_views, baseline_floor)
                tier = "C"
                tier_conf = 0.5
        elif ch and ch.median_recent_views:
            baseline_views = max(ch.median_recent_views, baseline_floor)
            tier = "C"
            tier_conf = 0.5

        tier_confidences.append(tier_conf)

        # 3. Check Breakout Condition
        breakout_ratio = v.views / baseline_views
        is_breakout = (
            breakout_ratio >= breakout_multiplier_threshold
            and perf_pct >= performance_percentile_cutoff
            and v.views >= 500  # Minimum absolute view floor
        )

        if is_breakout:
            breakout_videos.append(v)
            breakout_channels.add(v.channel_id)
            evidence_list.append(
                BreakoutEvidence(
                    channel_id=v.channel_id,
                    channel_title=ch.title if ch else "Unknown",
                    subscribers=subs,
                    video_id=v.video_id,
                    video_title=v.title,
                    views=v.views,
                    baseline_views=baseline_views,
                    breakout_ratio=float(round(breakout_ratio, 2)),
                    baseline_tier=tier,
                )
            )

    k_breakouts = len(breakout_videos)
    # Bayesian smoothed breakout rate
    p_hat = beta_binomial_shrinkage(
        k=k_breakouts, n=eligible_videos, alpha=prior_alpha, beta=prior_beta
    )

    # Zero-guarded diversity factor
    diversity = breakout_diversity_factor(
        distinct_channels=len(breakout_channels),
        total_breakout_videos=k_breakouts,
    )

    avg_tier = (
        float(np.mean(tier_confidences)) if tier_confidences else 0.5
    )

    # If 0 breakouts, score reflects only the prior floor (~12.0)
    scaled_p = (p_hat / target_breakout_rate) * 65.0
    scaled_div = diversity * 35.0
    score = min(100.0, scaled_p + scaled_div)

    return float(max(0.0, score)), float(p_hat), k_breakouts, eligible_videos, float(diversity), evidence_list, avg_tier

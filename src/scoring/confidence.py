"""Evidence confidence calculation and decision gating model."""

import math
from typing import List, Optional, Tuple
from src.scoring.statistics import source_agreement_score


def compute_confidence_score(
    video_count: int,
    snapshot_coverage_ratio: float = 0.0,
    avg_breakout_tier_confidence: float = 0.5,
    source_demand_indices: Optional[List[float]] = None,
    sample_target: float = 50.0,
) -> Tuple[float, Optional[float], str]:
    """Compute Evidence Confidence Score in [0, 100] with single-source guards.
    
    Returns:
    (confidence_score, agreement_score, cross_source_status)
    """
    # 1. Sample Size Quality
    c_sample = min(1.0, math.sqrt(max(0, video_count) / max(sample_target, 1.0)))

    # 2. Temporal Velocity Quality
    cov = max(0.0, min(1.0, float(snapshot_coverage_ratio)))
    if cov >= 0.70:
        c_temporal = 1.0
    elif cov >= 0.30:
        c_temporal = 0.75
    else:
        c_temporal = 0.40

    # 3. Breakout Tier Quality
    c_tier = max(0.0, min(1.0, float(avg_breakout_tier_confidence)))

    # 4. Source Agreement Quality (with Single-Source Guard)
    indices = source_demand_indices or []
    agreement, status = source_agreement_score(indices)

    if agreement is not None:
        # Multi-source full formula
        raw_conf = (
            0.35 * c_sample
            + 0.25 * c_temporal
            + 0.20 * c_tier
            + 0.20 * agreement
        )
        conf_score = raw_conf * 100.0
    else:
        # Single-source reweighted and penalized by 15%
        reweighted = (
            (0.35 / 0.80) * c_sample
            + (0.25 / 0.80) * c_temporal
            + (0.20 / 0.80) * c_tier
        )
        conf_score = reweighted * 100.0 * 0.85

    return float(min(100.0, max(0.0, conf_score))), agreement, status

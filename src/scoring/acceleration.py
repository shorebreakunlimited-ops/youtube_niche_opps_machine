"""Acceleration score calculation comparing recent vs historical velocity."""

from typing import Dict, List, Optional
import numpy as np

from src.models import Video
from src.scoring.statistics import centered_bounded_acceleration


def compute_acceleration_score(
    videos: List[Video],
    snapshot_velocities: Optional[Dict[str, float]] = None,
    sensitivity_k: float = 1.0,
    recent_cutoff_days: float = 30.0,
    baseline_cutoff_days: float = 180.0,
) -> float:
    """Compute centered bounded acceleration score in [0, 100].
    
    Prefers snapshot delta velocity when available, falling back to lifetime proxy.
    Compares recent velocity (<=30 days) to historical baseline (31 to 180 days).
    """
    if not videos:
        return 50.0

    recent_vels = []
    baseline_vels = []

    for v in videos:
        # Determine velocity for this video
        vel = (
            snapshot_velocities.get(v.video_id)
            if snapshot_velocities and v.video_id in snapshot_velocities
            else v.lifetime_proxy_velocity
        )

        age = v.video_age_days
        if age <= recent_cutoff_days:
            recent_vels.append(vel)
        elif age <= baseline_cutoff_days:
            baseline_vels.append(vel)

    if not recent_vels and not baseline_vels:
        return 50.0
    if not recent_vels:
        # No recent uploads: contracting momentum
        return 25.0
    if not baseline_vels:
        # Brand new emerging cluster with only recent videos
        return 75.0

    recent_median = float(np.median(recent_vels))
    baseline_median = float(np.median(baseline_vels))

    return centered_bounded_acceleration(
        recent_velocity=recent_median,
        baseline_velocity=baseline_median,
        k=sensitivity_k,
    )

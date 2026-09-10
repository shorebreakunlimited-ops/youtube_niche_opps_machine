"""Outlier resistance and continuous viral anomaly detection."""

from typing import Dict, List, Tuple
import numpy as np

from src.models import Video
from src.scoring.statistics import continuous_sigmoid_outlier_penalty


def analyze_outliers(
    videos: List[Video],
    top1_center: float = 0.55,
    top3_center: float = 0.78,
    steepness: float = 15.0,
    max_penalty: float = 40.0,
) -> Tuple[float, float, float, bool, Dict[str, float]]:
    """Compute continuous sigmoid outlier penalty and distribution quantiles.
    
    Returns:
    (outlier_risk_score, top1_share, top3_share, is_viral_outlier_risk, quantiles)
    """
    if not videos:
        return 0.0, 0.0, 0.0, False, {}

    views = sorted([max(1, v.views) for v in videos], reverse=True)
    total_views = sum(views)

    top1_share = views[0] / total_views
    top3_share = sum(views[:3]) / total_views if len(views) >= 3 else top1_share

    penalty = continuous_sigmoid_outlier_penalty(
        top1_share=top1_share,
        top3_share=top3_share,
        top1_center=top1_center,
        top3_center=top3_center,
        steepness=steepness,
        max_penalty=max_penalty,
    )

    is_viral_outlier = bool(top1_share > 0.65 or top3_share > 0.85)

    arr = np.array(views)
    quantiles = {
        "p25": float(np.percentile(arr, 25)),
        "median": float(np.median(arr)),
        "p75": float(np.percentile(arr, 75)),
        "p90": float(np.percentile(arr, 90)),
        "p95": float(np.percentile(arr, 95)),
        "max": float(views[0]),
    }

    return float(penalty), float(top1_share), float(top3_share), is_viral_outlier, quantiles

"""Statistical utilities and mathematical foundations for the Niche Engine."""

import math
from typing import List, Optional, Sequence, Tuple
import numpy as np


def median_absolute_deviation(data: Sequence[float]) -> float:
    """Compute the Median Absolute Deviation (MAD) of a numeric sequence.
    
    MAD = median(|X_i - median(X)|)
    """
    clean_data = [x for x in data if x is not None and not np.isnan(x)]
    if not clean_data:
        return 0.0
    arr = np.array(clean_data, dtype=float)
    med = np.median(arr)
    mad = float(np.median(np.abs(arr - med)))
    return mad


def robust_zscore(data: Sequence[float], epsilon: float = 1e-6) -> List[float]:
    """Calculate robust Z-scores using median and MAD.
    
    Z_i = 0.6745 * (X_i - median(X)) / max(MAD, epsilon)
    """
    clean_data = [x for x in data if x is not None and not np.isnan(x)]
    if not clean_data:
        return []
    arr = np.array(clean_data, dtype=float)
    med = float(np.median(arr))
    mad = median_absolute_deviation(clean_data)
    denominator = max(mad, epsilon)
    z_scores = 0.6745 * (arr - med) / denominator
    return [float(z) for z in z_scores]


def percentile_rank(data: Sequence[float], value: float) -> float:
    """Compute the percentile rank (0.0 to 100.0) of a single value relative to data."""
    clean_data = [x for x in data if x is not None and not np.isnan(x)]
    if not clean_data:
        return 50.0
    arr = np.sort(np.array(clean_data, dtype=float))
    # Count how many items in arr are less than or equal to value
    count = np.searchsorted(arr, value, side="right")
    return float(count / len(arr) * 100.0)


def percentile_ranks(data: Sequence[float]) -> List[float]:
    """Compute percentile ranks (0.0 to 100.0) for every element in data."""
    if not data:
        return []
    arr = np.array(data, dtype=float)
    n = len(arr)
    if n == 1:
        return [50.0]
    # Use scipy/pandas style average ranking or sort-based rank
    ranks = np.argsort(np.argsort(arr)) + 1
    return [float(r / n * 100.0) for r in ranks]


def safe_ratio(numerator: float, denominator: float, floor: float = 1.0) -> float:
    """Safely divide numerator by denominator with a strictly enforced floor."""
    denom = max(float(denominator), float(floor))
    return float(numerator) / denom


def winsorize(data: Sequence[float], lower_pct: float = 0.05, upper_pct: float = 0.95) -> List[float]:
    """Winsorize data between lower_pct and upper_pct quantiles."""
    clean_data = [x for x in data if x is not None and not np.isnan(x)]
    if not clean_data:
        return []
    arr = np.array(clean_data, dtype=float)
    low_val = float(np.percentile(arr, lower_pct * 100.0))
    high_val = float(np.percentile(arr, upper_pct * 100.0))
    clipped = np.clip(arr, low_val, high_val)
    return [float(x) for x in clipped]


def beta_binomial_shrinkage(
    k: int, n: int, alpha: float = 1.0, beta: float = 19.0
) -> float:
    """Empirical Bayesian conjugate smoothing for binomial breakout rate.
    
    p_hat = (k + alpha) / (n + alpha + beta)
    
    Prior: alpha=1.0, beta=19.0 (initial calibration prior).
    """
    k_clean = max(0, int(k))
    n_clean = max(k_clean, int(n))
    return float((k_clean + alpha) / (n_clean + alpha + beta))


def centered_bounded_acceleration(
    recent_velocity: float,
    baseline_velocity: float,
    k: float = 1.0,
    epsilon: float = 0.001,
) -> float:
    """Centered bounded hyperbolic tangent acceleration transformation.
    
    Score = 50.0 + 50.0 * tanh(k * ln(recent / max(baseline, epsilon)))
    
    Properties:
    - ratio < 1 -> score in [0, 50)
    - ratio == 1 -> exactly 50.0
    - ratio > 1 -> score in (50, 100]
    """
    rec = max(0.0, float(recent_velocity))
    base = max(float(epsilon), float(baseline_velocity))
    ratio = rec / base
    if ratio <= 0.0:
        return 0.0
    val = 50.0 + 50.0 * math.tanh(k * math.log(ratio))
    return float(min(100.0, max(0.0, val)))


def continuous_sigmoid_outlier_penalty(
    top1_share: float,
    top3_share: float,
    top1_center: float = 0.55,
    top3_center: float = 0.78,
    steepness: float = 15.0,
    max_penalty: float = 40.0,
) -> float:
    """Continuous smooth sigmoid outlier penalty bounded strictly in [0, max_penalty].
    
    P_outlier = max_penalty * (0.65 / (1 + e^(-s * (top1 - c1))) + 0.35 / (1 + e^(-s * (top3 - c3))))
    """
    t1 = max(0.0, min(1.0, float(top1_share)))
    t3 = max(t1, min(1.0, float(top3_share)))
    
    sig1 = 1.0 / (1.0 + math.exp(-steepness * (t1 - top1_center)))
    sig3 = 1.0 / (1.0 + math.exp(-steepness * (t3 - top3_center)))
    
    combined = 0.65 * sig1 + 0.35 * sig3
    penalty = max_penalty * combined
    return float(min(max_penalty, max(0.0, penalty)))


def incumbent_friction_factor(
    breakout_rate: float, p_neutralize: float = 0.20
) -> float:
    """Compute the incumbent friction factor gamma with configurable neutralization threshold.
    
    gamma = max(0.0, 1.0 - breakout_rate / p_neutralize)
    
    When breakout_rate >= p_neutralize (default 0.20), gamma = 0.0 (penalty neutralized).
    """
    p = max(0.0, float(breakout_rate))
    p_neut = max(0.001, float(p_neutralize))
    gamma = 1.0 - (p / p_neut)
    return float(max(0.0, min(1.0, gamma)))


def breakout_diversity_factor(
    distinct_channels: int, total_breakout_videos: int
) -> float:
    """Compute breakout channel diversity without phantom breakout credit.
    
    diversity = 0.0 if total_breakout_videos == 0 else distinct_channels / total_breakout_videos
    """
    total = max(0, int(total_breakout_videos))
    distinct = max(0, int(distinct_channels))
    if total == 0:
        return 0.0
    return float(min(1.0, distinct / total))


def source_agreement_score(
    source_demand_indices: Sequence[float],
) -> Tuple[Optional[float], str]:
    """Compute source agreement across independent demand indices in [0, 1].
    
    If fewer than 2 sources exist, returns (None, 'UNAVAILABLE').
    Else clamp(1.0 - 2.0 * mean_absolute_disagreement, 0.0, 1.0), 'AVAILABLE'.
    """
    clean_indices = [
        float(x) for x in source_demand_indices if x is not None and not np.isnan(x)
    ]
    if len(clean_indices) < 2:
        return None, "UNAVAILABLE"
    
    mean_idx = sum(clean_indices) / len(clean_indices)
    mad_sources = sum(abs(x - mean_idx) for x in clean_indices) / len(clean_indices)
    agreement = max(0.0, min(1.0, 1.0 - 2.0 * mad_sources))
    return float(agreement), "AVAILABLE"


def guarded_entropy_ratio(cluster_sizes: Sequence[int]) -> float:
    """Compute Shannon entropy ratio with explicit mathematical guards for K <= 1.
    
    E_norm = 1.0 if K <= 1 else (-sum p_c ln p_c) / ln(K)
    """
    sizes = [s for s in cluster_sizes if s > 0]
    k = len(sizes)
    if k <= 1:
        return 1.0
    total = sum(sizes)
    probs = [s / total for s in sizes]
    shannon = -sum(p * math.log(p) for p in probs)
    max_entropy = math.log(k)
    return float(min(1.0, max(0.0, shannon / max_entropy)))


def guarded_inter_cluster_distance(centroids: Sequence[Sequence[float]]) -> float:
    """Compute mean pairwise cosine distance with explicit mathematical guards for K < 2.
    
    D_inter = 1.0 if K < 2 else mean pairwise cosine distance
    """
    k = len(centroids)
    if k < 2:
        return 1.0
    
    norm_centroids = []
    for c in centroids:
        arr = np.array(c, dtype=float)
        norm = np.linalg.norm(arr)
        if norm > 0:
            norm_centroids.append(arr / norm)
        else:
            norm_centroids.append(arr)
            
    distances = []
    for i in range(k):
        for j in range(i + 1, k):
            cos_sim = float(np.dot(norm_centroids[i], norm_centroids[j]))
            cos_dist = max(0.0, min(1.0, 1.0 - cos_sim))
            distances.append(cos_dist)
            
    if not distances:
        return 1.0
    return float(sum(distances) / len(distances))

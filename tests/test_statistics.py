"""Unit tests for statistical math and robust calculations."""

import pytest
import math
from src.scoring.statistics import (
    median_absolute_deviation,
    robust_zscore,
    percentile_rank,
    percentile_ranks,
    safe_ratio,
    winsorize,
    beta_binomial_shrinkage,
    centered_bounded_acceleration,
    continuous_sigmoid_outlier_penalty,
    incumbent_friction_factor,
    breakout_diversity_factor,
    source_agreement_score,
    guarded_entropy_ratio,
    guarded_inter_cluster_distance,
)


def test_zero_breakouts_do_not_receive_diversity_credit():
    """Mandatory Test 1: Confirm 0 breakout videos yields exactly diversity = 0.0."""
    div = breakout_diversity_factor(distinct_channels=0, total_breakout_videos=0)
    assert div == 0.0
    
    # Even if distinct_channels was somehow non-zero while total=0
    div2 = breakout_diversity_factor(distinct_channels=3, total_breakout_videos=0)
    assert div2 == 0.0

    # Non-zero breakouts compute proper ratio
    div3 = breakout_diversity_factor(distinct_channels=4, total_breakout_videos=5)
    assert div3 == 0.8


def test_incumbent_friction_reaches_zero_at_configured_breakout_threshold():
    """Mandatory Test 2: Confirm gamma = 0.0 exactly at p_neutralize and 1.0 at 0.0."""
    p_neutralize = 0.20
    
    # At 0 breakout rate -> 1.0
    assert incumbent_friction_factor(0.0, p_neutralize=p_neutralize) == 1.0
    
    # Linear intermediate progression
    assert pytest.approx(incumbent_friction_factor(0.05, p_neutralize=p_neutralize), 1e-4) == 0.75
    assert pytest.approx(incumbent_friction_factor(0.10, p_neutralize=p_neutralize), 1e-4) == 0.50
    assert pytest.approx(incumbent_friction_factor(0.15, p_neutralize=p_neutralize), 1e-4) == 0.25
    
    # At and above 0.20 -> exactly 0.0
    assert incumbent_friction_factor(0.20, p_neutralize=p_neutralize) == 0.0
    assert incumbent_friction_factor(0.35, p_neutralize=p_neutralize) == 0.0


def test_single_source_does_not_receive_perfect_agreement_confidence():
    """Mandatory Test 3: Single source returns None and UNAVAILABLE, not 1.0."""
    score, status = source_agreement_score([0.75])
    assert score is None
    assert status == "UNAVAILABLE"

    score_empty, status_empty = source_agreement_score([])
    assert score_empty is None
    assert status_empty == "UNAVAILABLE"

    # Two agreeing sources return high agreement
    score_two, status_two = source_agreement_score([0.70, 0.72])
    assert status_two == "AVAILABLE"
    assert score_two is not None and score_two > 0.95


def test_centered_bounded_acceleration():
    """Test centered tanh acceleration: neutral = 50.0, doubling = 80.0, halving = 20.0."""
    # Neutral: recent == baseline
    score_neutral = centered_bounded_acceleration(100.0, 100.0, k=1.0)
    assert pytest.approx(score_neutral, 1e-3) == 50.0

    # Doubling: ratio 2.0 -> ln(2) = 0.6931 -> tanh(0.6931) = 0.6000 -> 50 + 50*(0.6) = 80.0
    score_double = centered_bounded_acceleration(200.0, 100.0, k=1.0)
    assert pytest.approx(score_double, 0.1) == 80.0

    # Halving: ratio 0.5 -> 50 + 50*(-0.6) = 20.0
    score_half = centered_bounded_acceleration(50.0, 100.0, k=1.0)
    assert pytest.approx(score_half, 0.1) == 20.0

    # Zero recent velocity
    assert centered_bounded_acceleration(0.0, 100.0, k=1.0) == 0.0

    # Extreme acceleration approaches but does not exceed 100
    score_extreme = centered_bounded_acceleration(100000.0, 1.0, k=1.0)
    assert 99.0 < score_extreme <= 100.0


def test_continuous_sigmoid_outlier_penalty():
    """Test continuous sigmoid outlier penalty: strictly [0, 40], never negative, monotonic."""
    # Low concentration: should be very small
    pen_low = continuous_sigmoid_outlier_penalty(top1_share=0.20, top3_share=0.40)
    assert 0.0 <= pen_low < 5.0

    # Even if top3 triggers high while top1 is low, must NEVER go negative
    pen_asymmetric = continuous_sigmoid_outlier_penalty(top1_share=0.30, top3_share=0.85)
    assert 0.0 <= pen_asymmetric <= 40.0

    # High concentration: approaches max 40.0
    pen_high = continuous_sigmoid_outlier_penalty(top1_share=0.85, top3_share=0.98)
    assert 35.0 <= pen_high <= 40.0

    # Monotonicity test
    p1 = continuous_sigmoid_outlier_penalty(top1_share=0.40, top3_share=0.60)
    p2 = continuous_sigmoid_outlier_penalty(top1_share=0.60, top3_share=0.80)
    assert p2 > p1


def test_beta_binomial_shrinkage():
    """Test Bayesian shrinkage: small sample shrinks toward prior; large sample retains signal."""
    # Prior alpha=1, beta=19 (p0 = 1/21 ~ 4.76%)
    # 1 breakout out of 2 eligible: raw=50%, shrunk=(1+1)/(2+1+19) = 2/22 ~ 9.09%
    p_small = beta_binomial_shrinkage(k=1, n=2, alpha=1.0, beta=19.0)
    assert pytest.approx(p_small, 0.001) == 2.0 / 22.0

    # 25 breakouts out of 150: raw=16.67%, shrunk=(25+1)/(150+1+19) = 26/170 ~ 15.29%
    p_large = beta_binomial_shrinkage(k=25, n=150, alpha=1.0, beta=19.0)
    assert pytest.approx(p_large, 0.001) == 26.0 / 170.0

    # Large sample has much higher shrunk rate than the noisy 1/2 sample
    assert p_large > p_small


def test_guarded_topic_runway_metrics():
    """Test mathematical guards for entropy ratio (K<=1) and inter-cluster distance (K<2)."""
    # K = 0
    assert guarded_entropy_ratio([]) == 1.0
    assert guarded_inter_cluster_distance([]) == 1.0

    # K = 1
    assert guarded_entropy_ratio([45]) == 1.0
    assert guarded_inter_cluster_distance([[1.0, 0.0]]) == 1.0

    # K = 2 equal clusters -> max entropy = 1.0
    assert pytest.approx(guarded_entropy_ratio([20, 20]), 1e-4) == 1.0

    # K = 2 orthogonal vectors -> cosine dist = 1.0
    dist_ortho = guarded_inter_cluster_distance([[1.0, 0.0], [0.0, 1.0]])
    assert pytest.approx(dist_ortho, 1e-4) == 1.0

    # K = 2 identical vectors -> cosine dist = 0.0
    dist_ident = guarded_inter_cluster_distance([[1.0, 0.0], [1.0, 0.0]])
    assert pytest.approx(dist_ident, 1e-4) == 0.0


def test_robust_statistics_mad_and_zscore():
    """Test MAD, robust Z-scores, safe_ratio, percentile rank, and winsorization."""
    # Data with extreme outlier
    data = [10.0, 12.0, 11.0, 13.0, 12.0, 1000.0]
    mad = median_absolute_deviation(data)
    # Median of [10, 11, 12, 12, 13, 1000] is 12.0
    # Abs diffs: [2, 1, 0, 0, 1, 988] -> sorted: [0, 0, 1, 1, 2, 988] -> median is 1.0
    assert mad == 1.0

    z_scores = robust_zscore(data)
    assert len(z_scores) == len(data)
    # Normal points have small z-score
    assert abs(z_scores[0]) < 2.0
    # Outlier has high z-score
    assert z_scores[-1] > 10.0

    # Safe ratio
    assert safe_ratio(10.0, 0.0, floor=2.0) == 5.0
    assert safe_ratio(10.0, 5.0, floor=2.0) == 2.0

    # Percentile ranks
    pr = percentile_rank([10, 20, 30, 40, 50], 30)
    assert pr == 60.0

    # Winsorize
    clipped = winsorize([1, 2, 3, 4, 100], lower_pct=0.1, upper_pct=0.9)
    assert clipped[-1] < 100

"""Tests for decoupled composite scoring and decision tree recommendation precedence."""

import pytest
from src.scoring.opportunity import (
    compute_content_opportunity,
    compute_creator_adjusted_opportunity,
    evaluate_recommendation_precedence,
)


def test_content_opportunity_pure_market():
    """Verify Content Opportunity reflects pure market factors with outlier penalty."""
    score, raw = compute_content_opportunity(
        demand_score=80.0,
        supply_scarcity_score=75.0,
        acceleration_score=85.0,
        breakout_score=90.0,
        repeatability_score=80.0,
        durability_score=80.0,
        outlier_penalty=5.0,
    )
    # raw = 0.25*80 + 0.20*75 + 0.18*85 + 0.20*90 + 0.10*80 + 0.07*80 = 20 + 15 + 15.3 + 18 + 8 + 5.6 = 81.9
    assert pytest.approx(raw, 0.1) == 81.9
    # clamped = 81.9 - 5.0 = 76.9
    assert pytest.approx(score, 0.1) == 76.9


def test_creator_adjusted_opportunity_dampening():
    """Verify Creator-Adjusted Opportunity scales deductions and dampens penalties."""
    # Low risk (production=10, rights=5) -> small deduction, near 0 penalty
    adj_low, pen_low = compute_creator_adjusted_opportunity(
        content_opportunity_score=85.0,
        production_risk_score=10.0,
        rights_risk_score=5.0,
    )
    assert pen_low < 8.0
    assert adj_low > 77.0

    # High risk (production=70, rights=80) -> capped penalty
    adj_high, pen_high = compute_creator_adjusted_opportunity(
        content_opportunity_score=85.0,
        production_risk_score=70.0,
        rights_risk_score=80.0,
    )
    assert pen_high <= 40.0
    assert adj_high >= 45.0


def test_recommendation_precedence_deterministic_gates():
    """Verify strictly ordered decision hierarchy handles all gates in exact order."""
    # Gate 1: Insufficient Evidence (confidence < 40 or videos < 10)
    rec1, _ = evaluate_recommendation_precedence(
        confidence_score=35.0,
        eligible_videos=8,
        rights_risk_score=10.0,
        production_risk_score=10.0,
        top1_share=0.2,
        demand_score=80.0,
        supply_scarcity_score=80.0,
        creator_adjusted_opportunity=85.0,
        acceleration_score=80.0,
        breakout_score=80.0,
    )
    assert rec1 == "INSUFFICIENT EVIDENCE"

    # Gate 2: High Rights Risk (>45) even if market is otherwise high opportunity
    rec2, _ = evaluate_recommendation_precedence(
        confidence_score=75.0,
        eligible_videos=40,
        rights_risk_score=60.0,  # Fails Gate 2
        production_risk_score=20.0,
        top1_share=0.2,
        demand_score=80.0,
        supply_scarcity_score=80.0,
        creator_adjusted_opportunity=80.0,
        acceleration_score=80.0,
        breakout_score=80.0,
    )
    assert rec2 == "HIGH RIGHTS RISK"

    # Gate 3: High Production Risk (>55)
    rec3, _ = evaluate_recommendation_precedence(
        confidence_score=75.0,
        eligible_videos=40,
        rights_risk_score=20.0,
        production_risk_score=65.0,  # Fails Gate 3
        top1_share=0.2,
        demand_score=80.0,
        supply_scarcity_score=80.0,
        creator_adjusted_opportunity=80.0,
        acceleration_score=80.0,
        breakout_score=80.0,
    )
    assert rec3 == "HIGH PRODUCTION RISK"

    # Gate 4: Viral Outlier (>0.65)
    rec4, _ = evaluate_recommendation_precedence(
        confidence_score=75.0,
        eligible_videos=40,
        rights_risk_score=20.0,
        production_risk_score=20.0,
        top1_share=0.75,  # Fails Gate 4
        demand_score=80.0,
        supply_scarcity_score=80.0,
        creator_adjusted_opportunity=80.0,
        acceleration_score=80.0,
        breakout_score=80.0,
    )
    assert rec4 == "VIRAL OUTLIER"

    # Gate 5: Weak Demand (<35)
    rec5, _ = evaluate_recommendation_precedence(
        confidence_score=75.0,
        eligible_videos=40,
        rights_risk_score=20.0,
        production_risk_score=20.0,
        top1_share=0.2,
        demand_score=25.0,  # Fails Gate 5
        supply_scarcity_score=80.0,
        creator_adjusted_opportunity=50.0,
        acceleration_score=40.0,
        breakout_score=40.0,
    )
    assert rec5 == "WEAK DEMAND"

    # Gate 6: Saturated (<30)
    rec6, _ = evaluate_recommendation_precedence(
        confidence_score=75.0,
        eligible_videos=40,
        rights_risk_score=20.0,
        production_risk_score=20.0,
        top1_share=0.2,
        demand_score=70.0,
        supply_scarcity_score=20.0,  # Fails Gate 6
        creator_adjusted_opportunity=50.0,
        acceleration_score=40.0,
        breakout_score=40.0,
    )
    assert rec6 == "SATURATED"

    # Gate 7: Strong Opportunity (Opp >= 75, Conf >= 70)
    rec7, _ = evaluate_recommendation_precedence(
        confidence_score=80.0,
        eligible_videos=40,
        rights_risk_score=15.0,
        production_risk_score=20.0,
        top1_share=0.2,
        demand_score=85.0,
        supply_scarcity_score=80.0,
        creator_adjusted_opportunity=78.0,
        acceleration_score=80.0,
        breakout_score=82.0,
    )
    assert rec7 == "STRONG OPPORTUNITY"

    # Gate 8: Promising (Opp >= 65, Conf >= 60)
    rec8, _ = evaluate_recommendation_precedence(
        confidence_score=65.0,
        eligible_videos=30,
        rights_risk_score=15.0,
        production_risk_score=20.0,
        top1_share=0.2,
        demand_score=70.0,
        supply_scarcity_score=70.0,
        creator_adjusted_opportunity=67.0,
        acceleration_score=60.0,
        breakout_score=60.0,
    )
    assert rec8 == "PROMISING"

    # Gate 9: Watchlist (Acceleration >= 65 or Breakout >= 65)
    rec9, _ = evaluate_recommendation_precedence(
        confidence_score=55.0,
        eligible_videos=20,
        rights_risk_score=15.0,
        production_risk_score=20.0,
        top1_share=0.2,
        demand_score=60.0,
        supply_scarcity_score=60.0,
        creator_adjusted_opportunity=60.0,
        acceleration_score=72.0,  # Triggers Watchlist
        breakout_score=50.0,
    )
    assert rec9 == "WATCHLIST"

    # Gate 10: Reject
    rec10, _ = evaluate_recommendation_precedence(
        confidence_score=50.0,
        eligible_videos=20,
        rights_risk_score=20.0,
        production_risk_score=20.0,
        top1_share=0.2,
        demand_score=50.0,
        supply_scarcity_score=50.0,
        creator_adjusted_opportunity=50.0,
        acceleration_score=40.0,
        breakout_score=40.0,
    )
    assert rec10 == "REJECT"

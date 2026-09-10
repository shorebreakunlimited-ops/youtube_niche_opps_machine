"""Composite opportunity scoring and deterministic recommendation engine."""

import math
from typing import Dict, List, Tuple


def compute_content_opportunity(
    demand_score: float,
    supply_scarcity_score: float,
    acceleration_score: float,
    breakout_score: float,
    repeatability_score: float,
    durability_score: float,
    outlier_penalty: float,
) -> Tuple[float, float]:
    """Compute Pure Content Opportunity Score in [0, 100].
    
    CO_raw = 0.25 D + 0.20 S + 0.18 A + 0.20 B + 0.10 R + 0.07 U
    Content Opportunity = clamp(CO_raw - outlier_penalty, 0, 100)
    
    Returns:
    (content_opportunity_score, raw_content_opportunity)
    """
    raw_co = (
        0.25 * demand_score
        + 0.20 * supply_scarcity_score
        + 0.18 * acceleration_score
        + 0.20 * breakout_score
        + 0.10 * repeatability_score
        + 0.07 * durability_score
    )
    clamped_co = max(0.0, min(100.0, raw_co - outlier_penalty))
    return float(clamped_co), float(raw_co)


def compute_creator_adjusted_opportunity(
    content_opportunity_score: float,
    production_risk_score: float,
    rights_risk_score: float,
) -> Tuple[float, float]:
    """Compute practical Creator-Adjusted Opportunity Score in [0, 100].
    
    Deduction = 0.35 * ProdRisk + 0.40 * RightsRisk
    Effective Penalty = 40.0 * tanh(Deduction / 35.0)
    Creator-Adjusted = clamp(ContentOpp - Effective Penalty, 0, 100)
    
    Returns:
    (creator_adjusted_opportunity, effective_penalty)
    """
    deduction = 0.35 * production_risk_score + 0.40 * rights_risk_score
    effective_penalty = 40.0 * math.tanh(deduction / 35.0)
    adjusted_score = max(0.0, min(100.0, content_opportunity_score - effective_penalty))
    return float(adjusted_score), float(effective_penalty)


def evaluate_recommendation_precedence(
    confidence_score: float,
    eligible_videos: int,
    rights_risk_score: float,
    production_risk_score: float,
    top1_share: float,
    demand_score: float,
    supply_scarcity_score: float,
    creator_adjusted_opportunity: float,
    acceleration_score: float,
    breakout_score: float,
) -> Tuple[str, List[str]]:
    """Determine final recommendation via strictly ordered decision tree.
    
    Returns:
    (recommendation_string, reasoning_list)
    """
    reasoning: List[str] = []

    # 1. Insufficient Evidence Gate
    if confidence_score < 40.0 or eligible_videos < 10:
        reasoning.append(
            f"Confidence score ({confidence_score:.1f}) is below 40 or eligible sample ({eligible_videos}) is below 10."
        )
        return "INSUFFICIENT EVIDENCE", reasoning

    # 2. High Rights Risk Gate
    if rights_risk_score > 45.0:
        reasoning.append(
            f"Excessive rights/copyright risk ({rights_risk_score:.1f} > 45.0) creates severe fair-use exposure."
        )
        return "HIGH RIGHTS RISK", reasoning

    # 3. High Production Risk Gate
    if production_risk_score > 55.0:
        reasoning.append(
            f"High operational production burden ({production_risk_score:.1f} > 55.0) for solo AI-assisted creator."
        )
        return "HIGH PRODUCTION RISK", reasoning

    # 4. Viral Outlier Gate
    if top1_share > 0.65:
        reasoning.append(
            f"Single viral outlier controls {top1_share * 100.0:.1f}% of apparent viewership demand."
        )
        return "VIRAL OUTLIER", reasoning

    # 5. Weak Demand Gate
    if demand_score < 35.0:
        reasoning.append(
            f"Overall audience demand velocity ({demand_score:.1f}) is below viable threshold (35.0)."
        )
        return "WEAK DEMAND", reasoning

    # 6. Saturated Competition Gate
    if supply_scarcity_score < 30.0:
        reasoning.append(
            f"Competitor crowding and supply concentration are high (Scarcity score: {supply_scarcity_score:.1f} < 30.0)."
        )
        return "SATURATED", reasoning

    # 7. Strong Opportunity
    if creator_adjusted_opportunity >= 75.0 and confidence_score >= 70.0:
        reasoning.append(
            f"High creator-adjusted opportunity ({creator_adjusted_opportunity:.1f} >= 75) backed by high confidence ({confidence_score:.1f} >= 70)."
        )
        return "STRONG OPPORTUNITY", reasoning

    # 8. Promising
    if creator_adjusted_opportunity >= 65.0 and confidence_score >= 60.0:
        reasoning.append(
            f"Attractive creator-adjusted opportunity ({creator_adjusted_opportunity:.1f} >= 65) with viable evidence ({confidence_score:.1f} >= 60)."
        )
        return "PROMISING", reasoning

    # 9. Watchlist
    if acceleration_score >= 65.0 or breakout_score >= 65.0:
        reasoning.append(
            f"Emerging velocity momentum (Acceleration: {acceleration_score:.1f}) or early breakouts ({breakout_score:.1f})."
        )
        return "WATCHLIST", reasoning

    # 10. Default Reject
    reasoning.append(
        f"Fails to meet minimum opportunity criteria (Creator-Adjusted Score: {creator_adjusted_opportunity:.1f})."
    )
    return "REJECT", reasoning

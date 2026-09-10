from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class BreakoutEvidence:
    channel_id: str
    channel_title: str
    subscribers: Optional[int]
    video_id: str
    video_title: str
    views: int
    baseline_views: float
    breakout_ratio: float
    baseline_tier: str  # 'A', 'B', 'C'


@dataclass
class ValidationResult:
    niche_id: str
    niche_name: str
    content_opportunity_score: float
    creator_adjusted_opportunity: float
    commercial_attractiveness_score: float
    production_feasibility: float
    rights_safety: float
    confidence_score: float
    demand_score: float
    supply_scarcity: float
    acceleration_score: float
    breakout_score: float
    repeatability_score: float
    durability_score: float
    outlier_risk_score: float
    production_risk_score: float
    rights_risk_score: float
    recommendation: str
    reasoning: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    breakout_evidence: List[BreakoutEvidence] = field(default_factory=list)
    top_competitors: List[Dict[str, Any]] = field(default_factory=list)
    topic_clusters: List[Dict[str, Any]] = field(default_factory=list)
    video_ideas: List[str] = field(default_factory=list)
    sample_size: int = 0
    eligible_breakout_videos: int = 0
    validated_at: Optional[datetime] = None
    raw_payload_json: str = "{}"

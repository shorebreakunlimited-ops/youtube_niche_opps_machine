"""Mode B Deep Niche Validator and verification engine."""

from datetime import datetime, timezone
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

from src.collectors.browseract_adapter import BrowserActAdapter
from src.collectors.youtube_client import YouTubeClient
from src.models import BreakoutEvidence, Niche, ValidationResult
from src.scoring.acceleration import compute_acceleration_score
from src.scoring.breakout import compute_breakout_score
from src.scoring.confidence import compute_confidence_score
from src.scoring.demand import compute_demand_score
from src.scoring.monetization import compute_commercial_attractiveness
from src.scoring.opportunity import (
    compute_content_opportunity,
    compute_creator_adjusted_opportunity,
    evaluate_recommendation_precedence,
)
from src.scoring.production_risk import compute_production_risk
from src.scoring.rights_risk import compute_rights_risk
from src.scoring.supply import compute_supply_scarcity_score
from src.storage.cache import SQLiteCache
from src.storage.database import NicheDatabase
from src.validation.outlier_analysis import analyze_outliers

logger = logging.getLogger(__name__)


class NicheValidator:
    """Mode B Deep Niche Validator executing rigorous evidence-based validation."""

    def __init__(
        self,
        youtube_client: Optional[YouTubeClient] = None,
        browser_adapter: Optional[BrowserActAdapter] = None,
        db: Optional[NicheDatabase] = None,
        cache: Optional[SQLiteCache] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.db = db
        self.cache = cache
        self.config = config or {}
        self.youtube_client = youtube_client or YouTubeClient(cache=cache, db=db, use_mock=False)
        self.browser_adapter = browser_adapter or BrowserActAdapter(cache=cache)

    @staticmethod
    def generate_niche_id(name: str) -> str:
        slug = name.lower().strip()
        digest = hashlib.md5(slug.encode("utf-8")).hexdigest()[:12]
        return f"niche_{digest}"

    def validate_niche(
        self,
        niche_query: str,
        creator_profile: Optional[Dict[str, Any]] = None,
        max_videos: int = 50,
        force_refresh: bool = False,
        search_context: str = "validation",
    ) -> ValidationResult:
        """Execute full Mode B validation on a target niche query or seed."""
        clean_name = niche_query.strip()
        niche_id = self.generate_niche_id(clean_name)

        # 1. Collect YouTube search data and channels
        videos, channels, observations = self.youtube_client.search_videos(
            query=clean_name,
            max_results=max_videos,
            search_context=search_context,
        )

        # 2. Collect autocomplete suggestions for topic runway and query demand
        suggestions = self.browser_adapter.get_autocomplete_suggestions(clean_name)

        # 3. Upsert Niche record in database if DB is configured
        if self.db:
            niche_entity = Niche(
                niche_id=niche_id,
                name=clean_name,
            )
            self.db.save_niche(niche_entity)

        # 4. Compute Sub-scores
        demand_score = compute_demand_score(videos)

        (
            breakout_score,
            p_hat_breakout,
            k_breakouts,
            n_eligible,
            breakout_diversity,
            breakout_evidence,
            avg_tier_conf,
        ) = compute_breakout_score(videos, channels)

        (
            supply_scarcity,
            hhi_index,
            incumbent_share,
            gamma_friction,
        ) = compute_supply_scarcity_score(
            videos, channels, p_hat_breakout=p_hat_breakout, p_neutralize=0.20
        )

        acceleration_score = compute_acceleration_score(videos)

        # Topic runway / Repeatability:
        # Number of unique angles from autocomplete suggestions and video titles
        distinct_topics = set(s.lower() for s in suggestions)
        for v in videos:
            words = [w for w in v.title.lower().split() if len(w) > 4]
            if len(words) >= 2:
                distinct_topics.add(" ".join(words[:2]))
        runway_count = len(distinct_topics)
        # Scale: weak <=15, limited <=35, workable <=70, strong >=120
        repeatability_score = min(100.0, max(10.0, (runway_count / 80.0) * 100.0))

        # Durability:
        # Proportion of videos published >90 days ago that still maintain healthy views
        old_videos = [v for v in videos if v.video_age_days > 90]
        if old_videos:
            durable_ratio = sum(1 for v in old_videos if v.views >= 5000) / len(old_videos)
            durability_score = min(100.0, max(20.0, durable_ratio * 100.0 + 20.0))
        else:
            durability_score = 65.0  # Fresh niche baseline

        # Outlier Analysis:
        (
            outlier_penalty,
            top1_share,
            top3_share,
            is_viral_risk,
            view_quantiles,
        ) = analyze_outliers(videos)

        # Pure Content Opportunity (pure market demand/supply/momentum/breakout):
        content_opportunity, raw_co = compute_content_opportunity(
            demand_score=demand_score,
            supply_scarcity_score=supply_scarcity,
            acceleration_score=acceleration_score,
            breakout_score=breakout_score,
            repeatability_score=repeatability_score,
            durability_score=durability_score,
            outlier_penalty=outlier_penalty,
        )

        # Commercial Attractiveness:
        commercial_attractiveness = compute_commercial_attractiveness(clean_name)

        # Production Feasibility:
        custom_prod = creator_profile.get("production") if creator_profile else None
        prod_risk = compute_production_risk(clean_name, custom_ratings=custom_prod)
        production_feasibility = 100.0 - prod_risk

        # Rights Safety:
        custom_rights = creator_profile.get("rights") if creator_profile else None
        rights_risk = compute_rights_risk(clean_name, custom_ratings=custom_rights)
        rights_safety = 100.0 - rights_risk

        # Creator-Adjusted Opportunity:
        (
            creator_adjusted_opp,
            creator_penalty,
        ) = compute_creator_adjusted_opportunity(
            content_opportunity_score=content_opportunity,
            production_risk_score=prod_risk,
            rights_risk_score=rights_risk,
        )

        # Multi-source demand indices for confidence
        source_indices = []
        if len(videos) > 0:
            source_indices.append(demand_score)
        if len(suggestions) > 0:
            # Suggestion depth proxy in [0, 100]
            source_indices.append(min(100.0, len(suggestions) * 10.0))

        confidence_score, agreement_score, status = compute_confidence_score(
            video_count=len(videos),
            snapshot_coverage_ratio=0.0,
            avg_breakout_tier_confidence=avg_tier_conf,
            source_demand_indices=source_indices if len(source_indices) >= 2 else None,
        )

        # Deterministic Recommendation via strictly ordered precedence
        recommendation, reasoning = evaluate_recommendation_precedence(
            confidence_score=confidence_score,
            eligible_videos=len(videos),
            rights_risk_score=rights_risk,
            production_risk_score=prod_risk,
            top1_share=top1_share,
            demand_score=demand_score,
            supply_scarcity_score=supply_scarcity,
            creator_adjusted_opportunity=creator_adjusted_opp,
            acceleration_score=acceleration_score,
            breakout_score=breakout_score,
        )

        # Assemble risks
        risks: List[str] = []
        if is_viral_risk:
            risks.append(f"Viral outlier concentration: Top video holds {top1_share * 100.0:.1f}% of total views.")
        if incumbent_share > 0.50:
            risks.append(f"Heavy incumbent domination: Large channels (>250k subs) command {incumbent_share * 100.0:.1f}% of view share.")
        if rights_risk > 35.0:
            risks.append(f"Rights risk elevated ({rights_risk:.1f}/100): requires third-party footage or media clearance.")
        if prod_risk > 45.0:
            risks.append(f"High production load ({prod_risk:.1f}/100): difficult for solo automated pipeline.")
        if confidence_score < 50.0:
            risks.append(f"Low confidence ({confidence_score:.1f}/100): limited sample size or single data source.")

        # Top Competitors
        channel_view_sums: Dict[str, int] = {}
        for v in videos:
            channel_view_sums[v.channel_id] = channel_view_sums.get(v.channel_id, 0) + v.views

        sorted_cids = sorted(channel_view_sums.keys(), key=lambda cid: channel_view_sums[cid], reverse=True)
        top_competitors = []
        tot_views = max(1, sum(v.views for v in videos))
        for cid in sorted_cids[:5]:
            ch = channels.get(cid)
            c_views = channel_view_sums[cid]
            top_competitors.append(
                {
                    "channel_id": cid,
                    "title": ch.title if ch else "Unknown",
                    "subscribers": ch.subscribers if ch else None,
                    "video_count": ch.video_count if ch else None,
                    "views_in_niche": c_views,
                    "view_share_pct": round((c_views / tot_views) * 100.0, 1),
                }
            )

        # Video Ideas from autocomplete and high-velocity formats
        video_ideas = [
            f"Complete Beginner Guide to {clean_name.title()}",
            f"Top 5 Mistakes in {clean_name.title()} (And How to Avoid Them)",
            f"{clean_name.title()} Full Workflow Walkthrough for 2026",
            f"The Untold Truth About {clean_name.title()}",
            f"How I Built a {clean_name.title()} System From Scratch",
        ]
        if suggestions:
            for s in suggestions[:5]:
                formatted_idea = s.title()
                if formatted_idea not in video_ideas:
                    video_ideas.append(formatted_idea)

        result = ValidationResult(
            niche_id=niche_id,
            niche_name=clean_name,
            content_opportunity_score=round(content_opportunity, 2),
            creator_adjusted_opportunity=round(creator_adjusted_opp, 2),
            commercial_attractiveness_score=round(commercial_attractiveness, 2),
            production_feasibility=round(production_feasibility, 2),
            rights_safety=round(rights_safety, 2),
            confidence_score=round(confidence_score, 2),
            demand_score=round(demand_score, 2),
            supply_scarcity=round(supply_scarcity, 2),
            acceleration_score=round(acceleration_score, 2),
            breakout_score=round(breakout_score, 2),
            repeatability_score=round(repeatability_score, 2),
            durability_score=round(durability_score, 2),
            outlier_risk_score=round(outlier_penalty, 2),
            production_risk_score=round(prod_risk, 2),
            rights_risk_score=round(rights_risk, 2),
            recommendation=recommendation,
            reasoning=reasoning,
            risks=risks,
            breakout_evidence=breakout_evidence,
            top_competitors=top_competitors,
            topic_clusters=[{"topic": s, "type": "autocomplete"} for s in suggestions[:8]],
            video_ideas=video_ideas[:8],
            sample_size=len(videos),
            eligible_breakout_videos=n_eligible,
            validated_at=datetime.now(timezone.utc),
            raw_payload_json=json.dumps(
                {
                    "hhi_index": round(hhi_index, 4),
                    "incumbent_share": round(incumbent_share, 4),
                    "gamma_friction": round(gamma_friction, 4),
                    "breakout_diversity": round(breakout_diversity, 4),
                    "p_hat_breakout": round(p_hat_breakout, 4),
                    "creator_penalty": round(creator_penalty, 2),
                    "view_quantiles": view_quantiles,
                }
            ),
        )

        if self.db:
            self.db.save_validation_snapshot(result)

        return result

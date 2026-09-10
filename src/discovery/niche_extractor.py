"""Mode A Automated Niche Discovery and ranking engine."""

from typing import Any, Dict, List, Optional
from src.collectors.browseract_adapter import BrowserActAdapter
from src.discovery.query_expander import QueryExpander
from src.discovery.semantic_deduper import SemanticDeduper
from src.models import ValidationResult
from src.validation.niche_validator import NicheValidator


class NicheExtractor:
    """Mode A Automated Discovery engine extracting and ranking candidate subniches.
    
    IMPORTANT ARCHITECTURAL DIRECTIVE:
    Discovery strictly ranks candidates on Content Opportunity Score with Confidence gating.
    Creator-Adjusted Opportunity is preserved on each result for the user's decision layer,
    but is strictly withheld from discovery ranking.
    """

    def __init__(
        self,
        validator: NicheValidator,
        query_expander: Optional[QueryExpander] = None,
        deduper: Optional[SemanticDeduper] = None,
        browser_adapter: Optional[BrowserActAdapter] = None,
    ):
        self.validator = validator
        self.expander = query_expander or QueryExpander()
        self.deduper = deduper or SemanticDeduper()
        self.browser_adapter = browser_adapter or self.validator.browser_adapter

    def discover_subniches(
        self,
        seed_topic: str,
        max_candidates: int = 10,
        min_confidence_gate: float = 40.0,
        creator_profile: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Discover, evaluate, and rank candidate subniches for a given root seed."""
        # 1. Expand seed across 15 universal axes and interrogatives
        expanded_queries = self.expander.expand_seed_across_15_axes(seed_topic)
        interrogatives = self.expander.generate_interrogative_probes(seed_topic)

        # 2. Gather autocomplete suggestions for subniche candidates
        raw_candidates = [seed_topic]
        # Query suggestions for top axis queries
        for q_obj in expanded_queries[:8]:
            suggs = self.browser_adapter.get_autocomplete_suggestions(q_obj["query"])
            raw_candidates.extend(suggs[:3])

        for q_str in interrogatives[:4]:
            suggs = self.browser_adapter.get_autocomplete_suggestions(q_str)
            raw_candidates.extend(suggs[:3])

        # 3. Deduplicate candidates to eliminate near-duplicate keywords
        clean_candidates = self.deduper.deduplicate_candidates(
            raw_candidates, similarity_threshold=0.75
        )

        # Limit to evaluation budget
        eval_candidates = clean_candidates[:max_candidates]
        if seed_topic not in eval_candidates:
            eval_candidates.insert(0, seed_topic)

        # 4. Validate each candidate niche through Mode B validator
        validated_results: List[ValidationResult] = []
        for cand in eval_candidates:
            res = self.validator.validate_niche(
                niche_query=cand,
                creator_profile=creator_profile,
                max_videos=25,
                search_context="discovery",
            )
            validated_results.append(res)

        # 5. Apply Confidence Gating & Pure Content Opportunity Ranking
        # Directive: Rank on Content Opportunity + Confidence gating.
        # Creator-adjusted opportunity affects only the user-facing decision layer.
        eligible_candidates = [
            r for r in validated_results if r.confidence_score >= min_confidence_gate
        ]
        # If none pass the gate, fall back to top by confidence
        if not eligible_candidates:
            eligible_candidates = validated_results

        # Sort strictly by content_opportunity_score descending
        ranked_candidates = sorted(
            eligible_candidates,
            key=lambda r: (r.content_opportunity_score, r.confidence_score),
            reverse=True,
        )

        # 6. Format output leaderboard
        leaderboard = []
        for rank, res in enumerate(ranked_candidates, start=1):
            leaderboard.append(
                {
                    "rank": rank,
                    "niche_name": res.niche_name,
                    "content_opportunity_score": res.content_opportunity_score,
                    "confidence_score": res.confidence_score,
                    "demand_score": res.demand_score,
                    "supply_scarcity": res.supply_scarcity,
                    "breakout_score": res.breakout_score,
                    "acceleration_score": res.acceleration_score,
                    "repeatability_score": res.repeatability_score,
                    "recommendation": res.recommendation,
                    # Creator-adjusted score preserved for decision layer only:
                    "creator_adjusted_opportunity": res.creator_adjusted_opportunity,
                    "production_feasibility": res.production_feasibility,
                    "rights_safety": res.rights_safety,
                    "validation_result": res,
                }
            )

        return leaderboard

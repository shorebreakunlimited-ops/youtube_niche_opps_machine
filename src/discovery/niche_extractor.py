"""Mode A Automated Niche Discovery and ranking engine."""

import logging
import re
from typing import Any, Dict, List, Optional, Set
import numpy as np

from src.collectors.browseract_adapter import BrowserActAdapter
from src.discovery.query_expander import QueryExpander
from src.discovery.semantic_deduper import SemanticDeduper
from src.models import ValidationResult
from src.validation.niche_validator import NicheValidator

logger = logging.getLogger(__name__)


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

    def cluster_candidates_semantically(
        self,
        candidates: List[str],
        distance_threshold: float = 0.40,
    ) -> List[Dict[str, Any]]:
        """Cluster candidate phrases into coherent thematic groups using TF-IDF token vectors."""
        if not candidates:
            return []
        
        # Build token vocabulary
        tokenized = []
        vocab = set()
        for cand in candidates:
            tokens = re.findall(r"\b[a-z]{3,}\b", cand.lower())
            tokenized.append(tokens)
            vocab.update(tokens)
            
        vocab_list = sorted(vocab)
        vocab_map = {w: i for i, w in enumerate(vocab_list)}
        v_size = max(1, len(vocab_map))
        
        # Vectors
        vecs = []
        for tokens in tokenized:
            vec = np.zeros(v_size)
            for t in tokens:
                if t in vocab_map:
                    vec[vocab_map[t]] += 1.0
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            vecs.append(vec)
            
        # Agglomerative / leader clustering
        clusters: List[Dict[str, Any]] = []
        for i, cand in enumerate(candidates):
            v_cand = vecs[i]
            assigned = False
            for cl in clusters:
                centroid = cl["centroid"]
                cos_sim = float(np.dot(v_cand, centroid))
                cos_dist = 1.0 - cos_sim
                if cos_dist <= distance_threshold:
                    cl["members"].append(cand)
                    # Update centroid
                    new_cent = cl["centroid"] + v_cand
                    norm = np.linalg.norm(new_cent)
                    cl["centroid"] = new_cent / norm if norm > 0 else new_cent
                    assigned = True
                    break
            if not assigned:
                clusters.append({
                    "cluster_name": cand,
                    "centroid": v_cand,
                    "members": [cand],
                })
                
        return clusters

    def discover_subniches(
        self,
        seed_topic: str,
        max_candidates: int = 10,
        min_confidence_gate: float = 40.0,
        creator_profile: Optional[Dict[str, Any]] = None,
        enable_graph_traversal: bool = True,
    ) -> List[Dict[str, Any]]:
        """Discover, evaluate, and rank candidate subniches for a given root seed.
        
        Executes a multi-tier exploratory discovery loop:
        1. 15-axis universal query generation & interrogatives
        2. Recursive 2-level alphabet tree probing
        3. Search-result graph traversal (inspecting related video titles & channel cohorts)
        4. TF-IDF candidate clustering & Jaccard deduplication
        5. Deep validation on top cluster representatives
        6. Pure Content Opportunity ranking with Confidence gating
        """
        clean_seed = seed_topic.strip()
        raw_candidates: List[str] = [clean_seed]

        # 1. 15-axis universal queries & interrogatives
        expanded_queries = self.expander.expand_seed_across_15_axes(clean_seed)
        interrogatives = self.expander.generate_interrogative_probes(clean_seed)

        for q_obj in expanded_queries[:10]:
            suggs = self.browser_adapter.get_autocomplete_suggestions(q_obj["query"])
            raw_candidates.extend(suggs[:4])

        for q_str in interrogatives[:6]:
            suggs = self.browser_adapter.get_autocomplete_suggestions(q_str)
            raw_candidates.extend(suggs[:4])

        # 2. Recursive alphabet tree probing (A-Z tree exploration)
        alphabet_probes = self.expander.generate_recursive_alphabet_probes(clean_seed, top_letters="abcdefst")
        for probe in alphabet_probes:
            suggs = self.browser_adapter.get_autocomplete_suggestions(probe)
            raw_candidates.extend(suggs[:3])

        # 3. Search-result graph expansion: traverse top video titles & channels from initial search
        if enable_graph_traversal and self.validator.youtube_client:
            try:
                seed_videos, _, _ = self.validator.youtube_client.search_videos(
                    query=clean_seed,
                    max_results=15,
                    search_context="discovery_graph_seed",
                )
                for sv in seed_videos:
                    # Extract recurring substantive noun phrases (2-4 words) from video titles
                    words = re.findall(r"\b[A-Za-z0-9\-\.]{4,}\b", sv.title)
                    if len(words) >= 2:
                        phrase = f"{clean_seed} {' '.join(words[:2]).lower()}"
                        raw_candidates.append(phrase)
            except Exception as e:
                logger.warning(f"Discovery graph traversal encountered non-fatal error: {e}")

        # 4. Semantic deduplication & candidate clustering
        deduped = self.deduper.deduplicate_candidates(
            raw_candidates, similarity_threshold=0.70
        )

        clusters = self.cluster_candidates_semantically(deduped, distance_threshold=0.35)
        # Pick top cluster representatives (ensures diverse thematic coverage across discovered clusters)
        clustered_candidates = [cl["cluster_name"] for cl in clusters]

        # Ensure seed topic is evaluated
        if clean_seed not in clustered_candidates:
            clustered_candidates.insert(0, clean_seed)

        eval_candidates = clustered_candidates[:max_candidates]

        # 5. Validate each candidate niche through Mode B validator
        validated_results: List[ValidationResult] = []
        for cand in eval_candidates:
            res = self.validator.validate_niche(
                niche_query=cand,
                creator_profile=creator_profile,
                max_videos=25,
                search_context="discovery",
            )
            validated_results.append(res)

        # 6. Apply Confidence Gating & Pure Content Opportunity Ranking
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

        # 7. Format output leaderboard
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

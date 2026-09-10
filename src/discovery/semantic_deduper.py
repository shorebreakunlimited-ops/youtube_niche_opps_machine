"""Semantic deduplication and canonical cluster extraction."""

import re
from typing import Dict, List, Set


class SemanticDeduper:
    """Removes redundant queries, candidate niches, and video concepts using token set distance."""

    @staticmethod
    def _tokenize(text: str) -> Set[str]:
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        tokens = [w for w in cleaned.split() if len(w) > 2]
        return set(tokens)

    @classmethod
    def token_jaccard_similarity(cls, text_a: str, text_b: str) -> float:
        set_a = cls._tokenize(text_a)
        set_b = cls._tokenize(text_b)
        if not set_a and not set_b:
            return 1.0
        if not set_a or not set_b:
            return 0.0
        intersection = len(set_a.intersection(set_b))
        union = len(set_a.union(set_b))
        return float(intersection / union)

    @classmethod
    def deduplicate_candidates(
        cls, candidates: List[str], similarity_threshold: float = 0.80
    ) -> List[str]:
        """Deduplicate a list of candidate niche names or queries preserving first occurrence."""
        unique_candidates: List[str] = []
        for cand in candidates:
            clean = cand.strip()
            if not clean:
                continue
            is_duplicate = False
            for existing in unique_candidates:
                # Substring equivalence check for near-identical phrases
                if clean.lower() == existing.lower():
                    is_duplicate = True
                    break
                sim = cls.token_jaccard_similarity(clean, existing)
                if sim >= similarity_threshold:
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_candidates.append(clean)
        return unique_candidates

    @classmethod
    def cluster_topics(
        cls, topics: List[str], similarity_threshold: float = 0.65
    ) -> Dict[str, List[str]]:
        """Cluster a collection of topic strings by semantic similarity."""
        clusters: Dict[str, List[str]] = {}
        for topic in topics:
            clean = topic.strip()
            if not clean:
                continue
            assigned = False
            for canonical in clusters.keys():
                sim = cls.token_jaccard_similarity(clean, canonical)
                if sim >= similarity_threshold:
                    clusters[canonical].append(clean)
                    assigned = True
                    break
            if not assigned:
                clusters[clean] = [clean]
        return clusters

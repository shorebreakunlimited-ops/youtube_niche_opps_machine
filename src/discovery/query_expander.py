"""Query expander leveraging the 15 universal domain-neutral axes and depth probing."""

from typing import Dict, List, Optional
from src.validation.topic_depth import UNIVERSAL_15_AXES


class QueryExpander:
    """Expands seeds into systematic search and autocomplete queries across 15 universal axes."""

    def __init__(self, universal_axes: Optional[Dict[str, Dict]] = None):
        self.axes = universal_axes or UNIVERSAL_15_AXES

    def expand_seed_across_15_axes(self, seed: str) -> List[Dict[str, str]]:
        """Generate targeted search queries across all 15 universal domain-neutral axes."""
        clean_seed = seed.strip()
        queries = []

        for axis_key, axis_meta in self.axes.items():
            for kw in axis_meta["keywords"][:2]:  # Top 2 representative keywords per axis
                if kw in ("for beginners", "basics", "101"):
                    q = f"{clean_seed} {kw}"
                elif kw in ("vs", "versus"):
                    q = f"{clean_seed} {kw}"
                elif kw in ("how to build", "how to fix", "how to monetize"):
                    action = kw.replace("how to ", "")
                    q = f"how to {action} {clean_seed}"
                else:
                    q = f"{clean_seed} {kw}"

                queries.append(
                    {
                        "query": q,
                        "axis_id": axis_meta["axis_id"],
                        "axis_name": axis_meta["name"],
                        "intent_type": axis_key,
                    }
                )

        return queries

    def generate_autocomplete_alphabet_probes(self, seed: str) -> List[str]:
        """Generate 26 A-Z alphabetical queries for depth suggestion discovery."""
        clean_seed = seed.strip()
        return [f"{clean_seed} {c}" for c in "abcdefghijklmnopqrstuvwxyz"]

    def generate_recursive_alphabet_probes(self, seed: str, top_letters: str = "abcst") -> List[str]:
        """Generate focused recursive 2-level alphabet tree probes for deep discovery."""
        clean_seed = seed.strip()
        probes = []
        for c in top_letters:
            probes.append(f"{clean_seed} {c}")
        return probes

    def generate_interrogative_probes(self, seed: str) -> List[str]:
        """Generate interrogative question-intent probes."""
        clean_seed = seed.strip()
        return [
            f"how to use {clean_seed}",
            f"why use {clean_seed}",
            f"best {clean_seed} tutorial",
            f"what is {clean_seed}",
            f"can you {clean_seed}",
            f"{clean_seed} explained simply",
        ]

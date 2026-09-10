"""Discovery expansion and automated candidate niche extraction."""

from src.discovery.query_expander import QueryExpander
from src.discovery.semantic_deduper import SemanticDeduper
from src.discovery.niche_extractor import NicheExtractor

__all__ = ["QueryExpander", "SemanticDeduper", "NicheExtractor"]

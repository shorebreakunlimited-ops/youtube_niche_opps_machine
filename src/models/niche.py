from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Niche:
    niche_id: str
    name: str
    market: Optional[str] = None
    subniche: Optional[str] = None
    format: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class NicheVideoMembership:
    niche_id: str
    video_id: str
    relevance_score: float
    primary_cluster_id: Optional[str] = None
    first_seen_in_niche: Optional[datetime] = None
    last_seen_in_niche: Optional[datetime] = None


@dataclass
class NicheVideoDiscovery:
    run_id: str
    niche_id: str
    video_id: str
    discovery_method: str
    originating_query: str
    rank_position: Optional[int] = None
    observed_at: Optional[datetime] = None
    id: Optional[int] = None

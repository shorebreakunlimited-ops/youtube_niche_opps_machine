from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class SearchRankObservation:
    run_id: str
    query: str
    video_id: str
    rank_position: int
    observed_at: Optional[datetime] = None
    region: str = "US"
    language: str = "en"
    order_param: str = "relevance"
    device_context: str = "desktop"
    search_context: str = "api"
    id: Optional[int] = None


@dataclass
class RawObservation:
    run_id: str
    niche_id: str
    source: str
    query: str
    metrics_json: str
    video_id: Optional[str] = None
    channel_id: Optional[str] = None
    collected_at: Optional[datetime] = None
    id: Optional[int] = None

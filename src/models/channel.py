from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ChannelMetricSnapshot:
    channel_id: str
    observed_at: datetime
    subscribers: Optional[int] = None
    total_views: Optional[int] = None
    video_count: Optional[int] = None
    id: Optional[int] = None


@dataclass
class Channel:
    channel_id: str
    title: str
    custom_url: Optional[str] = None
    subscribers: Optional[int] = None
    total_views: Optional[int] = None
    video_count: Optional[int] = None
    median_recent_views: Optional[float] = None
    created_at: Optional[str] = None
    first_seen_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    @property
    def is_subscriber_count_known(self) -> bool:
        return self.subscribers is not None and self.subscribers >= 0

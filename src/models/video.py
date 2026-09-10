from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class VideoMetricSnapshot:
    video_id: str
    observed_at: datetime
    views: int
    likes: Optional[int] = None
    comments: Optional[int] = None
    id: Optional[int] = None


@dataclass
class Video:
    video_id: str
    channel_id: str
    title: str
    published_at: str
    views: int
    likes: Optional[int] = None
    comments: Optional[int] = None
    duration: Optional[str] = None
    category_id: Optional[str] = None
    first_seen_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    @property
    def published_datetime(self) -> datetime:
        dt_str = self.published_at.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(dt_str)
        except Exception:
            return datetime.now(timezone.utc)

    @property
    def video_age_days(self) -> float:
        now = datetime.now(timezone.utc)
        pub = self.published_datetime
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        delta_days = (now - pub).total_seconds() / 86400.0
        return max(0.001, delta_days)

    @property
    def lifetime_proxy_velocity(self) -> float:
        """Lifetime views divided by age in days."""
        return self.views / max(self.video_age_days, 1.0)

    @property
    def likes_per_1000_views(self) -> float:
        if self.views <= 0 or self.likes is None:
            return 0.0
        return (self.likes / self.views) * 1000.0

    @property
    def comments_per_1000_views(self) -> float:
        if self.views <= 0 or self.comments is None:
            return 0.0
        return (self.comments / self.views) * 1000.0

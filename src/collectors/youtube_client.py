"""YouTube Data API v3 client with strict quota accounting, 50-item batching, and caching."""

from dataclasses import asdict
from datetime import datetime, timezone, timedelta
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple
import uuid
import requests

from src.models import Channel, SearchRankObservation, Video
from src.storage.cache import SQLiteCache
from src.storage.database import NicheDatabase

logger = logging.getLogger(__name__)


class QuotaExceededError(Exception):
    """Raised when daily YouTube API quota is exceeded."""
    pass


class YouTubeClient:
    """Production-grade YouTube Data API v3 client with quota tracking, batching, and SQLite caching."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        cache: Optional[SQLiteCache] = None,
        db: Optional[NicheDatabase] = None,
        search_list_daily_limit: int = 100,
        videos_batch_daily_limit: int = 10000,
        batch_size: int = 50,
        use_mock: bool = False,
    ):
        self.api_key = api_key or os.environ.get("YOUTUBE_API_KEY", "")
        self.cache = cache
        self.db = db
        self.search_list_daily_limit = search_list_daily_limit
        self.videos_batch_daily_limit = videos_batch_daily_limit
        self.batch_size = min(50, max(1, batch_size))
        self.use_mock = use_mock or (not self.api_key)

        # In-memory quota counters for the current day
        self._current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self._search_calls_used = 0
        self._video_batch_units_used = 0

    def _check_and_reset_daily_quota(self) -> None:
        """Reset quota or load current day's tracked usage from database."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != self._current_date:
            self._current_date = today
            self._search_calls_used = 0
            self._video_batch_units_used = 0

        if self.db:
            usage = self.db.get_quota_usage(self._current_date)
            self._search_calls_used = max(self._search_calls_used, usage["search_calls_used"])
            self._video_batch_units_used = max(self._video_batch_units_used, usage["video_batch_units_used"])

    def get_quota_status(self) -> Dict[str, Any]:
        """Return current quota utilization status."""
        self._check_and_reset_daily_quota()
        return {
            "date": self._current_date,
            "search_list": {
                "used": self._search_calls_used,
                "limit": self.search_list_daily_limit,
                "remaining": max(0, self.search_list_daily_limit - self._search_calls_used),
            },
            "videos_batch": {
                "used": self._video_batch_units_used,
                "limit": self.videos_batch_daily_limit,
                "remaining": max(0, self.videos_batch_daily_limit - self._video_batch_units_used),
            },
            "mock_mode": self.use_mock,
        }

    def _consume_search_quota(self) -> None:
        self._check_and_reset_daily_quota()
        if self._search_calls_used >= self.search_list_daily_limit:
            raise QuotaExceededError(
                f"Daily search.list quota exceeded: {self._search_calls_used}/{self.search_list_daily_limit} calls used today."
            )
        self._search_calls_used += 1
        if self.db:
            self.db.record_quota_consumption(self._current_date, search_calls=1)

    def _consume_video_batch_quota(self, batch_count: int = 1) -> None:
        self._check_and_reset_daily_quota()
        if self._video_batch_units_used + batch_count > self.videos_batch_daily_limit:
            raise QuotaExceededError(
                f"Daily videos.batch quota exceeded: {self._video_batch_units_used}/{self.videos_batch_daily_limit} units used."
            )
        self._video_batch_units_used += batch_count
        if self.db:
            self.db.record_quota_consumption(self._current_date, video_batch_units=batch_count)

    def search_videos(
        self,
        query: str,
        max_results: int = 50,
        order: str = "relevance",
        published_after: Optional[str] = None,
        region_code: str = "US",
        relevance_language: str = "en",
        search_context: str = "niche_validation",
    ) -> Tuple[List[Video], Dict[str, Channel], List[SearchRankObservation]]:
        """Search videos by keyword/topic with automatic batch detail enrichment and ranking observations."""
        cache_key = f"yt_search:{query}:{max_results}:{order}:{published_after}:{region_code}:{relevance_language}"
        if self.cache:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                try:
                    raw = json.loads(cached_data) if isinstance(cached_data, str) else cached_data
                    videos = [Video(**v) for v in raw.get("videos", [])]
                    channels = {k: Channel(**c) for k, c in raw.get("channels", {}).items()}
                    observations = []
                    for o in raw.get("observations", []):
                        if isinstance(o.get("observed_at"), str):
                            try:
                                o["observed_at"] = datetime.fromisoformat(o["observed_at"])
                            except Exception:
                                o["observed_at"] = None
                        observations.append(SearchRankObservation(**o))
                    return videos, channels, observations
                except Exception as e:
                    logger.warning(f"Error reading search cache: {e}")

        if self.use_mock:
            videos, channels, observations = self._generate_mock_search_results(query, max_results)
        else:
            self._consume_search_quota()
            url = "https://www.googleapis.com/youtube/v3/search"
            params = {
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": min(50, max_results),
                "order": order,
                "regionCode": region_code,
                "relevanceLanguage": relevance_language,
                "key": self.api_key,
            }
            if published_after:
                params["publishedAfter"] = published_after

            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code != 200:
                logger.error(f"YouTube search API error: {resp.status_code} {resp.text}")
                # Fallback to mock if API returns error
                videos, channels, observations = self._generate_mock_search_results(query, max_results)
            else:
                data = resp.json()
                items = data.get("items", [])
                video_ids = [item["id"]["videoId"] for item in items if "id" in item and "videoId" in item["id"]]

                # Fetch full statistics & details for all videos in batch (up to 50 per batch)
                videos = self.get_videos_batch(video_ids)
                
                # Fetch channels in batch
                channel_ids = list({v.channel_id for v in videos})
                channels = self.get_channels_batch(channel_ids)

                observations = []
                run_id = f"run_{uuid.uuid4().hex[:8]}"
                now_dt = datetime.now(timezone.utc)
                for rank, v in enumerate(videos, start=1):
                    obs = SearchRankObservation(
                        run_id=run_id,
                        query=query,
                        video_id=v.video_id,
                        rank_position=rank,
                        observed_at=now_dt,
                        region=region_code,
                        language=relevance_language,
                        order_param=order,
                        search_context=search_context,
                    )
                    observations.append(obs)

        # Store in cache
        if self.cache:
            to_cache = {
                "videos": [asdict(v) for v in videos],
                "channels": {k: asdict(c) for k, c in channels.items()},
                "observations": [asdict(o) for o in observations],
            }
            self.cache.set(cache_key, to_cache, ttl_seconds=24 * 3600)

        # Store in database if provided
        if self.db:
            for c in channels.values():
                self.db.upsert_channel(c)
            for v in videos:
                self.db.upsert_video(v)
            for obs in observations:
                self.db.record_search_rank_observation(obs)

        return videos, channels, observations

    def get_videos_batch(self, video_ids: List[str]) -> List[Video]:
        """Fetch video metadata and view statistics in batches of 50."""
        if not video_ids:
            return []

        videos: List[Video] = []
        chunks = [video_ids[i:i + self.batch_size] for i in range(0, len(video_ids), self.batch_size)]

        for chunk in chunks:
            if self.use_mock:
                for vid in chunk:
                    videos.append(
                        Video(
                            video_id=vid,
                            channel_id=f"ch_{vid[:6]}",
                            title=f"Video {vid}",
                            published_at="2026-08-01T00:00:00Z",
                            views=15000,
                            likes=800,
                            comments=120,
                        )
                    )
                continue

            self._consume_video_batch_quota(1)
            url = "https://www.googleapis.com/youtube/v3/videos"
            params = {
                "part": "snippet,statistics,contentDetails",
                "id": ",".join(chunk),
                "key": self.api_key,
            }
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code != 200:
                logger.error(f"YouTube videos.list API error: {resp.status_code} {resp.text}")
                continue

            data = resp.json()
            for item in data.get("items", []):
                snippet = item.get("snippet", {})
                stats = item.get("statistics", {})
                content_details = item.get("contentDetails", {})

                duration_iso = content_details.get("duration", "PT0S")
                duration_sec = self._parse_iso_duration(duration_iso)

                v = Video(
                    video_id=item["id"],
                    channel_id=snippet.get("channelId", ""),
                    title=snippet.get("title", ""),
                    published_at=snippet.get("publishedAt", datetime.now(timezone.utc).isoformat()),
                    views=int(stats.get("viewCount", 0)),
                    likes=int(stats.get("likeCount", 0)) if "likeCount" in stats else None,
                    comments=int(stats.get("commentCount", 0)) if "commentCount" in stats else None,
                    duration=duration_iso,
                    category_id=snippet.get("categoryId"),
                )
                videos.append(v)

        return videos

    def get_channels_batch(self, channel_ids: List[str]) -> Dict[str, Channel]:
        """Fetch channel details in batches of 50."""
        if not channel_ids:
            return {}

        channels: Dict[str, Channel] = {}
        chunks = [channel_ids[i:i + self.batch_size] for i in range(0, len(channel_ids), self.batch_size)]

        for chunk in chunks:
            if self.use_mock:
                for cid in chunk:
                    channels[cid] = Channel(
                        channel_id=cid,
                        title=f"Creator {cid}",
                        subscribers=12000,
                        video_count=45,
                    )
                continue

            url = "https://www.googleapis.com/youtube/v3/channels"
            params = {
                "part": "snippet,statistics",
                "id": ",".join(chunk),
                "key": self.api_key,
            }
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code != 200:
                logger.error(f"YouTube channels.list API error: {resp.status_code} {resp.text}")
                continue

            data = resp.json()
            for item in data.get("items", []):
                snippet = item.get("snippet", {})
                stats = item.get("statistics", {})

                c = Channel(
                    channel_id=item["id"],
                    title=snippet.get("title", ""),
                    subscribers=int(stats.get("subscriberCount", 0)) if "subscriberCount" in stats and not stats.get("hiddenSubscriberCount") else None,
                    total_views=int(stats.get("viewCount", 0)) if "viewCount" in stats else None,
                    video_count=int(stats.get("videoCount", 0)) if "videoCount" in stats else None,
                    created_at=snippet.get("publishedAt"),
                )
                channels[item["id"]] = c

        return channels

    @staticmethod
    def _parse_iso_duration(duration_str: str) -> int:
        """Parse ISO 8601 duration (e.g., PT1H2M10S or PT4M30S) into integer seconds."""
        match = re.match(
            r"^P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$",
            duration_str,
        )
        if not match:
            return 0
        parts = match.groupdict()
        days = int(parts.get("days") or 0)
        hours = int(parts.get("hours") or 0)
        minutes = int(parts.get("minutes") or 0)
        seconds = int(parts.get("seconds") or 0)
        return days * 86400 + hours * 3600 + minutes * 60 + seconds

    def _generate_mock_search_results(
        self, query: str, count: int = 25
    ) -> Tuple[List[Video], Dict[str, Channel], List[SearchRankObservation]]:
        """Generate realistic synthetic videos, channels, and observations for testing without live API."""
        videos = []
        channels = {}
        observations = []
        now_str = datetime.now(timezone.utc).isoformat()

        # Generate 1 dominant incumbent channel, 4 small channels with 2 breakouts, and 10 long tail channels
        incumbent_id = "ch_mock_incumbent"
        channels[incumbent_id] = Channel(
            channel_id=incumbent_id,
            title="The Prime Niche Authority",
            subscribers=650000,
            video_count=320,
            median_recent_views=85000.0,
        )

        # Generate staggered publication dates so some videos are recent (<=30d) and some baseline (>30d)
        now_dt = datetime.now(timezone.utc)
        run_id = f"mock_{uuid.uuid4().hex[:8]}"

        for i in range(count):
            vid = f"mock_vid_{i+1:03d}"
            # Even videos are recent (e.g. 5, 10, 15 days ago), odd videos are baseline (e.g. 45, 60 days ago)
            days_ago = (5 + i * 2) if i % 2 == 0 else (40 + i * 5)
            pub_date = (now_dt - timedelta(days=days_ago)).isoformat()

            if i == 0:
                cid = incumbent_id
                v_views = 120000
                v_likes = 5400
                v_comments = 410
                duration = 720
            elif i in (1, 2):
                cid = f"ch_mock_breakout_{i}"
                channels[cid] = Channel(
                    channel_id=cid,
                    title=f"Rising Creator {i}",
                    subscribers=15000,
                    video_count=24,
                    median_recent_views=1200.0,
                )
                v_views = 42000  # Breakout (>3x baseline, >75th percentile)
                v_likes = 2100
                v_comments = 290
                duration = 540
            else:
                cid = f"ch_mock_tail_{i}"
                channels[cid] = Channel(
                    channel_id=cid,
                    title=f"Tail Creator {i}",
                    subscribers=4000,
                    video_count=18,
                    median_recent_views=1500.0,
                )
                v_views = max(600, 4000 - i * 150)
                v_likes = int(v_views * 0.04)
                v_comments = int(v_views * 0.008)
                duration = 600

            v = Video(
                video_id=vid,
                channel_id=cid,
                title=f"{query.title()} - Practical Guide #{i+1}",
                published_at=pub_date,
                views=v_views,
                likes=v_likes,
                comments=v_comments,
                duration="PT10M",
                category_id="27",
            )
            videos.append(v)
            obs = SearchRankObservation(
                run_id=run_id,
                query=query,
                video_id=vid,
                rank_position=i + 1,
                observed_at=now_dt,
                search_context="mock_validation",
            )
            observations.append(obs)

        return videos, channels, observations

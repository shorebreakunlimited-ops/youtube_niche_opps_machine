"""YouTube verification helpers using the repo YouTube Data API client."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Sequence

from src.collectors.youtube_client import YouTubeClient

DEFAULT_MAJOR_CREATORS = (
    "explore with us",
    "ewu",
    "jcs",
    "red tree",
    "code blue cam",
    "midwest safety",
    "audit the audit",
    "law&crime",
    "law and crime",
)


@dataclass(frozen=True)
class YouTubeAuditResult:
    verified_at: str
    search_queries: str
    videos_reviewed: int
    videos_over_500k: int
    top_video_views: Optional[int]
    top_video_url: Optional[str]
    major_creator_matches: str
    data_source: str


def _relevant(text: str, needles: Sequence[str]) -> bool:
    blob = text.lower()
    return any(n.lower() in blob for n in needles)


def audit_case_on_youtube(
    queries: Sequence[str],
    relevance_needles: Sequence[str],
    *,
    client: Optional[YouTubeClient] = None,
    major_creators: Sequence[str] = DEFAULT_MAJOR_CREATORS,
    max_results_per_query: int = 15,
) -> YouTubeAuditResult:
    """Search YouTube, filter to case-relevant hits, return verified metrics.

    Never invents estimates. Empty audits return zeros/None with a real data_source.
    """
    yt = client or YouTubeClient()
    by_id = {}
    for query in queries:
        videos, channels, _ = yt.search_videos(query, max_results=max_results_per_query)
        channel_names = {cid: ch.title for cid, ch in channels.items()} if channels else {}
        for video in videos:
            channel_title = channel_names.get(video.channel_id, "")
            blob = f"{video.title} {channel_title}"
            if relevance_needles and not _relevant(blob, relevance_needles):
                continue
            by_id[video.video_id] = (video, channel_title)

    rows = sorted(by_id.values(), key=lambda item: item[0].views, reverse=True)
    over_500k = [item for item in rows if item[0].views >= 500_000]
    major: List[str] = []
    for _video, channel_title in rows:
        ch_l = channel_title.lower()
        if any(m in ch_l for m in major_creators):
            major.append(channel_title)

    top_video = rows[0][0] if rows else None
    top_url = f"https://www.youtube.com/watch?v={top_video.video_id}" if top_video else None

    return YouTubeAuditResult(
        verified_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        search_queries=" | ".join(queries),
        videos_reviewed=len(rows),
        videos_over_500k=len(over_500k),
        top_video_views=(top_video.views if top_video else None),
        top_video_url=top_url,
        major_creator_matches="; ".join(sorted(set(major))),
        data_source="youtube_data_api_v3",
    )

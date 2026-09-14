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

LIVE_DATA_SOURCE = "youtube_data_api_v3"
MOCK_DATA_SOURCE = "mock"


class YouTubeAuditError(RuntimeError):
    """Raised when a live YouTube audit cannot be completed."""


@dataclass(frozen=True)
class YouTubeAuditResult:
    verified_at: Optional[str]
    search_queries: str
    videos_reviewed: int
    videos_over_500k: int
    top_video_views: Optional[int]
    top_video_url: Optional[str]
    major_creator_matches: str
    data_source: str
    youtube_verified: bool


def _relevant(text: str, needles: Sequence[str]) -> bool:
    blob = text.lower()
    return any(n.lower() in blob for n in needles)


def mock_youtube_audit_result(
    queries: Sequence[str],
    *,
    videos_reviewed: int = 0,
    videos_over_500k: int = 0,
    top_video_views: Optional[int] = None,
    top_video_url: Optional[str] = None,
    major_creator_matches: str = "",
) -> YouTubeAuditResult:
    """Explicit mock/test audit result. Never marks youtube_verified."""
    return YouTubeAuditResult(
        verified_at=None,
        search_queries=" | ".join(queries),
        videos_reviewed=videos_reviewed,
        videos_over_500k=videos_over_500k,
        top_video_views=top_video_views,
        top_video_url=top_video_url,
        major_creator_matches=major_creator_matches,
        data_source=MOCK_DATA_SOURCE,
        youtube_verified=False,
    )


def audit_case_on_youtube(
    queries: Sequence[str],
    relevance_needles: Sequence[str],
    *,
    client: Optional[YouTubeClient] = None,
    major_creators: Sequence[str] = DEFAULT_MAJOR_CREATORS,
    max_results_per_query: int = 15,
) -> YouTubeAuditResult:
    """Search YouTube live and return verified metrics.

    Rejects mock clients. API failures raise YouTubeAuditError — never falls
    back to mock data for verification. Only a successful live API path may
    set data_source=youtube_data_api_v3 and youtube_verified=True.
    """
    yt = client or YouTubeClient()
    if getattr(yt, "use_mock", False):
        raise YouTubeAuditError(
            "audit_case_on_youtube rejects clients with use_mock=True; "
            "live API verification only"
        )
    if not getattr(yt, "api_key", None):
        raise YouTubeAuditError(
            "audit_case_on_youtube requires a live YouTube API key; missing key"
        )

    by_id = {}
    try:
        for query in queries:
            videos, channels, _ = yt.search_videos(
                query,
                max_results=max_results_per_query,
                fallback_to_mock=False,
            )
            channel_names = {cid: ch.title for cid, ch in channels.items()} if channels else {}
            for video in videos:
                channel_title = channel_names.get(video.channel_id, "")
                blob = f"{video.title} {channel_title}"
                if relevance_needles and not _relevant(blob, relevance_needles):
                    continue
                by_id[video.video_id] = (video, channel_title)
    except YouTubeAuditError:
        raise
    except Exception as exc:  # noqa: BLE001 - surface any live API failure explicitly
        raise YouTubeAuditError(f"YouTube audit failed: {exc}") from exc

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
        data_source=LIVE_DATA_SOURCE,
        youtube_verified=True,
    )

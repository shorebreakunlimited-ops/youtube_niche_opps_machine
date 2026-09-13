"""yt-dlp metadata extraction with hard index caps and oEmbed fallback."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Sequence
from urllib.parse import quote, urlparse

from ingest.fts_index import VideoDoc

try:
    import yt_dlp
except ImportError:  # pragma: no cover
    yt_dlp = None  # type: ignore


_WATCH_ID_RE = re.compile(r"(?:v=|/shorts/|/live/|youtu\.be/)([A-Za-z0-9_-]{6,})")


def load_url_list(path: Path | str) -> list[str]:
    path = Path(path)
    urls: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        item = line.strip()
        if not item or item.startswith("#"):
            continue
        urls.append(item)
    return urls


def video_id_from_url(url: str) -> str | None:
    match = _WATCH_ID_RE.search(url)
    if match:
        return match.group(1)
    # Bare 11-char ids sometimes appear in lists.
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url.strip()):
        return url.strip()
    return None


def _normalize_url(url_or_id: str) -> str:
    value = url_or_id.strip()
    if value.startswith("http://") or value.startswith("https://"):
        return value
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", value):
        return f"https://www.youtube.com/watch?v={value}"
    return value


def _entry_to_doc(entry: dict, source_name: str) -> VideoDoc | None:
    if not entry:
        return None
    if entry.get("_type") == "playlist":
        return None
    video_id = entry.get("id") or video_id_from_url(
        entry.get("webpage_url") or entry.get("url") or ""
    )
    if not video_id:
        return None
    url = (
        entry.get("webpage_url")
        or entry.get("url")
        or f"https://www.youtube.com/watch?v={video_id}"
    )
    # Flat playlist entries may only have url as id.
    if url and not url.startswith("http"):
        url = f"https://www.youtube.com/watch?v={video_id}"
    return VideoDoc(
        video_id=str(video_id),
        url=url,
        title=str(entry.get("title") or ""),
        description=str(entry.get("description") or ""),
        channel=str(entry.get("channel") or entry.get("uploader") or ""),
        source_name=source_name,
        upload_date=str(entry.get("upload_date") or ""),
        duration=int(entry["duration"]) if entry.get("duration") is not None else None,
    )


def fetch_oembed_doc(url: str, *, source_name: str) -> VideoDoc | None:
    """
    Lightweight metadata fallback when yt-dlp player extraction is bot-blocked.
    Uses YouTube oEmbed (title + author). Good enough for triage FTS.
    """
    url = _normalize_url(url)
    video_id = video_id_from_url(url)
    if not video_id:
        return None
    oembed = (
        "https://www.youtube.com/oembed?format=json&url="
        + quote(f"https://www.youtube.com/watch?v={video_id}", safe="")
    )
    try:
        with urllib.request.urlopen(oembed, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None
    title = str(payload.get("title") or "")
    channel = str(payload.get("author_name") or "")
    if not title:
        return None
    return VideoDoc(
        video_id=video_id,
        url=f"https://www.youtube.com/watch?v={video_id}",
        title=title,
        description=title,  # oEmbed has no description; title still yields FTS tokens
        channel=channel,
        source_name=source_name,
    )


def extract_docs_from_url(
    url: str,
    *,
    source_name: str,
    max_index_videos: int | None = None,
    flat_playlist: bool = True,
) -> list[VideoDoc]:
    """
    Extract video metadata via yt-dlp.
    For channels/playlists, max_index_videos hard-caps catalog size.
    Falls back to oEmbed for single-video URLs when yt-dlp is blocked.
    """
    if yt_dlp is None:
        raise RuntimeError("yt-dlp is required. Install with: pip install yt-dlp")

    url = _normalize_url(url)
    opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "ignoreerrors": True,
        "extract_flat": "in_playlist" if flat_playlist else False,
    }
    if max_index_videos is not None:
        opts["playlistend"] = max(0, int(max_index_videos))

    docs: list[VideoDoc] = []
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if info is None:
            fallback = fetch_oembed_doc(url, source_name=source_name)
            return [fallback] if fallback else []
        entries = info.get("entries")
        if entries is None:
            doc = _entry_to_doc(info, source_name)
            if doc and (doc.title or doc.description):
                return [doc]
            fallback = fetch_oembed_doc(url, source_name=source_name)
            return [fallback] if fallback else ([doc] if doc else [])

        for entry in entries:
            if entry is None:
                continue
            doc = _entry_to_doc(entry, source_name)
            if not doc:
                continue
            docs.append(doc)
            if max_index_videos is not None and len(docs) >= max_index_videos:
                break

    if not docs:
        fallback = fetch_oembed_doc(url, source_name=source_name)
        if fallback:
            return [fallback]
    return docs


def enrich_docs(
    docs: Sequence[VideoDoc],
    *,
    source_name: str | None = None,
    progress: Callable[[str], None] | None = None,
) -> list[VideoDoc]:
    """Fetch full metadata for flat playlist stubs (title/description)."""
    if yt_dlp is None:
        raise RuntimeError("yt-dlp is required. Install with: pip install yt-dlp")

    enriched: list[VideoDoc] = []
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "ignoreerrors": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        for doc in docs:
            if progress:
                progress(doc.video_id)
            src = source_name or doc.source_name
            info = ydl.extract_info(doc.url, download=False)
            full = _entry_to_doc(info, src) if info else None
            if full and (full.title or full.description):
                # Prefer richer description when present; otherwise keep prior text.
                if not full.description and doc.description:
                    full = VideoDoc(
                        video_id=full.video_id,
                        url=full.url,
                        title=full.title or doc.title,
                        description=doc.description,
                        channel=full.channel or doc.channel,
                        source_name=full.source_name,
                        upload_date=full.upload_date or doc.upload_date,
                        duration=full.duration if full.duration is not None else doc.duration,
                    )
                enriched.append(full)
                continue

            oembed = fetch_oembed_doc(doc.url, source_name=src)
            if oembed:
                # Preserve any existing description from flat extract.
                if doc.description and not oembed.description:
                    oembed = VideoDoc(
                        video_id=oembed.video_id,
                        url=oembed.url,
                        title=oembed.title or doc.title,
                        description=doc.description,
                        channel=oembed.channel or doc.channel,
                        source_name=oembed.source_name,
                        upload_date=doc.upload_date,
                        duration=doc.duration,
                    )
                elif doc.description and oembed.description == oembed.title:
                    oembed = VideoDoc(
                        video_id=oembed.video_id,
                        url=oembed.url,
                        title=oembed.title or doc.title,
                        description=doc.description,
                        channel=oembed.channel or doc.channel,
                        source_name=oembed.source_name,
                        upload_date=doc.upload_date,
                        duration=doc.duration,
                    )
                enriched.append(oembed)
            else:
                enriched.append(doc)
    return enriched


def resolve_source_urls(
    source_url: str,
    *,
    repo_root: Path,
) -> list[str]:
    """
    Resolve a source_url that may be a channel URL or a local video_list file.
    """
    raw = source_url.strip()
    parsed = urlparse(raw)
    if parsed.scheme in {"http", "https"}:
        return [raw]

    path = Path(raw)
    if not path.is_absolute():
        path = repo_root / path
    if not path.exists():
        raise FileNotFoundError(f"video_list path not found: {path}")
    return load_url_list(path)

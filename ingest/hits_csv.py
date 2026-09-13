"""Keyword hit CSV I/O with human review_status gating."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Sequence

from ingest import DOWNLOADABLE_STATUSES, REVIEW_STATUSES
from ingest.fts_index import KeywordHit

KEYWORD_HIT_FIELDS = [
    "video_id",
    "url",
    "title",
    "channel",
    "source_name",
    "upload_date",
    "matched_keyword",
    "snippet",
    "review_status",
    "review_notes",
]


def write_keyword_hits(
    path: Path | str,
    hits: Sequence[KeywordHit],
    *,
    default_status: str = "new",
    preserve_existing: bool = True,
) -> list[dict]:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    prior: dict[tuple[str, str], dict] = {}
    if preserve_existing and path.exists():
        for row in read_keyword_hit_rows(path):
            prior[(row.get("video_id", ""), row.get("matched_keyword", ""))] = row

    if default_status not in REVIEW_STATUSES:
        raise ValueError(f"invalid default review_status: {default_status}")

    rows: list[dict] = []
    for hit in hits:
        key = (hit.video_id, hit.matched_keyword)
        old = prior.get(key, {})
        status = (old.get("review_status") or default_status).strip() or default_status
        if status not in REVIEW_STATUSES:
            status = default_status
        rows.append(
            {
                "video_id": hit.video_id,
                "url": hit.url,
                "title": hit.title,
                "channel": hit.channel,
                "source_name": hit.source_name,
                "upload_date": hit.upload_date,
                "matched_keyword": hit.matched_keyword,
                "snippet": hit.snippet,
                "review_status": status,
                "review_notes": old.get("review_notes", ""),
            }
        )

    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=KEYWORD_HIT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return rows


def append_keyword_hit_row(path: Path | str, row: dict) -> None:
    """Incrementally append one hit row (creates header if needed)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=KEYWORD_HIT_FIELDS)
        if new_file:
            writer.writeheader()
        out = {k: row.get(k, "") for k in KEYWORD_HIT_FIELDS}
        writer.writerow(out)


def read_keyword_hit_rows(path: Path | str) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def filter_downloadable_rows(rows: Iterable[dict]) -> list[dict]:
    out: list[dict] = []
    seen_urls: set[str] = set()
    for row in rows:
        status = (row.get("review_status") or "").strip().lower()
        if status not in DOWNLOADABLE_STATUSES:
            continue
        url = (row.get("url") or "").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        out.append(row)
    return out


def write_target_urls(
    path: Path | str,
    rows: Sequence[dict],
    *,
    max_target_urls: int | None = None,
) -> list[str]:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    urls: list[str] = []
    for row in rows:
        url = (row.get("url") or "").strip()
        if not url:
            continue
        urls.append(url)
        if max_target_urls is not None and len(urls) >= max_target_urls:
            break
    with path.open("w", encoding="utf-8") as fh:
        fh.write(
            "# Auto-exported from keyword_hits with review_status in "
            "{download, episode_candidate}\n"
        )
        for url in urls:
            fh.write(url + "\n")
    return urls


def status_distribution(rows: Sequence[dict]) -> dict[str, int]:
    dist: dict[str, int] = {}
    for row in rows:
        status = (row.get("review_status") or "").strip() or "(empty)"
        dist[status] = dist.get(status, 0) + 1
    return dist

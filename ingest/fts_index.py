"""SQLite FTS5 index for video metadata keyword discovery."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
    video_id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    channel TEXT NOT NULL DEFAULT '',
    source_name TEXT NOT NULL DEFAULT '',
    upload_date TEXT NOT NULL DEFAULT '',
    duration INTEGER
);

CREATE VIRTUAL TABLE IF NOT EXISTS videos_fts USING fts5(
    video_id UNINDEXED,
    title,
    description,
    channel,
    content='videos',
    content_rowid='rowid'
);

CREATE TRIGGER IF NOT EXISTS videos_ai AFTER INSERT ON videos BEGIN
  INSERT INTO videos_fts(rowid, video_id, title, description, channel)
  VALUES (new.rowid, new.video_id, new.title, new.description, new.channel);
END;

CREATE TRIGGER IF NOT EXISTS videos_ad AFTER DELETE ON videos BEGIN
  INSERT INTO videos_fts(videos_fts, rowid, video_id, title, description, channel)
  VALUES ('delete', old.rowid, old.video_id, old.title, old.description, old.channel);
END;

CREATE TRIGGER IF NOT EXISTS videos_au AFTER UPDATE ON videos BEGIN
  INSERT INTO videos_fts(videos_fts, rowid, video_id, title, description, channel)
  VALUES ('delete', old.rowid, old.video_id, old.title, old.description, old.channel);
  INSERT INTO videos_fts(rowid, video_id, title, description, channel)
  VALUES (new.rowid, new.video_id, new.title, new.description, new.channel);
END;
"""


@dataclass(frozen=True)
class VideoDoc:
    video_id: str
    url: str
    title: str = ""
    description: str = ""
    channel: str = ""
    source_name: str = ""
    upload_date: str = ""
    duration: int | None = None


@dataclass(frozen=True)
class KeywordHit:
    video_id: str
    url: str
    title: str
    description: str
    channel: str
    source_name: str
    upload_date: str
    matched_keyword: str
    snippet: str


_TOKEN_RE = re.compile(r"[A-Za-z0-9_*]+")


def load_keywords(path: Path | str) -> list[str]:
    path = Path(path)
    keywords: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        term = line.strip()
        if not term or term.startswith("#"):
            continue
        keywords.append(term)
    return keywords


def _fts_query_for_term(term: str) -> str:
    raw = term.strip()
    if not raw:
        raise ValueError("empty keyword")
    parts = _TOKEN_RE.findall(raw)
    if not parts:
        raise ValueError(f"unsupported keyword: {term!r}")
    escaped: list[str] = []
    for part in parts:
        if part.endswith("*") and len(part) > 1:
            body = part[:-1].replace('"', "")
            escaped.append(f'"{body}"*')
        else:
            escaped.append(f'"{part.replace(chr(34), "")}"')
    return " AND ".join(escaped)


class VideoFTSIndex:
    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "VideoFTSIndex":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def upsert_many(self, docs: Iterable[VideoDoc]) -> int:
        count = 0
        for doc in docs:
            existing = self.conn.execute(
                "SELECT rowid FROM videos WHERE video_id = ?", (doc.video_id,)
            ).fetchone()
            if existing:
                self.conn.execute(
                    """
                    UPDATE videos
                    SET url=?, title=?, description=?, channel=?, source_name=?,
                        upload_date=?, duration=?
                    WHERE video_id=?
                    """,
                    (
                        doc.url,
                        doc.title or "",
                        doc.description or "",
                        doc.channel or "",
                        doc.source_name or "",
                        doc.upload_date or "",
                        doc.duration,
                        doc.video_id,
                    ),
                )
            else:
                self.conn.execute(
                    """
                    INSERT INTO videos (
                        video_id, url, title, description, channel,
                        source_name, upload_date, duration
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        doc.video_id,
                        doc.url,
                        doc.title or "",
                        doc.description or "",
                        doc.channel or "",
                        doc.source_name or "",
                        doc.upload_date or "",
                        doc.duration,
                    ),
                )
            count += 1
        self.conn.commit()
        return count

    def count_videos(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) AS n FROM videos").fetchone()
        return int(row["n"] if row else 0)

    def search_keywords(
        self,
        keywords: Sequence[str],
        *,
        max_search_hits: int = 100,
    ) -> list[KeywordHit]:
        hits: list[KeywordHit] = []
        seen: set[tuple[str, str]] = set()

        for keyword in keywords:
            if len(hits) >= max_search_hits:
                break
            try:
                query = _fts_query_for_term(keyword)
            except ValueError:
                continue
            remaining = max_search_hits - len(hits)
            rows = self.conn.execute(
                """
                SELECT
                    v.video_id, v.url, v.title, v.description, v.channel,
                    v.source_name, v.upload_date,
                    snippet(videos_fts, 1, '[', ']', ' … ', 12) AS snip
                FROM videos_fts
                JOIN videos v ON v.rowid = videos_fts.rowid
                WHERE videos_fts MATCH ?
                LIMIT ?
                """,
                (query, remaining),
            ).fetchall()
            for row in rows:
                key = (row["video_id"], keyword)
                if key in seen:
                    continue
                seen.add(key)
                hits.append(
                    KeywordHit(
                        video_id=row["video_id"],
                        url=row["url"],
                        title=row["title"],
                        description=row["description"] or "",
                        channel=row["channel"] or "",
                        source_name=row["source_name"] or "",
                        upload_date=row["upload_date"] or "",
                        matched_keyword=keyword,
                        snippet=row["snip"] or "",
                    )
                )
                if len(hits) >= max_search_hits:
                    break
        return hits

"""Relational SQLite storage layer with normalized snapshots and split provenance."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.models import (
    Channel,
    ChannelMetricSnapshot,
    Niche,
    NicheVideoDiscovery,
    NicheVideoMembership,
    SearchRankObservation,
    ValidationResult,
    Video,
    VideoMetricSnapshot,
)


class Database:
    def __init__(self, db_path: str = "data/niche_engine.db"):
        self.db_path = db_path
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self.conn:
            self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS niches (
                niche_id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                market TEXT,
                subniche TEXT,
                format TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS channels (
                channel_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                custom_url TEXT,
                created_at TEXT,
                first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS videos (
                video_id TEXT PRIMARY KEY,
                channel_id TEXT NOT NULL,
                title TEXT NOT NULL,
                published_at TEXT NOT NULL,
                duration TEXT,
                category_id TEXT,
                first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(channel_id) REFERENCES channels(channel_id)
            );

            CREATE TABLE IF NOT EXISTS niche_video_memberships (
                niche_id TEXT NOT NULL,
                video_id TEXT NOT NULL,
                relevance_score REAL NOT NULL,
                primary_cluster_id TEXT,
                first_seen_in_niche TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen_in_niche TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (niche_id, video_id),
                FOREIGN KEY(niche_id) REFERENCES niches(niche_id),
                FOREIGN KEY(video_id) REFERENCES videos(video_id)
            );

            CREATE TABLE IF NOT EXISTS niche_video_discoveries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                niche_id TEXT NOT NULL,
                video_id TEXT NOT NULL,
                discovery_method TEXT NOT NULL,
                originating_query TEXT NOT NULL,
                rank_position INTEGER,
                observed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(niche_id) REFERENCES niches(niche_id),
                FOREIGN KEY(video_id) REFERENCES videos(video_id)
            );

            CREATE TABLE IF NOT EXISTS video_metric_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT NOT NULL,
                observed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                views INTEGER NOT NULL,
                likes INTEGER,
                comments INTEGER,
                FOREIGN KEY(video_id) REFERENCES videos(video_id)
            );

            CREATE TABLE IF NOT EXISTS channel_metric_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL,
                observed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                subscribers INTEGER,
                total_views INTEGER,
                video_count INTEGER,
                FOREIGN KEY(channel_id) REFERENCES channels(channel_id)
            );

            CREATE TABLE IF NOT EXISTS search_rank_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                query TEXT NOT NULL,
                video_id TEXT NOT NULL,
                rank_position INTEGER NOT NULL,
                observed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                region TEXT DEFAULT 'US',
                language TEXT DEFAULT 'en',
                order_param TEXT DEFAULT 'relevance',
                device_context TEXT DEFAULT 'desktop',
                search_context TEXT DEFAULT 'api',
                FOREIGN KEY(video_id) REFERENCES videos(video_id)
            );

            CREATE TABLE IF NOT EXISTS validation_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                niche_id TEXT NOT NULL,
                validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                content_opportunity_score REAL NOT NULL,
                creator_adjusted_opportunity REAL NOT NULL,
                commercial_attractiveness_score REAL NOT NULL,
                production_feasibility REAL NOT NULL,
                rights_safety REAL NOT NULL,
                confidence_score REAL NOT NULL,
                demand_score REAL NOT NULL,
                supply_scarcity REAL NOT NULL,
                acceleration_score REAL NOT NULL,
                breakout_score REAL NOT NULL,
                repeatability_score REAL NOT NULL,
                recommendation TEXT NOT NULL,
                raw_payload_json TEXT NOT NULL,
                FOREIGN KEY(niche_id) REFERENCES niches(niche_id)
            );

            CREATE TABLE IF NOT EXISTS watchlist (
                niche_id TEXT PRIMARY KEY,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                target_score_threshold REAL DEFAULT 75.0,
                active INTEGER DEFAULT 1,
                FOREIGN KEY(niche_id) REFERENCES niches(niche_id)
            );

            CREATE TABLE IF NOT EXISTS quota_usage (
                usage_date TEXT PRIMARY KEY,
                search_calls_used INTEGER DEFAULT 0,
                video_batch_units_used INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_video_snapshots ON video_metric_snapshots(video_id, observed_at);
            CREATE INDEX IF NOT EXISTS idx_channel_snapshots ON channel_metric_snapshots(channel_id, observed_at);
            CREATE INDEX IF NOT EXISTS idx_search_ranks ON search_rank_observations(query, observed_at);
            CREATE INDEX IF NOT EXISTS idx_discoveries ON niche_video_discoveries(niche_id, video_id);
            CREATE INDEX IF NOT EXISTS idx_memberships ON niche_video_memberships(niche_id, relevance_score);
            CREATE INDEX IF NOT EXISTS idx_val_snaps ON validation_snapshots(niche_id, validated_at);
            """)

    def save_niche(self, niche: Niche) -> None:
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO niches (niche_id, name, market, subniche, format)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(niche_id) DO UPDATE SET
                    name=excluded.name,
                    market=excluded.market,
                    subniche=excluded.subniche,
                    format=excluded.format
                """,
                (niche.niche_id, niche.name, niche.market, niche.subniche, niche.format),
            )

    def get_niche(self, niche_id: str) -> Optional[Niche]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM niches WHERE niche_id = ?", (niche_id,))
        row = cur.fetchone()
        if not row:
            return None
        return Niche(
            niche_id=row["niche_id"],
            name=row["name"],
            market=row["market"],
            subniche=row["subniche"],
            format=row["format"],
        )

    def save_channel(self, channel: Channel) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO channels (channel_id, title, custom_url, created_at, first_seen_at, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(channel_id) DO UPDATE SET
                    title=excluded.title,
                    custom_url=excluded.custom_url,
                    last_updated=?
                """,
                (
                    channel.channel_id,
                    channel.title,
                    channel.custom_url,
                    channel.created_at,
                    now,
                    now,
                    now,
                ),
            )

    def save_channel_snapshot(self, snapshot: ChannelMetricSnapshot) -> int:
        obs_at = (
            snapshot.observed_at.isoformat()
            if isinstance(snapshot.observed_at, datetime)
            else snapshot.observed_at
        )
        with self.conn:
            cur = self.conn.execute(
                """
                INSERT INTO channel_metric_snapshots (channel_id, observed_at, subscribers, total_views, video_count)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    snapshot.channel_id,
                    obs_at,
                    snapshot.subscribers,
                    snapshot.total_views,
                    snapshot.video_count,
                ),
            )
            return cur.lastrowid

    def save_video(self, video: Video) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO videos (video_id, channel_id, title, published_at, duration, category_id, first_seen_at, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(video_id) DO UPDATE SET
                    title=excluded.title,
                    duration=excluded.duration,
                    category_id=excluded.category_id,
                    last_updated=?
                """,
                (
                    video.video_id,
                    video.channel_id,
                    video.title,
                    video.published_at,
                    video.duration,
                    video.category_id,
                    now,
                    now,
                    now,
                ),
            )

    def get_videos_by_channel(self, channel_id: str) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT * FROM videos WHERE channel_id = ?
            ORDER BY published_at DESC
            """,
            (channel_id,),
        )
        return [dict(row) for row in cur.fetchall()]

    def save_video_snapshot(self, snapshot: VideoMetricSnapshot) -> int:
        obs_at = (
            snapshot.observed_at.isoformat()
            if isinstance(snapshot.observed_at, datetime)
            else snapshot.observed_at
        )
        with self.conn:
            cur = self.conn.execute(
                """
                INSERT INTO video_metric_snapshots (video_id, observed_at, views, likes, comments)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    snapshot.video_id,
                    obs_at,
                    snapshot.views,
                    snapshot.likes,
                    snapshot.comments,
                ),
            )
            return cur.lastrowid

    def record_membership(self, membership: NicheVideoMembership) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO niche_video_memberships (
                    niche_id, video_id, relevance_score, primary_cluster_id, first_seen_in_niche, last_seen_in_niche
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(niche_id, video_id) DO UPDATE SET
                    relevance_score=excluded.relevance_score,
                    primary_cluster_id=coalesce(excluded.primary_cluster_id, primary_cluster_id),
                    last_seen_in_niche=?
                """,
                (
                    membership.niche_id,
                    membership.video_id,
                    membership.relevance_score,
                    membership.primary_cluster_id,
                    now,
                    now,
                    now,
                ),
            )

    def record_discovery(self, discovery: NicheVideoDiscovery) -> int:
        obs_at = (
            discovery.observed_at.isoformat()
            if isinstance(discovery.observed_at, datetime)
            else datetime.now(timezone.utc).isoformat()
        )
        with self.conn:
            cur = self.conn.execute(
                """
                INSERT INTO niche_video_discoveries (
                    run_id, niche_id, video_id, discovery_method, originating_query, rank_position, observed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    discovery.run_id,
                    discovery.niche_id,
                    discovery.video_id,
                    discovery.discovery_method,
                    discovery.originating_query,
                    discovery.rank_position,
                    obs_at,
                ),
            )
            return cur.lastrowid

    def record_search_rank(self, obs: SearchRankObservation) -> int:
        obs_at = (
            obs.observed_at.isoformat()
            if isinstance(obs.observed_at, datetime)
            else datetime.now(timezone.utc).isoformat()
        )
        with self.conn:
            cur = self.conn.execute(
                """
                INSERT INTO search_rank_observations (
                    run_id, query, video_id, rank_position, observed_at, region, language, order_param, device_context, search_context
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    obs.run_id,
                    obs.query,
                    obs.video_id,
                    obs.rank_position,
                    obs_at,
                    obs.region,
                    obs.language,
                    obs.order_param,
                    obs.device_context,
                    obs.search_context,
                ),
            )
            return cur.lastrowid

    def save_validation_snapshot(self, result: ValidationResult) -> int:
        val_at = (
            result.validated_at.isoformat()
            if isinstance(result.validated_at, datetime)
            else datetime.now(timezone.utc).isoformat()
        )
        with self.conn:
            cur = self.conn.execute(
                """
                INSERT INTO validation_snapshots (
                    niche_id, validated_at, content_opportunity_score, creator_adjusted_opportunity,
                    commercial_attractiveness_score, production_feasibility, rights_safety,
                    confidence_score, demand_score, supply_scarcity, acceleration_score,
                    breakout_score, repeatability_score, recommendation, raw_payload_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.niche_id,
                    val_at,
                    result.content_opportunity_score,
                    result.creator_adjusted_opportunity,
                    result.commercial_attractiveness_score,
                    result.production_feasibility,
                    result.rights_safety,
                    result.confidence_score,
                    result.demand_score,
                    result.supply_scarcity,
                    result.acceleration_score,
                    result.breakout_score,
                    result.repeatability_score,
                    result.recommendation,
                    result.raw_payload_json,
                ),
            )
            return cur.lastrowid

    def compute_snapshot_delta_velocity(self, video_id: str) -> Optional[float]:
        """Compute real snapshot delta velocity from the two most recent observations."""
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT views, observed_at
            FROM video_metric_snapshots
            WHERE video_id = ?
            ORDER BY observed_at DESC
            LIMIT 2
            """,
            (video_id,),
        )
        rows = cur.fetchall()
        if len(rows) < 2:
            return None
        
        v2, t2_str = rows[0]["views"], rows[0]["observed_at"]
        v1, t1_str = rows[1]["views"], rows[1]["observed_at"]
        
        t2 = datetime.fromisoformat(t2_str.replace("Z", "+00:00"))
        t1 = datetime.fromisoformat(t1_str.replace("Z", "+00:00"))
        
        elapsed_days = max(0.0417, (t2 - t1).total_seconds() / 86400.0)
        return max(0.0, float(v2 - v1) / elapsed_days)

    def get_validation_history(self, niche_id: str) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT * FROM validation_snapshots
            WHERE niche_id = ?
            ORDER BY validated_at DESC
            """,
            (niche_id,),
        )
        return [dict(row) for row in cur.fetchall()]

    def add_to_watchlist(self, niche_id: str, threshold: float = 75.0) -> None:
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO watchlist (niche_id, target_score_threshold, active)
                VALUES (?, ?, 1)
                ON CONFLICT(niche_id) DO UPDATE SET
                    target_score_threshold=excluded.target_score_threshold,
                    active=1
                """,
                (niche_id, threshold),
            )

    def get_watchlist(self) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT w.*, n.name as niche_name
            FROM watchlist w
            JOIN niches n ON w.niche_id = n.niche_id
            WHERE w.active = 1
            ORDER BY w.added_at DESC
            """
        )
        return [dict(row) for row in cur.fetchall()]

    def get_quota_usage(self, usage_date: str) -> Dict[str, int]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT search_calls_used, video_batch_units_used FROM quota_usage WHERE usage_date = ?",
            (usage_date,),
        )
        row = cur.fetchone()
        if not row:
            return {"search_calls_used": 0, "video_batch_units_used": 0}
        return {"search_calls_used": int(row[0]), "video_batch_units_used": int(row[1])}

    def record_quota_consumption(
        self, usage_date: str, search_calls: int = 0, video_batch_units: int = 0
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO quota_usage (usage_date, search_calls_used, video_batch_units_used, last_updated)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(usage_date) DO UPDATE SET
                    search_calls_used = search_calls_used + excluded.search_calls_used,
                    video_batch_units_used = video_batch_units_used + excluded.video_batch_units_used,
                    last_updated = excluded.last_updated
                """,
                (usage_date, search_calls, video_batch_units, now),
            )

    # Convenient method aliases
    upsert_channel = save_channel
    upsert_video = save_video
    record_search_rank_observation = record_search_rank

    def close(self) -> None:
        self.conn.close()


# Alias for backward/forward naming compatibility
NicheDatabase = Database

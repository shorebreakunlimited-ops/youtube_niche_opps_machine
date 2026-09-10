"""CSV tabular exports for discovery leaderboards and breakout evidence."""

import csv
import io
from typing import Any, Dict, List
from src.models import BreakoutEvidence


def export_discovery_to_csv(leaderboard: List[Dict[str, Any]]) -> str:
    """Format a discovery leaderboard as CSV text."""
    output = io.StringIO()
    writer = csv.writer(output)

    headers = [
        "rank",
        "niche_name",
        "content_opportunity_score",
        "confidence_score",
        "recommendation",
        "demand_score",
        "supply_scarcity",
        "breakout_score",
        "acceleration_score",
        "repeatability_score",
        "creator_adjusted_opportunity",
        "production_feasibility",
        "rights_safety",
    ]
    writer.writerow(headers)

    for entry in leaderboard:
        writer.writerow(
            [
                entry.get("rank"),
                entry.get("niche_name"),
                entry.get("content_opportunity_score"),
                entry.get("confidence_score"),
                entry.get("recommendation"),
                entry.get("demand_score"),
                entry.get("supply_scarcity"),
                entry.get("breakout_score"),
                entry.get("acceleration_score"),
                entry.get("repeatability_score"),
                entry.get("creator_adjusted_opportunity"),
                entry.get("production_feasibility"),
                entry.get("rights_safety"),
            ]
        )

    return output.getvalue()


def export_breakout_evidence_to_csv(evidence_list: List[BreakoutEvidence]) -> str:
    """Format breakout evidence list as CSV text."""
    output = io.StringIO()
    writer = csv.writer(output)

    headers = [
        "channel_id",
        "channel_title",
        "subscribers",
        "video_id",
        "video_title",
        "views",
        "baseline_views",
        "breakout_ratio",
        "baseline_tier",
    ]
    writer.writerow(headers)

    for ev in evidence_list:
        writer.writerow(
            [
                ev.channel_id,
                ev.channel_title,
                ev.subscribers,
                ev.video_id,
                ev.video_title,
                ev.views,
                ev.baseline_views,
                ev.breakout_ratio,
                ev.baseline_tier,
            ]
        )

    return output.getvalue()

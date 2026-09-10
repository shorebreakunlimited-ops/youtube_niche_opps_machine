"""Command line interface for the YouTube Niche Opportunity Search Engine."""

import argparse
import json
import os
import sys
from typing import Optional

from src.collectors.browseract_adapter import BrowserActAdapter
from src.collectors.youtube_client import YouTubeClient
from src.discovery.niche_extractor import NicheExtractor
from src.reports.console import (
    print_discovery_leaderboard,
    print_sensitivity_report,
    print_validation_scorecard,
)
from src.reports.csv_export import export_discovery_to_csv
from src.reports.json_export import export_discovery_to_json, export_validation_to_json
from src.simulation.sensitivity import simulate_monte_carlo_sensitivity
from src.storage.cache import SQLiteCache
from src.storage.database import NicheDatabase
from src.validation.niche_validator import NicheValidator


def build_engine(use_mock: bool = False, db_path: str = "data/niche_engine.db", cache_path: str = "data/cache.db"):
    """Instantiate the engine components with SQLite database and request cache."""
    cache = SQLiteCache(cache_db=cache_path)
    db = NicheDatabase(db_path=db_path)
    api_key = os.environ.get("YOUTUBE_API_KEY")
    client = YouTubeClient(api_key=api_key, cache=cache, db=db, use_mock=use_mock or (not api_key))
    browser = BrowserActAdapter(cache=cache)
    validator = NicheValidator(youtube_client=client, browser_adapter=browser, db=db, cache=cache)
    extractor = NicheExtractor(validator=validator, browser_adapter=browser)
    return validator, extractor, db, client


def cmd_validate(args):
    validator, _, db, client = build_engine(use_mock=args.mock)
    print(f"Validating niche '{args.query}' (max_videos={args.max_videos}, mock={client.use_mock})...")
    result = validator.validate_niche(niche_query=args.query, max_videos=args.max_videos)

    if args.add_to_watchlist:
        db.add_to_watchlist(result.niche_id, threshold=75.0)
        print(f"Added {result.niche_name} to watchlist.")

    if args.json:
        print(export_validation_to_json(result))
    else:
        print_validation_scorecard(result)


def cmd_discover(args):
    _, extractor, _, client = build_engine(use_mock=args.mock)
    print(f"Running automated discovery on seed '{args.seed}' (max_candidates={args.candidates}, mock={client.use_mock})...")
    leaderboard = extractor.discover_subniches(
        seed_topic=args.seed,
        max_candidates=args.candidates,
        min_confidence_gate=args.min_confidence,
    )

    if args.json:
        print(export_discovery_to_json(leaderboard))
    elif args.csv:
        print(export_discovery_to_csv(leaderboard))
    else:
        print_discovery_leaderboard(leaderboard, seed_topic=args.seed)


def cmd_simulate(args):
    # Simulated realistic candidates or user-specified seeds
    cohort = [
        {
            "name": "Cursor AI Rules & Workflows",
            "demand": 82.0,
            "supply": 74.0,
            "acceleration": 78.0,
            "breakout": 88.0,
            "repeatability": 85.0,
            "durability": 65.0,
            "outlier_penalty": 2.0,
        },
        {
            "name": "LangGraph Multi-Agent RAG",
            "demand": 85.0,
            "supply": 62.0,
            "acceleration": 80.0,
            "breakout": 70.0,
            "repeatability": 80.0,
            "durability": 60.0,
            "outlier_penalty": 5.0,
        },
        {
            "name": "Solopreneur Notion ERP Systems",
            "demand": 68.0,
            "supply": 58.0,
            "acceleration": 60.0,
            "breakout": 62.0,
            "repeatability": 70.0,
            "durability": 75.0,
            "outlier_penalty": 0.0,
        },
        {
            "name": "Local LLM Fine-Tuning on Mac",
            "demand": 74.0,
            "supply": 68.0,
            "acceleration": 72.0,
            "breakout": 65.0,
            "repeatability": 68.0,
            "durability": 60.0,
            "outlier_penalty": 0.0,
        },
        {
            "name": "3D Blender Game Assets",
            "demand": 55.0,
            "supply": 35.0,
            "acceleration": 48.0,
            "breakout": 40.0,
            "repeatability": 90.0,
            "durability": 80.0,
            "outlier_penalty": 12.0,
        },
    ]

    report = simulate_monte_carlo_sensitivity(
        cohort_scores=cohort,
        iterations=args.iterations,
        perturbation_pct=args.perturbation / 100.0,
    )

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print_sensitivity_report(report)


def cmd_quota(args):
    _, _, _, client = build_engine(use_mock=args.mock)
    status = client.get_quota_status()
    print("\nYouTube Data API v3 Quota Utilization:")
    print(f"  Date (UTC): {status['date']}")
    print(f"  Mock Mode:  {status['mock_mode']}")
    print("  search.list calls:")
    print(f"    Used:      {status['search_list']['used']}")
    print(f"    Limit:     {status['search_list']['limit']} calls/day")
    print(f"    Remaining: {status['search_list']['remaining']}")
    print("  videos.batchGetStats units:")
    print(f"    Used:      {status['videos_batch']['used']}")
    print(f"    Limit:     {status['videos_batch']['limit']} units/day")
    print(f"    Remaining: {status['videos_batch']['remaining']}\n")


def cmd_watchlist(args):
    _, _, db, _ = build_engine()
    items = db.get_watchlist()
    if not items:
        print("\nWatchlist is currently empty. Add niches using 'validate <query> --add-to-watchlist'.\n")
        return

    print("\nActive Watched Niches:")
    for item in items:
        print(f"  • {item.get('niche_name')} (ID: {item.get('niche_id')}, Threshold: {item.get('target_score_threshold')})")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="YouTube Niche Opportunity Search Engine CLI (v2.2 Architecture)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Validate
    p_val = subparsers.add_parser("validate", help="Run Mode B deep validation on a niche query")
    p_val.add_argument("query", type=str, help="Target niche search query or seed")
    p_val.add_argument("--max-videos", type=int, default=30, help="Number of videos to analyze (default 30)")
    p_val.add_argument("--mock", action="store_true", help="Use synthetic mock data instead of live API")
    p_val.add_argument("--add-to-watchlist", action="store_true", help="Add niche to active SQLite watchlist")
    p_val.add_argument("--json", action="store_true", help="Output raw JSON instead of console scorecard")
    p_val.set_defaults(func=cmd_validate)

    # Discover
    p_disc = subparsers.add_parser("discover", help="Run Mode A automated discovery on a root seed")
    p_disc.add_argument("seed", type=str, help="Root topic seed to expand")
    p_disc.add_argument("--candidates", type=int, default=6, help="Max candidates to evaluate (default 6)")
    p_disc.add_argument("--min-confidence", type=float, default=20.0, help="Minimum confidence gate (default 20.0)")
    p_disc.add_argument("--mock", action="store_true", help="Use synthetic mock data instead of live API")
    p_disc.add_argument("--json", action="store_true", help="Output raw JSON instead of leaderboard")
    p_disc.add_argument("--csv", action="store_true", help="Output CSV leaderboard")
    p_disc.set_defaults(func=cmd_discover)

    # Simulate
    p_sim = subparsers.add_parser("simulate", help="Run Monte Carlo sensitivity analysis on scoring weights")
    p_sim.add_argument("--iterations", type=int, default=500, help="Number of simulation draws (default 500)")
    p_sim.add_argument("--perturbation", type=float, default=20.0, help="Weight perturbation percentage +/- (default 20.0)")
    p_sim.add_argument("--json", action="store_true", help="Output raw JSON")
    p_sim.set_defaults(func=cmd_simulate)

    # Quota
    p_quota = subparsers.add_parser("quota", help="Display YouTube API quota utilization")
    p_quota.add_argument("--mock", action="store_true", help="Show mock quota")
    p_quota.set_defaults(func=cmd_quota)

    # Watchlist
    p_watch = subparsers.add_parser("watchlist", help="List active tracked niches in SQLite")
    p_watch.set_defaults(func=cmd_watchlist)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

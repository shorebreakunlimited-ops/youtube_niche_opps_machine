"""CLI for inspecting case ledgers."""

from __future__ import annotations

import argparse
import json

from .loader import launch_shortlist, load_ledger, provisional_candidates, rank_candidates


def _print_table(rows) -> None:
    if not rows:
        print("(no rows)")
        return
    print(f"{'SCORE':>5}  {'VERDICT':<7}  {'YT':<8}  {'POISON':>6}  CASE")
    print("-" * 96)
    for r in rows:
        yt = "verified" if r.youtube_verified else "unknown"
        score = r.candidate_score if r.candidate_score is not None else "-"
        print(
            f"{score:>5}  {r.verdict:<7}  {yt:<8}  {r.poison_signal_count:>6}  {r.case_name}"
        )
        print(f"       title: {r.working_title}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bodycam case ledger tools")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_cand = sub.add_parser("list-candidates", help="List scored candidate cases")
    p_cand.add_argument("--min-score", type=int, default=0)
    p_cand.add_argument("--strong-only", action="store_true")
    p_cand.add_argument("--include-children", action="store_true")

    sub.add_parser("list-poisoned", help="List poisoned cases")
    sub.add_parser("rank", help="Show provisional research candidates (not a final launch shortlist)")
    sub.add_parser("launch-shortlist", help="Final launch shortlist (independent gate; may be empty)")
    sub.add_parser("json-shortlist", help="Emit provisional research candidates as JSON")

    args = parser.parse_args(argv)

    if args.cmd == "list-candidates":
        verdicts = ["strong"] if args.strong_only else None
        _print_table(
            rank_candidates(
                min_score=args.min_score,
                verdicts=verdicts,
                include_children=args.include_children,
            )
        )
        return 0
    if args.cmd == "list-poisoned":
        rows = load_ledger("poisoned_cases")
        _print_table(sorted(rows, key=lambda r: r.case_name.lower()))
        return 0
    if args.cmd == "rank":
        _print_table(provisional_candidates())
        return 0
    if args.cmd == "launch-shortlist":
        _print_table(launch_shortlist())
        return 0
    if args.cmd == "json-shortlist":
        payload = [
            {
                "case_id": r.case_id,
                "case_name": r.case_name,
                "working_title": r.working_title,
                "candidate_score": r.candidate_score,
                "verdict": r.verdict,
                "videos_reviewed": r.videos_reviewed,
                "videos_over_500k": r.videos_over_500k,
                "top_video_views": r.top_video_views,
                "top_video_url": r.top_video_url,
                "major_creator_matches": r.major_creator_matches,
                "data_source": r.data_source,
                "verified_at": r.verified_at,
                "search_queries": r.search_queries,
                "poison_signal_count": r.poison_signal_count,
            }
            for r in provisional_candidates()
        ]
        print(json.dumps(payload, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

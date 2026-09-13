"""CLI for inspecting case ledgers."""

from __future__ import annotations

import argparse
import json

from src.case_ledgers.loader import launch_shortlist, load_ledger, rank_candidates


def _print_table(rows) -> None:
    if not rows:
        print("(no rows)")
        return
    print(f"{'SCORE':>5}  {'VERDICT':<7}  {'BURDEN':<7}  {'RISK':<8}  CASE")
    print("-" * 88)
    for r in rows:
        print(
            f"{r.candidate_score:>5}  {r.verdict:<7}  {r.production_burden:<7}  {r.risk_level:<8}  {r.case_name}"
        )
        print(f"       title: {r.working_title}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bodycam case ledger tools")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_cand = sub.add_parser("list-candidates", help="List scored candidate cases")
    p_cand.add_argument("--min-score", type=int, default=0)
    p_cand.add_argument("--strong-only", action="store_true")

    sub.add_parser("list-poisoned", help="List poisoned cases")
    sub.add_parser("rank", help="Rank launch shortlist (strong, score>=75)")
    sub.add_parser("json-shortlist", help="Emit launch shortlist as JSON")

    args = parser.parse_args(argv)

    if args.cmd == "list-candidates":
        verdicts = ["strong"] if args.strong_only else None
        _print_table(rank_candidates(min_score=args.min_score, verdicts=verdicts))
        return 0
    if args.cmd == "list-poisoned":
        rows = load_ledger("poisoned_cases")
        _print_table(sorted(rows, key=lambda r: r.case_name.lower()))
        return 0
    if args.cmd == "rank":
        _print_table(launch_shortlist())
        return 0
    if args.cmd == "json-shortlist":
        payload = [
            {
                "case_name": r.case_name,
                "working_title": r.working_title,
                "source_url": r.source_url,
                "jurisdiction": r.jurisdiction,
                "candidate_score": r.candidate_score,
                "verdict": r.verdict,
                "fresh_angle": r.fresh_angle,
                "notes": r.notes,
            }
            for r in launch_shortlist()
        ]
        print(json.dumps(payload, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

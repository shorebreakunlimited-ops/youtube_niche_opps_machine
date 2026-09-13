#!/usr/bin/env python3
"""
Gated downloader for body-cam triage pipeline.

Only downloads rows whose review_status is:
  - download
  - episode_candidate

This prevents every keyword match from becoming storage bloat.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ingest import DOWNLOADABLE_STATUSES
from ingest.hits_csv import (
    filter_downloadable_rows,
    read_keyword_hit_rows,
    write_target_urls,
)

try:
    import yt_dlp
except ImportError:  # pragma: no cover
    yt_dlp = None  # type: ignore


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Review-gated body-cam downloader.")
    p.add_argument(
        "--hits-csv",
        type=Path,
        default=ROOT / "ingest" / "keyword_hits.csv",
        help="Keyword hits CSV with review_status column",
    )
    p.add_argument(
        "--target-urls",
        type=Path,
        default=ROOT / "ingest" / "target_urls.txt",
        help="Where to write the approved URL list before download",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "ingest" / "downloads",
        help="Download directory",
    )
    p.add_argument(
        "--max-target-urls",
        type=int,
        default=25,
        help="Hard cap on approved URLs to download",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Export approved URLs only; do not download",
    )
    return p


def download_urls(urls: list[str], output_dir: Path) -> int:
    if yt_dlp is None:
        raise RuntimeError("yt-dlp is required. Install with: pip install yt-dlp")
    output_dir.mkdir(parents=True, exist_ok=True)
    opts = {
        "outtmpl": str(output_dir / "%(upload_date)s_%(id)s_%(title).80B.%(ext)s"),
        "ignoreerrors": True,
        "noplaylist": True,
        "restrictfilenames": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download(urls)
    return 0


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    rows = read_keyword_hit_rows(args.hits_csv)
    if not rows:
        raise SystemExit(f"No rows in {args.hits_csv}. Run channel_ingest.py first.")

    approved = filter_downloadable_rows(rows)
    if not approved:
        statuses = sorted({(r.get("review_status") or "").strip() for r in rows})
        raise SystemExit(
            "No downloadable rows. Mark review_status as "
            f"{sorted(DOWNLOADABLE_STATUSES)} in {args.hits_csv}. "
            f"Current statuses present: {statuses}"
        )

    urls = write_target_urls(
        args.target_urls,
        approved,
        max_target_urls=args.max_target_urls,
    )
    print(
        f"[gate] {len(urls)} approved URL(s) "
        f"(from {len(approved)} downloadable rows, "
        f"max-target-urls={args.max_target_urls})"
    )
    print(f"[gate] wrote {args.target_urls}")

    if args.dry_run:
        print("[dry-run] skipping download")
        for url in urls:
            print(f"  would download: {url}")
        return 0

    print(f"[download] starting {len(urls)} file(s) → {args.output_dir}")
    return download_urls(urls, args.output_dir)


if __name__ == "__main__":
    raise SystemExit(run())

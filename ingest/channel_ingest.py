#!/usr/bin/env python3
"""
Source-triage channel ingest for body-cam discovery.

Pipeline:
  source candidate → small index test → keyword yield → human review → target_urls.txt

Safe default:
  python ingest/channel_ingest.py
    → only enabled sources from config/sources.csv (smoke list)

Intentional full channel:
  python ingest/channel_ingest.py --include-disabled --source "KHON News" --jobs 2

Limit flags are separate on purpose (do not overload --limit):
  --max-index-videos
  --max-search-hits
  --max-target-urls
"""

from __future__ import annotations

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ingest.extract import enrich_docs, extract_docs_from_url, resolve_source_urls
from ingest.fts_index import VideoFTSIndex, load_keywords
from ingest.hits_csv import (
    filter_downloadable_rows,
    write_keyword_hits,
    write_target_urls,
)
from ingest.sources import load_sources, select_sources


def _repo_root() -> Path:
    return ROOT


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Body-cam source triage ingest (safe-by-default)."
    )
    p.add_argument(
        "--sources-file",
        type=Path,
        default=_repo_root() / "config" / "sources.csv",
        help="Source triage registry (default: config/sources.csv)",
    )
    p.add_argument(
        "--channels-file",
        type=Path,
        default=None,
        help="Optional explicit URL/video list (bypasses sources.csv selection).",
    )
    p.add_argument(
        "--keywords-file",
        type=Path,
        default=_repo_root() / "config" / "keywords.smoke.txt",
        help="FTS stem/token keyword file",
    )
    p.add_argument(
        "--source",
        action="append",
        default=[],
        dest="source_names",
        help="Select source_name from sources.csv (repeatable).",
    )
    p.add_argument(
        "--include-disabled",
        action="store_true",
        help="Allow disabled sources; requires explicit --source NAME.",
    )
    p.add_argument(
        "--max-index-videos",
        type=int,
        default=None,
        help="Hard cap on videos indexed per source/URL (playlistend).",
    )
    p.add_argument(
        "--max-search-hits",
        type=int,
        default=100,
        help="Hard cap on keyword FTS hits exported to keyword_hits.csv",
    )
    p.add_argument(
        "--max-target-urls",
        type=int,
        default=25,
        help="Hard cap when exporting approved URLs to target_urls.txt",
    )
    p.add_argument(
        "--jobs",
        type=int,
        default=1,
        help="Parallel metadata enrich workers (default 1).",
    )
    p.add_argument(
        "--db-path",
        type=Path,
        default=_repo_root() / "ingest" / "data" / "videos_fts.sqlite3",
        help="SQLite FTS database path",
    )
    p.add_argument(
        "--hits-csv",
        type=Path,
        default=_repo_root() / "ingest" / "keyword_hits.csv",
        help="Keyword yield CSV for human review",
    )
    p.add_argument(
        "--target-urls",
        type=Path,
        default=_repo_root() / "ingest" / "target_urls.txt",
        help="Approved download URL list (review_status gated)",
    )
    p.add_argument(
        "--enrich",
        action="store_true",
        default=True,
        help="Enrich flat playlist stubs with full metadata (default on).",
    )
    p.add_argument(
        "--no-enrich",
        action="store_false",
        dest="enrich",
        help="Skip metadata enrichment (faster, weaker FTS).",
    )
    p.add_argument(
        "--export-approved-targets",
        action="store_true",
        help="Also write target_urls.txt from download/episode_candidate rows.",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        help=argparse.SUPPRESS,  # deprecated trap
    )
    return p


def _reject_deprecated_limit(args: argparse.Namespace) -> None:
    if args.limit is not None:
        raise SystemExit(
            "ERROR: --limit is deprecated and dangerous (ambiguous catalog vs search cap).\n"
            "Use separate flags instead:\n"
            "  --max-index-videos N\n"
            "  --max-search-hits N\n"
            "  --max-target-urls N"
        )


def _index_source_urls(
    urls: list[str],
    *,
    source_name: str,
    max_index_videos: int | None,
    enrich: bool,
    jobs: int,
) -> list:
    docs = []
    remaining = max_index_videos
    for url in urls:
        per_url_cap = remaining
        batch = extract_docs_from_url(
            url,
            source_name=source_name,
            max_index_videos=per_url_cap,
            flat_playlist=True,
        )
        docs.extend(batch)
        if max_index_videos is not None:
            remaining = max_index_videos - len(docs)
            if remaining <= 0:
                docs = docs[:max_index_videos]
                break

    if not enrich or not docs:
        return docs

    # Enrich in parallel but keep order stable.
    if jobs <= 1 or len(docs) == 1:
        return enrich_docs(docs, source_name=source_name)

    enriched = [None] * len(docs)

    def _one(idx_doc):
        idx, doc = idx_doc
        return idx, enrich_docs([doc], source_name=source_name)[0]

    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        futures = [pool.submit(_one, (i, d)) for i, d in enumerate(docs)]
        for fut in as_completed(futures):
            idx, doc = fut.result()
            enriched[idx] = doc
    return [d for d in enriched if d is not None]


def run(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _reject_deprecated_limit(args)

    root = _repo_root()
    keywords = load_keywords(args.keywords_file)
    if not keywords:
        raise SystemExit(f"No keywords loaded from {args.keywords_file}")

    work_items: list[tuple[str, list[str]]] = []

    if args.channels_file:
        from ingest.extract import load_url_list

        urls = load_url_list(args.channels_file)
        if not urls:
            raise SystemExit(f"No URLs in {args.channels_file}")
        # Explicit channels-file is always treated as a controlled list.
        if args.max_index_videos is None:
            args.max_index_videos = len(urls)
        work_items.append((f"channels-file:{args.channels_file.name}", urls))
        print(
            f"[triage] explicit --channels-file ({len(urls)} urls); "
            f"max-index-videos={args.max_index_videos}"
        )
    else:
        sources = load_sources(args.sources_file)
        selected = select_sources(
            sources,
            include_disabled=args.include_disabled,
            source_names=args.source_names or None,
        )
        print("[triage] selected sources:")
        needs_index_cap = False
        for src in selected:
            print(
                f"  - {src.source_name} type={src.source_type} "
                f"enabled={src.enabled} priority={src.priority}"
            )
            urls = resolve_source_urls(src.source_url, repo_root=root)
            work_items.append((src.source_name, urls))
            if src.is_channel:
                needs_index_cap = True
            elif any(
                u.startswith("http") and ("@" in u or "/channel/" in u or "/c/" in u)
                for u in urls
            ):
                needs_index_cap = True

        # For channel sources without an explicit cap, require one.
        if needs_index_cap and args.max_index_videos is None:
            raise SystemExit(
                "Refusing unbounded channel index. Pass --max-index-videos N "
                "for a small index test before full ingest."
            )

        # video_list sources: default cap to total resolved URLs when unset
        if args.max_index_videos is None:
            total_urls = sum(len(urls) for _, urls in work_items)
            args.max_index_videos = total_urls

    all_docs = []
    for source_name, urls in work_items:
        print(f"[index] {source_name}: fetching metadata for {len(urls)} url(s)...")
        docs = _index_source_urls(
            urls,
            source_name=source_name,
            max_index_videos=args.max_index_videos,
            enrich=args.enrich,
            jobs=args.jobs,
        )
        print(f"[index] {source_name}: indexed {len(docs)} video(s)")
        all_docs.extend(docs)

    if not all_docs:
        raise SystemExit("No videos indexed; aborting keyword search.")

    args.db_path.parent.mkdir(parents=True, exist_ok=True)
    with VideoFTSIndex(args.db_path) as index:
        index.upsert_many(all_docs)
        print(f"[fts] database videos={index.count_videos()} path={args.db_path}")
        hits = index.search_keywords(keywords, max_search_hits=args.max_search_hits)
        print(f"[fts] keyword hits={len(hits)} (max-search-hits={args.max_search_hits})")

    rows = write_keyword_hits(args.hits_csv, hits, default_status="new")
    print(f"[review] wrote {len(rows)} rows → {args.hits_csv}")
    print("         review_status values: new | watch | download | reject | episode_candidate")
    print("         Downloader only pulls: download, episode_candidate")

    downloadable = filter_downloadable_rows(rows)
    if args.export_approved_targets:
        urls = write_target_urls(
            args.target_urls,
            downloadable,
            max_target_urls=args.max_target_urls,
        )
        print(
            f"[targets] exported {len(urls)} approved URL(s) → {args.target_urls} "
            f"(max-target-urls={args.max_target_urls})"
        )
    else:
        print(
            f"[targets] skipped export ({len(downloadable)} approved so far). "
            "Re-run with --export-approved-targets after human review."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(run())

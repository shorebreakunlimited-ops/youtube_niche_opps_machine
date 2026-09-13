#!/usr/bin/env python3
"""
Source-triage channel ingest for body-cam discovery.

Safe default:
  python3 ingest/channel_ingest.py

Controlled KHON test (does NOT enable KHON globally):
  python3 ingest/channel_ingest.py \
    --include-disabled \
    --source "KHON News" \
    --max-index-videos 100 \
    --max-search-hits 100 \
    --max-target-urls 10
"""

from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ingest.extract import (
    ExtractStats,
    enrich_docs,
    extract_docs_from_url,
    load_url_list,
    resolve_source_urls,
)
from ingest.fts_index import VideoDoc, VideoFTSIndex, load_keywords
from ingest.hits_csv import (
    filter_downloadable_rows,
    status_distribution,
    write_keyword_hits,
    write_target_urls,
)
from ingest.sources import load_sources, select_sources


@dataclass
class SourceRunStats:
    source_name: str
    requested: int = 0
    indexed: int = 0
    failed: int = 0
    skipped: int = 0
    runtime_sec: float = 0.0
    unique_video_ids: set[str] = field(default_factory=set)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Body-cam source triage ingest (safe-by-default)."
    )
    p.add_argument("--sources-file", type=Path, default=ROOT / "config" / "sources.csv")
    p.add_argument("--channels-file", type=Path, default=None)
    p.add_argument(
        "--keywords-file",
        type=Path,
        default=ROOT / "config" / "keywords.smoke.txt",
    )
    p.add_argument("--source", action="append", default=[], dest="source_names")
    p.add_argument("--include-disabled", action="store_true")
    p.add_argument("--max-index-videos", type=int, default=None)
    p.add_argument("--max-search-hits", type=int, default=100)
    p.add_argument("--max-target-urls", type=int, default=25)
    p.add_argument("--jobs", type=int, default=1)
    p.add_argument("--db-path", type=Path, default=ROOT / "ingest" / "data" / "videos_fts.sqlite3")
    p.add_argument("--hits-csv", type=Path, default=ROOT / "ingest" / "keyword_hits.csv")
    p.add_argument("--target-urls", type=Path, default=ROOT / "ingest" / "target_urls.txt")
    p.add_argument("--enrich", action="store_true", default=True)
    p.add_argument("--no-enrich", action="store_false", dest="enrich")
    p.add_argument("--export-approved-targets", action="store_true")
    p.add_argument("--progress-every", type=int, default=10)
    p.add_argument("--limit", type=int, default=None, help=argparse.SUPPRESS)
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
    progress_every: int,
    stats: SourceRunStats,
) -> list[VideoDoc]:
    docs: list[VideoDoc] = []
    remaining = max_index_videos
    extract_stats = ExtractStats()

    def _on_doc(doc: VideoDoc, n: int) -> None:
        stats.unique_video_ids.add(doc.video_id)
        if progress_every > 0 and n % progress_every == 0:
            cap = f"/{max_index_videos}" if max_index_videos else ""
            print(f"[index] {source_name}: incremental {n}{cap} … latest={doc.video_id}")

    for url in urls:
        batch = extract_docs_from_url(
            url,
            source_name=source_name,
            max_index_videos=remaining,
            flat_playlist=True,
            on_doc=_on_doc,
            stats=extract_stats,
        )
        docs.extend(batch)
        if max_index_videos is not None:
            remaining = max_index_videos - len(docs)
            if remaining <= 0:
                docs = docs[:max_index_videos]
                break

    if max_index_videos is not None and len(docs) > max_index_videos:
        raise SystemExit(
            f"STOP: catalog extraction ignored --max-index-videos={max_index_videos} "
            f"(indexed={len(docs)}). Refusing to continue."
        )

    if enrich and docs:
        if jobs <= 1 or len(docs) == 1:
            docs = enrich_docs(docs, source_name=source_name, on_doc=_on_doc)
        else:
            enriched: list[VideoDoc | None] = [None] * len(docs)

            def _one(idx_doc: tuple[int, VideoDoc]) -> tuple[int, VideoDoc]:
                idx, doc = idx_doc
                return idx, enrich_docs([doc], source_name=source_name)[0]

            with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
                futs = [pool.submit(_one, (i, d)) for i, d in enumerate(docs)]
                for fut in as_completed(futs):
                    idx, doc = fut.result()
                    enriched[idx] = doc
                    n = sum(1 for x in enriched if x is not None)
                    if progress_every > 0 and n % progress_every == 0:
                        print(f"[enrich] {source_name}: incremental {n}/{len(docs)}")
            docs = [d for d in enriched if d is not None]

    stats.requested += extract_stats.requested
    stats.indexed = len(docs)
    stats.failed += extract_stats.failed
    stats.skipped += extract_stats.skipped
    for d in docs:
        stats.unique_video_ids.add(d.video_id)
    return docs


def _print_smoke_report(
    *,
    source_stats: list[SourceRunStats],
    fts_hit_count: int,
    unique_videos: int,
    status_dist: dict[str, int],
    exported_targets: int,
    hits_csv: Path,
) -> None:
    print("\n======== SMOKE RESULT ========")
    for s in source_stats:
        print(
            f"[source] {s.source_name}: requested={s.requested} indexed={s.indexed} "
            f"failed={s.failed} skipped={s.skipped} unique={len(s.unique_video_ids)} "
            f"runtime_sec={s.runtime_sec:.2f}"
        )
    print(f"[fts] hit_count={fts_hit_count}")
    print(f"[dedupe] unique_videos={unique_videos}")
    print(f"[review] status_distribution={dict(sorted(status_dist.items()))}")
    print(f"[targets] exported_target_count={exported_targets}")
    print(f"[artifacts] hits_csv={hits_csv}")
    print("======== END SMOKE RESULT ========\n")


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _reject_deprecated_limit(args)

    keywords = load_keywords(args.keywords_file)
    if not keywords:
        raise SystemExit(f"No keywords loaded from {args.keywords_file}")

    work_items: list[tuple[str, list[str]]] = []

    if args.channels_file:
        urls = load_url_list(args.channels_file)
        if not urls:
            raise SystemExit(f"No URLs in {args.channels_file}")
        if args.max_index_videos is None:
            args.max_index_videos = len(urls)
        work_items.append((f"channels-file:{args.channels_file.name}", urls))
        print(
            f"[triage] explicit --channels-file ({len(urls)} urls); "
            f"max-index-videos={args.max_index_videos}"
        )
    else:
        sources = load_sources(args.sources_file)
        # Hard safety: never globally enable major channels.
        for name in ("KHON News", "KITV", "Hawaii News Now"):
            for src in sources:
                if src.source_name == name and src.enabled:
                    raise SystemExit(
                        f"Safety stop: {name} is enabled globally in sources.csv. "
                        "Keep enabled=false; use --include-disabled --source for tests."
                    )

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
            urls = resolve_source_urls(src.source_url, repo_root=ROOT)
            work_items.append((src.source_name, urls))
            if src.is_channel or any(
                u.startswith("http") and ("@" in u or "/channel/" in u or "/c/" in u)
                for u in urls
            ):
                needs_index_cap = True

        if needs_index_cap and args.max_index_videos is None:
            raise SystemExit(
                "Refusing unbounded channel index. Pass --max-index-videos N "
                "for a small index test before full ingest."
            )
        if args.max_index_videos is None:
            args.max_index_videos = sum(len(u) for _, u in work_items)

    all_docs: list[VideoDoc] = []
    source_stats: list[SourceRunStats] = []
    for source_name, urls in work_items:
        print(f"[index] {source_name}: fetching metadata for {len(urls)} url(s)...")
        stats = SourceRunStats(source_name=source_name)
        t0 = time.perf_counter()
        docs = _index_source_urls(
            urls,
            source_name=source_name,
            max_index_videos=args.max_index_videos,
            enrich=args.enrich,
            jobs=args.jobs,
            progress_every=args.progress_every,
            stats=stats,
        )
        stats.runtime_sec = time.perf_counter() - t0
        if args.max_index_videos is not None and len(docs) > args.max_index_videos:
            raise SystemExit(
                f"STOP: --max-index-videos={args.max_index_videos} ignored (got {len(docs)})."
            )
        print(
            f"[index] {source_name}: indexed={len(docs)} requested={stats.requested} "
            f"failed={stats.failed} skipped={stats.skipped} "
            f"runtime_sec={stats.runtime_sec:.2f}"
        )
        source_stats.append(stats)
        all_docs.extend(docs)

    if not all_docs:
        raise SystemExit("No videos indexed; aborting keyword search.")

    deduped: list[VideoDoc] = []
    seen: set[str] = set()
    for doc in all_docs:
        if doc.video_id in seen:
            continue
        seen.add(doc.video_id)
        deduped.append(doc)

    args.db_path.parent.mkdir(parents=True, exist_ok=True)
    with VideoFTSIndex(args.db_path) as index:
        batch_size = max(1, args.progress_every)
        for i in range(0, len(deduped), batch_size):
            chunk = deduped[i : i + batch_size]
            index.upsert_many(chunk)
            print(
                f"[fts] upserted {min(i + batch_size, len(deduped))}/{len(deduped)} unique video(s)"
            )
        print(f"[fts] database videos={index.count_videos()} path={args.db_path}")
        hits = index.search_keywords(keywords, max_search_hits=args.max_search_hits)
        print(f"[fts] keyword hits={len(hits)} (max-search-hits={args.max_search_hits})")

    rows = write_keyword_hits(args.hits_csv, hits, default_status="new")
    print(f"[review] wrote {len(rows)} rows → {args.hits_csv}")
    print("         review_status values: new | watch | download | reject | episode_candidate")
    print("         Downloader only pulls: download, episode_candidate")

    downloadable = filter_downloadable_rows(rows)
    exported = 0
    if args.export_approved_targets:
        urls = write_target_urls(
            args.target_urls,
            downloadable,
            max_target_urls=args.max_target_urls,
        )
        exported = len(urls)
        print(
            f"[targets] exported {exported} approved URL(s) → {args.target_urls} "
            f"(max-target-urls={args.max_target_urls})"
        )
    else:
        print(
            f"[targets] skipped export ({len(downloadable)} approved so far). "
            "Re-run with --export-approved-targets after human review."
        )

    _print_smoke_report(
        source_stats=source_stats,
        fts_hit_count=len(hits),
        unique_videos=len(deduped),
        status_dist=status_distribution(rows),
        exported_targets=exported,
        hits_csv=args.hits_csv,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

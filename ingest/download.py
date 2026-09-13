#!/usr/bin/env python3
"""
Review-gated downloader with failure reporting and storage limits.

Only downloads rows whose review_status is:
  - download
  - episode_candidate

Never run without --dry-run until full ingest is approved.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from dataclasses import dataclass, field
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


@dataclass
class DownloadReport:
    planned: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    bytes_before: int = 0
    bytes_after: int = 0
    failures: list[dict] = field(default_factory=list)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Review-gated body-cam downloader.")
    p.add_argument("--hits-csv", type=Path, default=ROOT / "ingest" / "keyword_hits.csv")
    p.add_argument("--target-urls", type=Path, default=ROOT / "ingest" / "target_urls.txt")
    p.add_argument("--output-dir", type=Path, default=ROOT / "ingest" / "downloads")
    p.add_argument("--max-target-urls", type=int, default=25)
    p.add_argument(
        "--max-storage-mb",
        type=float,
        default=500.0,
        help="Hard storage budget for output-dir (default 500 MB).",
    )
    p.add_argument(
        "--failure-log",
        type=Path,
        default=ROOT / "ingest" / "download_failures.csv",
        help="CSV log of failed downloads",
    )
    p.add_argument(
        "--report-json",
        type=Path,
        default=ROOT / "ingest" / "download_report.json",
        help="Machine-readable download report",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Export approved URLs only; do not download (required until approved).",
    )
    p.add_argument(
        "--allow-download",
        action="store_true",
        help="Explicitly allow real downloads (still respects storage limit).",
    )
    return p


def _dir_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                continue
    return total


def _write_failure_log(path: Path, failures: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["url", "error", "timestamp"]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(failures)


def download_urls(
    urls: list[str],
    output_dir: Path,
    *,
    max_storage_mb: float,
    failure_log: Path,
) -> DownloadReport:
    if yt_dlp is None:
        raise RuntimeError("yt-dlp is required. Install with: pip install yt-dlp")

    output_dir.mkdir(parents=True, exist_ok=True)
    report = DownloadReport(
        planned=len(urls),
        bytes_before=_dir_size_bytes(output_dir),
    )
    budget = int(max_storage_mb * 1024 * 1024)
    if report.bytes_before >= budget:
        raise SystemExit(
            f"Storage limit already reached: {report.bytes_before} bytes >= "
            f"{budget} bytes (--max-storage-mb={max_storage_mb})."
        )

    def _hook(d: dict) -> None:
        # Abort mid-download if storage budget exceeded.
        used = _dir_size_bytes(output_dir)
        if used >= budget:
            raise RuntimeError(
                f"storage limit exceeded during download ({used} >= {budget} bytes)"
            )

    opts = {
        "outtmpl": str(output_dir / "%(upload_date)s_%(id)s_%(title).80B.%(ext)s"),
        "ignoreerrors": False,
        "noplaylist": True,
        "restrictfilenames": True,
        "progress_hooks": [_hook],
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        for url in urls:
            used = _dir_size_bytes(output_dir)
            if used >= budget:
                report.skipped += 1
                report.failures.append(
                    {
                        "url": url,
                        "error": f"skipped: storage limit {used}>={budget}",
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    }
                )
                continue
            try:
                ydl.download([url])
                report.succeeded += 1
            except Exception as exc:  # noqa: BLE001 - collect all failure modes
                report.failed += 1
                report.failures.append(
                    {
                        "url": url,
                        "error": str(exc),
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    }
                )

    report.bytes_after = _dir_size_bytes(output_dir)
    _write_failure_log(failure_log, report.failures)
    return report


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
    print(f"[storage] max_storage_mb={args.max_storage_mb}")

    before_files = (
        len([p for p in args.output_dir.rglob("*") if p.is_file()])
        if args.output_dir.exists()
        else 0
    )

    if args.dry_run or not args.allow_download:
        if not args.dry_run and not args.allow_download:
            print(
                "[safety] refusing real download without --dry-run or --allow-download"
            )
        print("[dry-run] skipping download")
        for url in urls:
            print(f"  would download: {url}")
        after_files = (
            len([p for p in args.output_dir.rglob("*") if p.is_file()])
            if args.output_dir.exists()
            else 0
        )
        report = {
            "mode": "dry-run",
            "planned": len(urls),
            "downloaded_files": 0,
            "files_before": before_files,
            "files_after": after_files,
            "files_added": after_files - before_files,
            "confirmation": "dry-run downloaded zero files"
            if after_files == before_files
            else "ERROR: files changed during dry-run",
        }
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(
            f"[dry-run] confirmation: downloaded_files=0 "
            f"files_before={before_files} files_after={after_files}"
        )
        if after_files != before_files:
            raise SystemExit("Dry-run safety failure: output directory changed.")
        return 0

    print(f"[download] starting {len(urls)} file(s) → {args.output_dir}")
    report_obj = download_urls(
        urls,
        args.output_dir,
        max_storage_mb=args.max_storage_mb,
        failure_log=args.failure_log,
    )
    payload = {
        "mode": "download",
        "planned": report_obj.planned,
        "succeeded": report_obj.succeeded,
        "failed": report_obj.failed,
        "skipped": report_obj.skipped,
        "bytes_before": report_obj.bytes_before,
        "bytes_after": report_obj.bytes_after,
        "failures": report_obj.failures,
        "failure_log": str(args.failure_log),
    }
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        f"[download] planned={report_obj.planned} succeeded={report_obj.succeeded} "
        f"failed={report_obj.failed} skipped={report_obj.skipped}"
    )
    print(f"[download] failure_log={args.failure_log}")
    print(f"[download] report_json={args.report_json}")
    return 0 if report_obj.failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(run())

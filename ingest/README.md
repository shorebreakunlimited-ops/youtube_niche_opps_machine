# Body-cam source triage ingest

Pipeline:

```
source candidate → small index test → keyword yield → human review → target_urls.txt
```

## Safe default

```bash
python3 ingest/channel_ingest.py
```

Runs **only enabled** sources from `config/sources.csv`.
KHON / KITV / Hawaii News Now ship **disabled**.

## Controlled channel test (does not enable globally)

```bash
python3 ingest/channel_ingest.py \
  --include-disabled \
  --source "KHON News" \
  --max-index-videos 100 \
  --max-search-hits 100 \
  --max-target-urls 10
```

Smoke result prints:
- videos requested / indexed / failed / skipped
- runtime per source
- FTS hit count
- unique videos after dedupe
- review_status distribution
- exported target count

## Limits (do not use `--limit`)

- `--max-index-videos` — hard catalog cap (aborts if exceeded)
- `--max-search-hits` — hard FTS hit cap
- `--max-target-urls` — hard approved URL export/download cap

## Gated download

```bash
python3 ingest/download.py --dry-run --max-target-urls 10 --max-storage-mb 500
```

Downloader only pulls `download` / `episode_candidate`.
Real downloads require `--allow-download` and respect `--max-storage-mb`.
Failures are written to `download_failures.csv` + `download_report.json`.

KITV / Hawaii News Now: run only after KHON controlled test succeeds.

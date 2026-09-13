# Body-cam source triage ingest

Pipeline:

```
source candidate → small index test → keyword yield → human review → target_urls.txt
```

## Safe default

```bash
python ingest/channel_ingest.py
```

Runs **only enabled** sources from `config/sources.csv`. Full local-news channels
(KHON / KITV / HNN) ship **disabled**.

## Controlled smoke test

```bash
python ingest/channel_ingest.py \
  --channels-file config/channels.smoke.txt \
  --keywords-file config/keywords.smoke.txt \
  --max-search-hits 100 \
  --max-target-urls 10
```

Then inspect `ingest/keyword_hits.csv` and set `review_status` to one of:

| status | meaning |
| --- | --- |
| `new` | unscored |
| `watch` | needs human watch |
| `download` | approved for storage |
| `reject` | discard |
| `episode_candidate` | likely episode material |

## Intentional full-channel index test

```bash
python ingest/channel_ingest.py \
  --include-disabled \
  --source "KHON News" \
  --max-index-videos 10 \
  --max-search-hits 100 \
  --jobs 2
```

## Limits (do not use `--limit`)

- `--max-index-videos` — hard catalog cap per source
- `--max-search-hits` — hard FTS hit cap
- `--max-target-urls` — hard approved URL export/download cap

## Gated download

```bash
python ingest/download.py --dry-run
python ingest/download.py --max-target-urls 10
```

Downloader **only** pulls rows marked `download` or `episode_candidate`.

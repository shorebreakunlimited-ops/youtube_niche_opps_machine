# Case Ledgers — Two-Ledger Production System

Operational research system for bodycam / court-record episode selection.

## Ledgers

| Table | Purpose |
|---|---|
| `poisoned_cases.csv` | Avoid / only reopen with genuinely new evidence |
| `candidate_cases.csv` | Score and rank for production |
| `case_sources.csv` | Source matrix keyed by `case_id` |

## Core rule

Do **not** start with famous cases. Start where the footage is clickable and the **unanswered aftermath** is the gap.

A known-enough incident with raw evidence but **no dominant explanatory package** beats an unknown case with thin aftermath.

## Reproducible scoring

Each candidate stores integer 0–10 axes:

`novelty`, `evidence`, `decision_chain`, `aftermath`, `packaging`, `production_fit`, `safety`

`candidate_score` is a weighted 0–100 integer. Loader **rejects** rows where stored `candidate_score` or `verdict` does not match the recalculated result.

Weights: novelty 20, evidence 20, decision_chain 15, aftermath 15, packaging 15, production_fit 10, safety 5.

Verdicts: `strong` (≥75) / `maybe` (≥60) / `avoid` (<60). **2+ poison signals force `avoid`.**

## Poison rule

Poison signals are stored as structured boolean fields. `count_poison_signals()` runs on load. A candidate with **2+** poison signals cannot keep `strong` or `maybe`. `launch_shortlist()` re-checks independently of the CSV verdict.

## YouTube metrics (verified only)

Required fields:

`verified_at`, `search_queries`, `videos_reviewed`, `videos_over_500k`, `top_video_views`, `top_video_url`, `major_creator_matches`, `data_source`

Unknown values are empty / `unknown` / null — never `est.`. Strong / launch-ready status requires verified YouTube metrics from a real pipeline source (YouTube Data API v3 in this repo).

## Source discipline (strong candidates)

Each strong candidate requires all four source types in `case_sources.csv`:

1. `bodycam_raw`
2. `court_police_record`
3. `independent_reporting`
4. `legal_outcome`

Unsupported factual claims are not scored as evidence.

## Parent / child cases

Cpl. Matthew Lau (`C002`) is the parent investigation. Anthony Jameson (`C003`) is a **child/subcase** and is excluded from `launch_shortlist()`.

## Launch profile

10–40 minute bodycam/court-record story, one clean decision chain, documented aftermath, verified YouTube under-packaging, not dominated by a famous creator, titleable without the suspect’s name.

## CLI

```bash
python -m src.case_ledgers list-candidates --min-score 70
python -m src.case_ledgers list-poisoned
python -m src.case_ledgers rank
python -m src.case_ledgers json-shortlist
```

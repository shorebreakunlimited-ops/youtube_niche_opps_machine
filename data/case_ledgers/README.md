# Case Ledgers — Two-Ledger Production System

Operational research system for bodycam / court-record episode selection.

## Ledgers

| Table | Purpose |
|---|---|
| `poisoned_cases.csv` | Avoid / only reopen with genuinely new evidence |
| `candidate_cases.csv` | Score and rank for production research |
| `case_sources.csv` | Source matrix keyed by `case_id` (with provenance) |

## Core rule

Do **not** start with famous cases. Start where the footage is clickable and the **unanswered aftermath** is the gap.

## Reproducible scoring

Integer 0–10 axes: `novelty`, `evidence`, `decision_chain`, `aftermath`, `packaging`, `production_fit`, `safety`

`candidate_score` is a weighted 0–100 integer. Loader rejects score/verdict mismatches.

Weights: novelty 20, evidence 20, decision_chain 15, aftermath 15, packaging 15, production_fit 10, safety 5.

Verdicts: `strong` (≥75) / `maybe` (≥60) / `avoid` (<60). **2+ poison signals force `avoid`.**

## Poison rule

Structured poison booleans. `count_poison_signals()` runs on load. `launch_shortlist()` re-checks independently.

## YouTube provenance (live only)

`audit_case_on_youtube()`:

- Rejects clients with `use_mock=True`
- Raises `YouTubeAuditError` on API failure — never falls back to mock for verification
- Only successful live API responses may set `data_source=youtube_data_api_v3`, `youtube_verified=true`, `verified_at=<timestamp>`
- Mock/test helpers use `data_source=mock` and `youtube_verified=false`

## Source discipline

Strong candidates require four types in `case_sources.csv`:

1. `bodycam_raw` — direct video, agency release, court exhibit, public-record file, or documented acquisition location (**not** a news article)
2. `court_police_record` — official court/police document or docket
3. `independent_reporting` — independent journalism
4. `legal_outcome` — verified legal outcome

One secondary URL may **not** satisfy court record + independent reporting + legal outcome simultaneously.

Each row stores `provenance_class` and optional `acquisition_notes`.

## Parent / child

Cpl. Matthew Lau (`C002`) is parent. Anthony Jameson (`C003`) is a child/subcase.

## Provisional vs final launch

`provisional_candidates()` returns the research slate (currently includes C001 / C002 / C004 among others).

`launch_shortlist()` is the **final** launch gate and is intentionally empty until aftermath and raw-footage acquisition are locked. C001/C002/C004 are **provisional**, not a final launch shortlist.

C004 Robert Scalise is demoted to `maybe` (pending civil litigation; dismissed citation is not material aftermath; raw footage acquisition not established).

## CLI

```bash
python -m src.case_ledgers list-candidates --min-score 70
python -m src.case_ledgers list-poisoned
python -m src.case_ledgers rank              # provisional research slate
python -m src.case_ledgers launch-shortlist  # final launch gate
python -m src.case_ledgers json-shortlist
```

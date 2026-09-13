# Case Ledgers — Two-Ledger Production System

Operational research system for bodycam / court-record episode selection.

## Ledgers

| Table | Purpose |
|---|---|
| `poisoned_cases.csv` | Avoid / only reopen with genuinely new evidence |
| `candidate_cases.csv` | Score and rank for production |

## Core rule

Do **not** start with famous cases. Start where the footage is clickable and the **unanswered aftermath** is the gap.

A known-enough incident with raw evidence but **no dominant explanatory package** beats an unknown case with thin aftermath.

## Poison rule

A case is poisoned if it hits **two or more** poison signals (see `POISON_SIGNALS.md`).

## First-pass scoring (brutal)

| Axis | Question |
|---|---|
| Novelty | Has YouTube already had its definitive version? |
| Evidence | Bodycam, court docs, arrest records, local reporting, sentencing? |
| Decision Chain | Can we identify 3–5 turning points? |
| Aftermath | Can we answer what happened after? |
| Packaging | Can the title sell a reversal/consequence without naming the case? |
| Production Fit | Can we make it in 1–3 days? |
| Risk | Defamatory, politicized, or speculation-dependent? |

`candidate_score` is a 0–100 composite. Verdicts: `strong` / `maybe` / `avoid`.

## Episode format to hunt for

1. Cold open: the irreversible moment  
2. Context: why police were there  
3. Decision chain: 4 turning points  
4. Procedure/legal layer: what mattered  
5. Aftermath: charges, lawsuit, sentence, discipline, dismissal, or policy consequence  
6. Final read: what the footage proves — and what it does not  

## Launch profile

10–40 minute bodycam/court-record story, one clean decision chain, documented aftermath, not dominated by a famous creator, titleable without the suspect’s name.

## CLI

```bash
python -m src.case_ledgers.cli list-candidates --min-score 70
python -m src.case_ledgers.cli list-poisoned
python -m src.case_ledgers.cli rank
```

# YouTube Niche Opportunity Engine

Research tooling for YouTube niche opportunity discovery, plus a **two-ledger bodycam case system** for episode selection.

## Case Ledgers

Operational research for bodycam / court-record episode production lives in `data/case_ledgers/`:

| Ledger | Purpose |
|---|---|
| `poisoned_cases.csv` | Avoid / only reopen with new evidence |
| `candidate_cases.csv` | Score and rank for production |

Core rule: do **not** start with famous cases. Start where footage is clickable and the unanswered aftermath is the gap.

```bash
python3 -m src.case_ledgers rank
python3 -m src.case_ledgers list-candidates --min-score 70
python3 -m src.case_ledgers list-poisoned
```

See [`data/case_ledgers/README.md`](data/case_ledgers/README.md) for scoring rules, poison signals, and episode format.

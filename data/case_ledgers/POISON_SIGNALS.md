# Poison Signals

A case is **poisoned** if it hits **two or more** structured poison fields:

| Field | Meaning |
|---|---|
| `poison_five_plus_over_500k` | 5+ relevant YouTube videos over 500K views |
| `poison_covered_by_major_creator` | Covered by a major creator (EWU / JCS / Red Tree / etc.) |
| `poison_name_famous` | Name-driven case already famous |
| `poison_heavily_clipped` | Primary evidence already heavily clipped on TikTok/Shorts |
| `poison_no_new_update` | No new document / bodycam / court update |
| `poison_heavily_politicized` | Heavily politicized; comments become ideology war |
| `poison_needs_psych_claims` | Requires clinical psychology claims to be interesting |
| `poison_poor_footage` | Footage quality is poor or fragmented |

`count_poison_signals()` runs during CSV load/validation. Rows with **2+** true poison fields cannot keep a `strong` or `maybe` verdict. `launch_shortlist()` enforces the same rule independently of the CSV verdict.

## Avoid-first categories (seed poisoned ledger)

| Avoid First | Why |
|---|---|
| Chris Watts | Fully saturated, no fresh bodycam value left |
| Sarah Boone | Saturated by court/interrogation creators |
| Darrell Brooks | Over-mined; strong creators already own courtroom angle |
| Sherri Papini | Familiar, documentary-heavy coverage |
| Chandler Halderson | Strong interrogation coverage already exists |
| Jodi Arias / Casey Anthony / Peterson-type legacy | Searchable but stale and high competition |
| Ruby Franke / Jodi Hildebrandt | High demand, but saturated and emotionally/politically charged |
| George Floyd / Chauvin | Too politically radioactive for channel launch |
| Gabby Petito / Brian Laundrie | Saturated, little fresh bodycam angle left |
| Karen Read | Active interest but factional and legally messy |

## Better prospect types

| Prospect Type | Why It Works |
|---|---|
| Local bodycam incident with court outcome | Footage + consequence |
| Routine stop became felony chain | Title mechanics + low production burden |
| Officer decision mistake with lawsuit outcome | Higher-value legal/procedural angle |
| Welfare check / mental health escalation | Decision-chain rich |
| DUI with unusual legal aftermath | Easy entry, strong consequence framing |
| Missing person solved by patrol/bodycam detail | Mystery + procedure + aftermath |

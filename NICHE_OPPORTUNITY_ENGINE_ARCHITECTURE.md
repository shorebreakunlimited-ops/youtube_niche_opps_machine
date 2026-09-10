# YouTube Niche Opportunity Search Engine
## System Architecture, Quantitative Specification & Engineering Blueprint

**Document Version:** 2.2.0 (Architectural Freeze & Definitive Quantitative Blueprint)  
**Date:** September 10, 2026  
**Status:** Architecture Frozen / Ready for P0 Implementation  
**Primary Author:** Lead Quantitative Analyst & Product Architect  

---

## Executive Summary & Core Philosophy

The **YouTube Niche Opportunity Search Engine** is an evidence-driven quantitative engine designed to identify underserved, accelerating, and structurally repeatable YouTube content markets before they reach obvious saturation.

### 1. The Fundamental Axiom: Demand vs. Competent Supply Imbalance

Commercial creator tools often equate **high aggregate view counts** with **opportunity**. This is fundamentally flawed:
* A niche with 50 million monthly views dominated by 3 entrenched studio-scale incumbents with 10M+ subscribers presents **negative opportunity** for a new creator.
* A niche with 2 million monthly views where 5 separate channels under 15,000 subscribers are generating 200,000+ views per video demonstrates **acute, unmet audience demand**.

### 2. Multi-Dimensional Score Decoupling

To prevent conflating market audience dynamics with external commercial mechanics, creator operational constraints, or data sampling uncertainty, the engine strictly decouples its analytical outputs into distinct, independent vectors:

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             ANALYTICAL OUTPUT VECTORS                            │
├──────────────────────────┬────────────────────────────┬──────────────────────────┤
│ 1. CONTENT OPPORTUNITY   │ 2. COMMERCIAL ATTRACTIVE.  │ 3. CREATOR FEASIBILITY   │
│    (Pure Market Dynamics)│    (Business Monetization) │    (Operational & Legal) │
│ • Demand Velocity (D)    │ • Ad / CPM Alignment       │ • Production Feasibility │
│ • Supply Scarcity (S)    │ • Sponsor Density          │   (100 - Prod. Risk)     │
│ • Acceleration (A)       │ • Affiliate Viability      │ • Rights Safety          │
│ • Breakout Potential (B) │                            │   (100 - Rights Risk)    │
│ • Topic Runway Depth (R) │                            │                          │
│ • Trend Durability (U)   │                            │                          │
│ • Outlier Distortion (P) │                            │                          │
├──────────────────────────┴────────────────────────────┴──────────────────────────┤
│ 4. CREATOR-ADJUSTED OPPORTUNITY (Practical Actionable Decision Score)            │
│    f(Content Opportunity, Production Feasibility, Rights Safety)                 │
├──────────────────────────────────────────────────────────────────────────────────┤
│ 5. EVIDENCE CONFIDENCE (Decision Gate / Uncertainty Quantification)              │
│    • Sample Size Quality • Temporal Quality • Baseline Tier • Source Agreement   │
└──────────────────────────────────────────────────────────────────────────────────┘
```

Confidence is never subtracted as a penalty from opportunity scores; it functions strictly as an evidence gatekeeper for recommendations.

---

## 1. Phase 1: Repository & Environment Inspection

A full inspection of the runtime environment, credentials, and repository was conducted on September 10, 2026.

### 1.1 Repository State
* **Git Status:** Clean git repository on branch `main` at commit `77f1789 ("Initial commit")`.
* **Existing Files:** Only a single top-level `README.md`. No legacy or deprecated codebase to unwind.
* **Workspace:** Clean slate ready for a production-grade, modular Python architecture.

### 1.2 Environment & Tooling Verification
* **Operating System:** Linux 6.12.94+ x86_64, Python 3.12.3, Node.js v22.22.2.
* **Core Libraries Present:** `numpy` (2.4.4), `requests` (2.33.1), `urllib3` (2.6.3), `PyYAML` (6.0.1), `sqlite3` (built-in).
* **BrowserAct Automation Layer:**
  * Installed `browser-act-cli` v1.4.2.
  * Successfully passed version handshake (`browser-act get-skills core --skill-version 2.0.2`).
  * Injected secret `BROWSWER_ACT_API_KEY` configured and authenticated.
  * Verified live JS-rendered extraction using `browser-act stealth-extract`.
* **YouTube Data API v3 Layer (Verified Google September 2026 Specifications):**
  * Injected secret `YOUTUBE_API_KEY` verified live via a 1-unit `videos.list` endpoint call.
  * **Granular Quota Architecture:**
    * `search.list`: 1 unit per call with its own independent, default bucket of **100 calls/day**.
    * `videos.batchGetStats` (added June 2026): 1 unit per batch call (up to 50 video IDs) with its own independent, default bucket of **10,000 units/day**.
    * `videos.list`: 1 unit per batch call (up to 50 items).

### 1.3 Key Architectural Mandates
1. **No Reliance on YouTube Analytics for Competitors:** Third-party Analytics metrics (private retention curves, internal demographics, exact revenue/RPM) are strictly inaccessible for unowned competitor channels. All competitor intelligence is built exclusively on public Data API signals, public video statistics, and derived temporal models.
2. **Mandatory Normalized Snapshot Persistence:** A single static search query cannot distinguish a dying giant from an accelerating breakout. The engine mandates persistent, normalized SQLite observation snapshots to measure historical velocity (7d, 30d, 90d), creator entry rates, and breakout momentum.
3. **Graceful Degradation:** The collection layer follows a strict priority cascade:
   1. Official YouTube Data API v3 (batched)
   2. BrowserAct stealth extraction (for autocomplete, related queries, visual layouts)
   3. Inferred deterministic statistics
   4. Never use LLMs to fabricate quantitative metrics.

---

## 2. System Architecture & Modular Layout

```
youtube_niche_opps_machine/
├── config/
│   └── default_config.yaml         # Configurable weights, thresholds, floors, penalties
├── docs/
│   └── NICHE_OPPORTUNITY_ENGINE_ARCHITECTURE.md
├── src/
│   ├── __init__.py
│   ├── cli.py                      # Main CLI entrypoint (discover, validate, watchlist, rescan)
│   ├── collectors/
│   │   ├── __init__.py
│   │   ├── base.py                 # Abstract Base Collector with retries & cache interface
│   │   ├── youtube_api.py          # Quota-tracked, batched YouTube Data API v3 client
│   │   ├── youtube_browser.py      # Autocomplete, search layout, and related suggestions
│   │   └── browseract_adapter.py   # Subprocess/HTTP client wrapper for BrowserAct CLI
│   ├── models/
│   │   ├── __init__.py
│   │   ├── video.py                # Video dataclass with temporal velocity & ratios
│   │   ├── channel.py              # Channel dataclass with median baselines & upload cadence
│   │   ├── niche.py                # Niche entity with hierarchy (market -> subniche -> format)
│   │   ├── observation.py          # Timestamped search observation records
│   │   └── validation_result.py    # Complete scorecard with transparent decoupled vectors
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── database.py             # SQLite persistence: normalized snapshots, split provenance
│   │   └── cache.py                # TTL-based request and payload cache
│   ├── scoring/
│   │   ├── __init__.py
│   │   ├── statistics.py           # Robust stats: MAD, robust z-score, percentile, Winsorization
│   │   ├── demand.py               # Audience demand velocity & engagement scoring
│   │   ├── supply.py               # Supply density vs concentration with configurable porous interaction
│   │   ├── acceleration.py         # Centered bounded tanh acceleration transformation
│   │   ├── breakout.py             # Bayesian Beta-Binomial shrinkage, zero-guarded diversity, LOO baseline
│   │   ├── repeatability.py        # Shannon entropy, inter-cluster differentiation, video runway
│   │   ├── monetization.py         # Independent commercial attractiveness scoring
│   │   ├── production_risk.py      # Operational solo AI creator feasibility scoring
│   │   ├── rights_risk.py          # Independent copyright/fair-use source material risk scoring
│   │   ├── confidence.py           # Multi-source data quality & guarded confidence gating model
│   │   └── opportunity.py          # Pure Content Opportunity & Creator-Adjusted Opportunity
│   ├── validation/
│   │   ├── __init__.py
│   │   ├── niche_validator.py      # Mode B orchestrator: executes end-to-end deep validation
│   │   ├── outlier_analysis.py     # Continuous bounded Top-1/Top-3 viral anomaly detection
│   │   ├── competitor_analysis.py  # Public channel metrics & cohort distribution
│   │   └── topic_depth.py          # 15-axis domain-neutral query expansion with mathematical guards
│   ├── discovery/
│   │   ├── __init__.py
│   │   ├── query_expander.py       # Seed expansion across universal domain-neutral axes
│   │   ├── niche_extractor.py      # Extracts candidate niches from search/suggest
│   │   └── semantic_deduper.py     # Deduplication and clustering
│   ├── simulation/
│   │   ├── __init__.py
│   │   └── sensitivity.py          # Monte Carlo weight perturbation & full distribution rank metrics
│   └── reports/
│       ├── __init__.py
│       ├── console.py              # Formatted terminal scorecard
│       ├── json_export.py          # JSON serialization
│       └── csv_export.py           # CSV tabular export
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # Synthetic niche fixtures (breakout, viral, saturated)
│   ├── test_statistics.py          # Unit tests for robust math
│   ├── test_scoring.py             # Unit tests for component scores & clamping
│   ├── test_breakout.py            # Unit tests for Beta-Binomial shrinkage, LOO baselines, zero diversity
│   ├── test_outlier.py             # Unit tests for continuous bounded outlier penalties
│   ├── test_youtube_api.py         # Unit tests for batched requests & quota tracking
│   ├── test_database.py            # Tests for SQLite normalized snapshots & provenance split
│   ├── test_topic_depth.py         # Tests for topic runway, entropy, and mathematical edge guards
│   ├── test_interactions.py        # Correlated-factor amplification tests (Breakout x HHI)
│   └── test_sensitivity.py         # Tests for Monte Carlo ranking stability & distribution metrics
├── pyproject.toml
└── README.md
```

---

## 3. Mathematical & Quantitative Models

### 3.1 Robust Statistical Foundations (`src/scoring/statistics.py`)
To prevent extreme viral outliers from distorting median performance, the engine uses robust non-parametric statistics:

* **Median Absolute Deviation (MAD):**
  $$\text{MAD} = \text{median}\left(|X_i - \text{median}(X)|\right)$$
* **Robust Z-Score:**
  $$Z_i = \frac{0.6745 \cdot (X_i - \text{median}(X))}{\max(\text{MAD}, \epsilon)}$$
* **Percentile Rank:**
  $$P(X_i) = \frac{\text{rank}(X_i)}{N} \times 100$$
* **Safe Ratio:**
  $$\text{safe\_ratio}(a, b, \text{floor}) = \frac{a}{\max(b, \text{floor})}$$

---

### 3.2 Temporal Velocity: Real Snapshots vs. Cold-Start Proxy (`src/scoring/acceleration.py`)

A fundamental quantitative flaw is treating lifetime views divided by age as "current velocity." The engine explicitly delineates two velocity definitions:

1. **Snapshot Delta Velocity ($\text{VEL}_{\text{snapshot}}$):**
   When two distinct observations exist at $t_1$ and $t_2$ ($t_2 > t_1$):
   $$\text{VEL}_{\text{snapshot}} = \frac{\text{views}(t_2) - \text{views}(t_1)}{\max(\text{days}(t_2 - t_1), 0.0417)}$$
   *(where $0.0417\text{ days} = 1\text{ hour}$ floor).*

2. **Lifetime Proxy Velocity ($\text{VEL}_{\text{proxy}}$):**
   Cold-start fallback when only a single observation is available:
   $$\text{VEL}_{\text{proxy}} = \frac{\text{lifetime\_views}}{\max(\text{video\_age\_days}, 1.0)}$$

**Confidence Impact:** Whenever $\text{VEL}_{\text{proxy}}$ must be used due to lack of historical snapshots, the temporal confidence component is penalized:
$$C_{\text{temporal}} = \begin{cases} 1.0, & \text{if } \ge 70\% \text{ of sample has snapshot delta} \\ 0.75, & \text{if } 30\% - 70\% \text{ has snapshot delta} \\ 0.40, & \text{if purely lifetime proxy (cold-start)} \end{cases}$$

---

### 3.3 Centered Bounded Acceleration Score (`src/scoring/acceleration.py`)

The initial logarithmic formula ($50 \log_{1.5}(1 + \text{ratio})$) was defective because at neutral momentum ($\text{ratio} = 1.0$), it mapped to approximately **$85.5$**, and clipped to $100$ at merely $\approx 1.5\times$ growth.

The engine implements a mathematically symmetric, centered, bounded hyperbolic tangent transformation:

$$\text{Acceleration Score} = 50 + 50 \cdot \tanh\left(k \cdot \ln\left(\frac{\text{recent\_velocity}}{\max(\text{baseline\_velocity}, \epsilon)}\right)\right)$$

#### Properties of this Formulation:
* **Contracting Markets ($\text{recent} < \text{baseline}$):** $\ln(\text{ratio}) < 0 \implies \text{Score} \in [0, 50)$.
* **Neutral / Equilibrium ($\text{recent} = \text{baseline}$):** $\ln(1.0) = 0 \implies \tanh(0) = 0 \implies \mathbf{\text{Score} = \text{exactly } 50.0}$.
* **Accelerating Markets ($\text{recent} > \text{baseline}$):** $\ln(\text{ratio}) > 0 \implies \text{Score} \in (50, 100]$.
* **Configurable Sensitivity Parameter $k$:**
  * Default: $k = 1.0$.
  * At $k = 1.0$:
    * $0.5\times$ velocity (halving) $\implies \ln(0.5) = -0.693 \implies 50 + 50(-0.600) = \mathbf{20.0}$
    * $1.0\times$ velocity (neutral) $\implies \mathbf{50.0}$
    * $2.0\times$ velocity (doubling) $\implies \ln(2.0) = +0.693 \implies 50 + 50(+0.600) = \mathbf{80.0}$
    * $4.0\times$ velocity (quadrupling) $\implies \ln(4.0) = +1.386 \implies 50 + 50(+0.882) = \mathbf{94.1}$
    * Approximates 100 asymptotically for extreme momentum without premature clipping.

---

### 3.4 Small-Channel Breakout Analysis with Empirical Bayesian Shrinkage (`src/scoring/breakout.py`)

#### 1. The Shrinkage Problem
A raw breakout rate $k/n$ gives excessive weight to tiny samples: a niche with 1 breakout out of 2 eligible videos ($50\%$) would erroneously outrank a proven market with 25 breakouts out of 150 videos ($16.7\%$).

#### 2. Beta-Binomial Smoothed Breakout Estimator
The engine applies Bayesian conjugate smoothing:

$$\hat{p}_{\text{breakout}} = \frac{k_{\text{breakouts}} + \alpha}{n_{\text{eligible\_videos}} + \alpha + \beta}$$

* **Prior Parameters:** $\alpha = 1.0$, $\beta = 19.0$ (initial calibration prior, configurable; serves as a reasonable starting baseline until sufficient empirical engine data is collected across scans).
* **Sample Size Transparency:** $n_{\text{eligible\_videos}}$ is prominently exposed in all outputs alongside $\hat{p}_{\text{breakout}}$.
* **Behavior:**
  * $k = 1, n = 2 \implies \hat{p} = \frac{1 + 1}{2 + 1 + 19} = \frac{2}{22} \approx \mathbf{9.1\%}$ (properly shrunken).
  * $k = 25, n = 150 \implies \hat{p} = \frac{25 + 1}{150 + 1 + 19} = \frac{26}{170} \approx \mathbf{15.3\%}$ (retains high confidence).

#### 3. Zero-Guarded Breakout Diversity
To prevent phantom breakout points in markets with zero observed breakouts:

$$\text{diversity} = \begin{cases} 0.0, & \text{if } k_{\text{breakouts}} = 0 \\ \frac{\text{distinct\_breakout\_channels}}{\max(k_{\text{breakouts}}, 1)}, & \text{if } k_{\text{breakouts}} > 0 \end{cases}$$

#### 4. Leave-One-Out (LOO) Baseline Quality Tiers:
Candidate breakout videos are strictly excluded from their own baseline:
* **Tier A (Snapshot-Derived Age-Matched Baseline):** Compares candidate video's view velocity at day $D$ against the channel's historical median view velocity at the exact same age milestone $D$, excluding the candidate video.
* **Tier B (Age-Adjusted Historical Baseline):** Computes channel median from prior videos ($v_j \ne v_{\text{candidate}}$), normalized by historical velocity decay curves.
* **Tier C (Raw Recent-Video Median Proxy):**
  $$\text{baseline}_{\text{LOO}}(v_i) = \max\left(\text{median}\left(\{\text{views}(v_j) \mid v_j \in \text{Channel}, j \ne i\}\right), \; \text{baseline\_floor}\right)$$
  *(floor default: $100$ views).*

#### 5. Dual Definition of "Small Channel":
A channel qualifies if it meets either an absolute limit or a niche-relative cohort threshold:
1. **Absolute Subscriber Criterion:** $\text{subs} \le \text{small\_channel\_sub\_limit}$ (default: $50,000$).
2. **Niche-Relative Channel Size Percentile ($P_{\text{size}}$):**
   $$P_{\text{size}}(\text{channel}) = \frac{\text{rank}(\text{subs}_{\text{channel}})}{M_{\text{channels}}} \times 100$$
3. **Niche-Relative Video Performance Percentile ($P_{\text{perf}}$):**
   $$P_{\text{perf}}(v) = \frac{\text{rank}(\text{velocity}_v)}{N_{\text{videos}}} \times 100$$

**Breakout Qualification Rule:**
A video qualifies as a high-signal small-channel breakout if:
$$\left(\text{subs} \le 50,000 \lor P_{\text{size}} \le 25.0\right) \land \left(\frac{\text{views}(v)}{\text{baseline}_{\text{LOO}}(v)} \ge 3.0\right) \land \left(P_{\text{perf}}(v) \ge 75.0\right)$$

#### 6. Small-Channel Breakout Score:
$$\text{Breakout Score} = \min\left(100.0, \; 100 \cdot \left(0.65 \cdot \frac{\hat{p}_{\text{breakout}}}{\text{target\_breakout\_rate}} + 0.35 \cdot \text{diversity}\right)\right)$$
where $\text{target\_breakout\_rate} = 0.25$. When $k = 0$, $\text{diversity} = 0.0$ and score reflects only the prior floor ($\approx 12.0$).

---

### 3.5 Supply Scarcity & Competition Structure with Configurable Neutralization (`src/scoring/supply.py`)

A low-density market with one dominant incumbent and frequent newcomer breakouts represents a prime opportunity. Directly subtracting HHI penalizes this dynamic.

The engine decomposes Supply into **Supply Density** and **Competition Accessibility**, creating an interaction term with newcomer breakout success.

#### 1. Supply Density ($D_{\text{supply}}$):
Measures creator saturation, upload cadence, and competitor crowding:
$$D_{\text{supply}} = 0.40 \cdot D_{\text{creator\_norm}} + 0.35 \cdot D_{\text{cadence\_norm}} + 0.25 \cdot G_{\text{supply\_growth}}$$
$$\text{Base Scarcity} = 100 \cdot (1.0 - D_{\text{supply}})$$

#### 2. Incumbent Friction Factor ($\gamma$) with Configurable Neutralization:
Let $\text{HHI}_{\text{norm}} \in [0, 1]$ and $S_{\text{incumbent}} \in [0, 1]$ measure concentration.
The degree to which incumbent concentration acts as a barrier is modulated by observed breakout rate:

$$\gamma = \max\left(0.0, \; 1.0 - \frac{\hat{p}_{\text{breakout}}}{p_{\text{neutralize}}}\right)$$

* Default configurable parameter: $p_{\text{neutralize}} = 0.20$.
* Exact behavior:
  * $\hat{p} = 0.00 \implies \gamma = 1.00$ (Full HHI penalty applied).
  * $\hat{p} = 0.05 \implies \gamma = 0.75$ (75% penalty active).
  * $\hat{p} = 0.10 \implies \gamma = 0.50$ (50% penalty active).
  * $\hat{p} = 0.15 \implies \gamma = 0.25$ (25% penalty active).
  * $\hat{p} \ge 0.20 \implies \mathbf{\gamma = 0.00}$ (HHI penalty completely neutralized; market is proven porous).

#### 3. Unified Supply Scarcity Score:
$$\text{Supply Scarcity Score} = \text{clamp}\left(\text{Base Scarcity} - \gamma \cdot \left(25.0 \cdot \text{HHI}_{\text{norm}} + 20.0 \cdot S_{\text{incumbent}}\right), \; 0, \; 100\right)$$

---

### 3.6 Continuous Bounded Outlier Penalty (`src/validation/outlier_analysis.py`)

The outlier penalty measures pure market demand distortion—i.e., whether apparent demand is an artifact of one viral anomaly.

The engine implements a smooth, continuously differentiable surface across $\text{top1}$ and $\text{top3}$ view share, bounded strictly in $[0, 40]$:

$$P_{\text{outlier}} = 40.0 \cdot \left(\frac{1}{1 + \exp\left(-15 \cdot (\text{top1\_share} - 0.55)\right)} \cdot 0.65 + \frac{1}{1 + \exp\left(-15 \cdot (\text{top3\_share} - 0.78)\right)} \cdot 0.35\right)$$

#### Properties:
* **Strictly Bounded:** $P_{\text{outlier}} \in [0, 40.0]$ under all conditions.
* **Continuous & Monotonic:** Never negative; smoothly escalates as concentration rises.
* **Balanced Impact:** At $\text{top1} = 0.30, \text{top3} = 0.50 \implies P_{\text{outlier}} \approx 0.7$ (negligible). At $\text{top1} = 0.75, \text{top3} = 0.95 \implies P_{\text{outlier}} \approx 39.5$ (near maximum).

---

### 3.7 Topic Runway with Mathematical Edge Guards (`src/validation/topic_depth.py`)

To eliminate undefined divisions at $K = 1$ and undefined distances at $K < 2$, explicit mathematical guards are enforced:

#### Universal 15-Axis Base Ontology:
1. `entities`: Core subjects, figures, objects, organizations.
2. `events_cases`: Specific real-world occurrences, milestones, case studies.
3. `problems`: Puzzles, bottlenecks, hurdles, mysteries, errors.
4. `solutions`: Fixes, workarounds, engineering remedies, strategies.
5. `mechanisms_processes`: How something works, step-by-step causality.
6. `questions`: Beginner FAQ, intermediate how-tos, advanced conceptual debates.
7. `comparisons`: Versus matches, trade-offs, benchmarks, rankings.
8. `audiences`: Target segments (beginners, hobbyists, practitioners, executives).
9. `expertise_levels`: 101 foundational to expert deep-dives.
10. `products_tools`: Equipment, software, instruments, materials.
11. `locations`: Geographic, spatial, institutional environments.
12. `time_periods`: Historical eras, current state, future trajectories.
13. `controversies`: Competing hypotheses, debates, legal/ethical friction.
14. `formats`: Documentaries, deep-dives, timelines, teardowns, listicles.
15. `adjacent_topics`: Lateral crossovers, related niches.

#### Guarded Mathematical Metrics:
1. **Guarded Shannon Entropy Ratio ($E_{\text{norm}}$):**
   $$E_{\text{norm}} = \begin{cases} 1.0, & \text{if } K_{\text{clusters}} \le 1 \\ \frac{-\sum_{c=1}^K p_c \ln(p_c)}{\ln(K_{\text{clusters}})}, & \text{if } K_{\text{clusters}} \ge 2 \end{cases}$$
2. **Guarded Inter-Cluster Differentiation ($D_{\text{inter}}$):**
   $$D_{\text{inter}} = \begin{cases} 1.0, & \text{if } K_{\text{clusters}} \le 1 \\ \frac{1}{\binom{K}{2}} \sum_{i < j} \text{cosine\_distance}(\mu_i, \mu_j), & \text{if } K_{\text{clusters}} \ge 2 \end{cases}$$
3. **Guarded Estimated Video Depth:**
   $$\text{Runway Depth} = K_{\text{clusters}} \cdot (1 - R_{\text{dup}}) \cdot E_{\text{norm}} \cdot D_{\text{inter}}$$

#### Calibrated Runway Scale:
* $< 15$: **WEAK** (Single video or series only, cannot sustain a channel)
* $15 - 34$: **LIMITED** (Short-term series)
* $35 - 69$: **WORKABLE** (Multi-month viable channel)
* $70 - 119$: **STRONG** (Multi-year catalog viability)
* $\ge 120$: **EXTENSIVE RUNWAY** ($100+$ Video Catalog Viability)

---

### 3.8 Decoupled Scoring Architectures

#### 1. Pure Content Opportunity Score ($0 - 100$ Scale):
Measures purely observable audience demand, supply scarcity, acceleration, small-channel breakout rates, topic runway, and trend durability, adjusted strictly for market-level outlier distortion:

$$\text{CO}_{\text{raw}} = 0.25 D + 0.20 S + 0.18 A + 0.20 B + 0.10 R + 0.07 U$$

$$\mathbf{\text{Content Opportunity Score}} = \text{clamp}\left(\text{CO}_{\text{raw}} - P_{\text{outlier}}, \; 0, \; 100\right)$$

*Answers: "How attractive is this content market independent of my ability to produce it?"*

#### 2. Creator Feasibility Scores ($0 - 100$ Scale):
Measures operational friction and intellectual property risks for a solo AI-assisted creator:

* **Production Risk Score ($0 - 100$):**
  * Research burden / fact-checking requirements ($0 - 25$)
  * Original footage / camera capture requirements ($0 - 25$)
  * Complex animation / 3D simulation burden ($0 - 25$)
  * Audio/Voiceover and editing complexity ($0 - 25$)
  $$\mathbf{\text{Production Feasibility}} = 100 - \text{Production Risk Score}$$

* **Rights Risk Score ($0 - 100$):**
  * Studio TV / Film footage dependence ($0 - 30$)
  * Professional sports broadcast footage dependence ($0 - 30$)
  * Commercial music dependence ($0 - 20$)
  * Celebrity likeness / private individual exposure ($0 - 20$)
  $$\mathbf{\text{Rights Safety}} = 100 - \text{Rights Risk Score}$$

#### 3. Creator-Adjusted Opportunity Score:
Combines pure market attractiveness with creator feasibility deductions:

$$\text{Creator Deduction} = 0.35 \cdot \text{Production Risk Score} + 0.40 \cdot \text{Rights Risk Score}$$
$$\text{Effective Creator Penalty} = 40.0 \cdot \tanh\left(\frac{\text{Creator Deduction}}{35.0}\right)$$

$$\mathbf{\text{Creator-Adjusted Opportunity}} = \text{clamp}\left(\text{Content Opportunity Score} - \text{Effective Creator Penalty}, \; 0, \; 100\right)$$

*Answers: "Given market demand AND my operational/rights constraints, should I build this channel?"*

*Important Discovery Ranking Policy:*
Mode A Automated Discovery ranks candidate niches exclusively on **Content Opportunity Score** with **Confidence gating**. **Creator-Adjusted Opportunity** is strictly withheld from discovery ranking and used solely in the user-facing "Should I build this?" decision layer.

#### 4. Commercial Attractiveness Score ($0 - 100$ Scale):
Reported independently to decouple business monetizability from organic content appetite:
$$\mathbf{\text{Commercial Attractiveness Score}} = 0.40 \cdot \text{AdRateIndex} + 0.35 \cdot \text{SponsorAffinity} + 0.25 \cdot \text{AffiliateViability}$$

---

### 3.9 Well-Specified Source Agreement Confidence with Single-Source Guard

To prevent a single source from falsely receiving perfect agreement with itself, explicit guards and dynamic reweighting are implemented:

1. Let each source $s \in \{\text{YouTube API}, \text{Search Layout}, \text{Google/Browser Suggest}\}$ produce an independent normalized demand index $\theta_s \in [0, 1]$.
2. **Single-Source Guard:**
   $$\text{If } |S| < 2: \quad C_{\text{agreement}} = \text{None}, \quad \text{cross\_source\_validation} = \text{"UNAVAILABLE"}$$
3. When $|S| \ge 2$:
   $$\bar{\theta} = \text{mean}(\theta_s)$$
   $$\Delta_{\text{sources}} = \frac{1}{|S|} \sum_{s \in S} |\theta_s - \bar{\theta}|$$
   $$C_{\text{agreement}} = \text{clamp}\left(1.0 - 2.0 \cdot \Delta_{\text{sources}}, \; 0.0, \; 1.0\right)$$

#### Dynamic Confidence Calculation:
* **When $|S| \ge 2$:**
  $$\mathbf{\text{Confidence Score}} = 100 \cdot \left(0.35 \cdot C_{\text{sample}} + 0.25 \cdot C_{\text{temporal}} + 0.20 \cdot C_{\text{breakout\_tier}} + 0.20 \cdot C_{\text{agreement}}\right)$$
* **When $|S| < 2$ (Reweighted without phantom agreement credit):**
  $$\mathbf{\text{Confidence Score}} = 100 \cdot \left(\frac{0.35}{0.80} \cdot C_{\text{sample}} + \frac{0.25}{0.80} \cdot C_{\text{temporal}} + \frac{0.20}{0.80} \cdot C_{\text{breakout\_tier}}\right) \times 0.85$$
  *(Penalized by $15\%$ for lack of cross-source validation).*

---

### 3.10 Unambiguous Recommendation Precedence Matrix

Evaluated via an explicit sequential decision tree. The first condition met triggers the recommendation:

```
[ Evaluation Start ]
         │
         ▼
[ Condition 1: Confidence < 40 OR Eligible Videos < 10 ] ──YES──► INSUFFICIENT EVIDENCE
         │ NO
         ▼
[ Condition 2: Rights Safety < 55 (Rights Risk > 45) ] ─────YES──► HIGH RIGHTS RISK
         │ NO
         ▼
[ Condition 3: Production Feasibility < 45 (Risk > 55) ] ───YES──► HIGH PRODUCTION RISK
         │ NO
         ▼
[ Condition 4: Outlier Share top1 > 65% ] ───────────────────YES──► VIRAL OUTLIER
         │ NO
         ▼
[ Condition 5: Demand Score D < 35 ] ────────────────────────YES──► WEAK DEMAND
         │ NO
         ▼
[ Condition 6: Supply Scarcity S < 30 ] ─────────────────────YES──► SATURATED
         │ NO
         ▼
[ Condition 7: CreatorAdjustedOpp >= 75 AND Conf >= 70 ] ────YES──► STRONG OPPORTUNITY
         │ NO
         ▼
[ Condition 8: CreatorAdjustedOpp >= 65 AND Conf >= 60 ] ────YES──► PROMISING
         │ NO
         ▼
[ Condition 9: Acceleration >= 65 OR Breakout >= 65 ] ───────YES──► WATCHLIST
         │ NO
         ▼
[ Else ] ─────────────────────────────────────────────────────► REJECT
```

---

## 4. Normalized Relational Database Schema (`src/storage/database.py`)

Provenance is cleanly split between membership and discovery occurrences, and controlled search observations record complete reproducible query contexts:

```sql
-- Core Entities
CREATE TABLE IF NOT EXISTS niches (
    niche_id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    market TEXT,
    subniche TEXT,
    format TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS channels (
    channel_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    custom_url TEXT,
    created_at TEXT, -- Overall YouTube channel creation date
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS videos (
    video_id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL,
    title TEXT NOT NULL,
    published_at TEXT NOT NULL,
    duration TEXT,
    category_id TEXT,
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(channel_id) REFERENCES channels(channel_id)
);

-- Niche Membership (Split from Discovery)
CREATE TABLE IF NOT EXISTS niche_video_memberships (
    niche_id TEXT NOT NULL,
    video_id TEXT NOT NULL,
    relevance_score REAL NOT NULL,
    primary_cluster_id TEXT,
    first_seen_in_niche TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_in_niche TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (niche_id, video_id),
    FOREIGN KEY(niche_id) REFERENCES niches(niche_id),
    FOREIGN KEY(video_id) REFERENCES videos(video_id)
);

-- Niche Video Discovery Events (Multiple Paths Preserved)
CREATE TABLE IF NOT EXISTS niche_video_discoveries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    niche_id TEXT NOT NULL,
    video_id TEXT NOT NULL,
    discovery_method TEXT NOT NULL, -- 'seed_search', 'suggest_expansion', 'related_graph'
    originating_query TEXT NOT NULL,
    rank_position INTEGER,
    observed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(niche_id) REFERENCES niches(niche_id),
    FOREIGN KEY(video_id) REFERENCES videos(video_id)
);

-- Normalized Metric Snapshots (Time-Series)
CREATE TABLE IF NOT EXISTS video_metric_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT NOT NULL,
    observed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    views INTEGER NOT NULL,
    likes INTEGER,
    comments INTEGER,
    FOREIGN KEY(video_id) REFERENCES videos(video_id)
);

CREATE TABLE IF NOT EXISTS channel_metric_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT NOT NULL,
    observed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    subscribers INTEGER,
    total_views INTEGER,
    video_count INTEGER,
    FOREIGN KEY(channel_id) REFERENCES channels(channel_id)
);

-- Controlled Search Observations (Fully Reproducible Query Context)
CREATE TABLE IF NOT EXISTS search_rank_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    query TEXT NOT NULL,
    video_id TEXT NOT NULL,
    rank_position INTEGER NOT NULL,
    observed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    region TEXT DEFAULT 'US',
    language TEXT DEFAULT 'en',
    order_param TEXT DEFAULT 'relevance',
    device_context TEXT DEFAULT 'desktop', -- 'desktop', 'mobile'
    search_context TEXT DEFAULT 'api',     -- 'api', 'browser_stealth', 'suggest'
    FOREIGN KEY(video_id) REFERENCES videos(video_id)
);

-- Validation Snapshots & Watchlist
CREATE TABLE IF NOT EXISTS validation_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    niche_id TEXT NOT NULL,
    validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    content_opportunity_score REAL NOT NULL,
    creator_adjusted_opportunity REAL NOT NULL,
    commercial_attractiveness_score REAL NOT NULL,
    production_feasibility REAL NOT NULL,
    rights_safety REAL NOT NULL,
    confidence_score REAL NOT NULL,
    demand_score REAL NOT NULL,
    supply_scarcity REAL NOT NULL,
    acceleration_score REAL NOT NULL,
    breakout_score REAL NOT NULL,
    repeatability_score REAL NOT NULL,
    recommendation TEXT NOT NULL,
    raw_payload_json TEXT NOT NULL,
    FOREIGN KEY(niche_id) REFERENCES niches(niche_id)
);

CREATE TABLE IF NOT EXISTS watchlist (
    niche_id TEXT PRIMARY KEY,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    target_score_threshold REAL DEFAULT 75.0,
    active INTEGER DEFAULT 1,
    FOREIGN KEY(niche_id) REFERENCES niches(niche_id)
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_video_snapshots ON video_metric_snapshots(video_id, observed_at);
CREATE INDEX IF NOT EXISTS idx_channel_snapshots ON channel_metric_snapshots(channel_id, observed_at);
CREATE INDEX IF NOT EXISTS idx_search_ranks ON search_rank_observations(query, observed_at);
CREATE INDEX IF NOT EXISTS idx_discoveries ON niche_video_discoveries(niche_id, video_id);
CREATE INDEX IF NOT EXISTS idx_memberships ON niche_video_memberships(niche_id, relevance_score);
```

---

## 5. Monte Carlo Sensitivity & Comprehensive Rank Stability (`src/simulation/sensitivity.py`)

The sensitivity engine outputs full rank and score distributions across $N = 1,000$ iterations:

1. Positive scoring weights for Content Opportunity ($D, S, A, B, R, U$) are perturbed by $\pm 25\%$:
   $$w_k' = w_k \cdot (1 + \delta_k), \quad \delta_k \sim \mathcal{U}(-0.25, +0.25)$$
   $$\hat{w}_k = \frac{w_k'}{\sum_j w_j'}$$
2. Scores and relative ranks are recalculated.
3. **Reported Distribution Metrics:**
   * **Median Rank:** Midpoint ordinal rank across simulations.
   * **$P_{05}$ Rank & $P_{95}$ Rank:** 5th and 95th percentile rank bounds.
   * **Absolute Rank Range:** $P_{95} - P_{05}$.
   * **Normalized Rank Stability:** $1.0 - \frac{P_{95} - P_{05}}{M_{\text{niches}}}$.
   * **Score Standard Deviation ($\sigma_{\text{opp}}$):** Volatility of the 0–100 score.
   * **$\mathbb{P}(\text{Rank } = 1)$:** Probability of ranking #1 among candidates.
   * **$\mathbb{P}(\text{Top } 3)$:** Probability of finishing in the top 3.
   * **$\mathbb{P}(\text{Top Decile})$:** Probability of finishing in the top 10%.

---

## 6. CLI Command Interface

```bash
# Mode A: Automated Discovery
python -m src.cli discover --seed "engineering failures" --depth 3 --limit 15

# Mode B: Deep Niche Validation
python -m src.cli validate "declassified administrative mysteries" --export-json report.json

# Competitor / Channel Concept Validation
python -m src.cli validate-channel "https://www.youtube.com/@PracticalEngineering"

# Side-by-Side Niche Comparison
python -m src.cli compare "Dam failures" "Ancient city reconstructions"

# Watchlist Management & Trend Rescan
python -m src.cli watchlist add "sports biomechanics breakdowns"
python -m src.cli rescan

# Sensitivity Simulation with Distribution Statistics
python -m src.cli simulate --scenarios 6 --iterations 1000
```

---

## 7. Phased Implementation Roadmap (P0 – P4)

| Phase | Milestone | Core Deliverables | Test & Verification Criteria |
|---|---|---|---|
| **P0** | **Engine Correctness & Relational Storage** | `statistics.py`, `models/`, `storage/database.py` (normalized snapshots, split provenance, contextual ranks), `config/default_config.yaml` | $100\%$ math unit tests (MAD, Z-score, safe ratio, LOO baseline, schema migrations, snapshot delta tests). Mandatory tests: `test_zero_breakouts_do_not_receive_diversity_credit`, `test_incumbent_friction_reaches_zero_at_configured_breakout_threshold`. |
| **P1** | **Opportunity Core & Decoupled Vectors** | `acceleration.py` (centered tanh), `breakout.py` (Beta-Binomial shrinkage, LOO, dual small-channel, 0 diversity), `supply.py` (density vs. concentration interaction with $p_{\text{neutralize}}$), `outlier_analysis.py` (continuous sigmoid), `rights_risk.py`, `production_risk.py`, `confidence.py` (guarded single-source agreement), `opportunity.py`, decision tree recommendation engine | Synthetic fixtures (breakout, viral anomaly, saturated commodity, incumbent monopoly with breakouts, cold-start vs snapshot velocity) all evaluate with zero conflicts. Specific tests: `test_high_hhi_breakout_interaction_does_not_double_count_excessively`, `test_single_source_does_not_receive_perfect_agreement_confidence`. |
| **P2** | **Collectors & Mode B Deep Validation** | `youtube_api.py` (batched, quota-tracked: search.list 100 calls/day, videos.batchGetStats 10k units/day), `browseract_adapter.py`, `youtube_browser.py`, `niche_validator.py` | Live & mocked YouTube Data API calls, 50-item batching, TTL caching, graceful degradation when BrowserAct unavailable. |
| **P3** | **Discovery Expansion & Guarded Runway** | `query_expander.py` (15-axis domain-neutral ontology), `topic_depth.py` (entropy, differentiation, runway with $K \le 1$ guards), `niche_extractor.py`, `semantic_deduper.py` | Topic breadth testing, entropy calculation, deduplication against keyword collision. |
| **P4** | **Observability, Reports & Sensitivity Simulation** | `cli.py`, `console.py`, `json_export.py`, `sensitivity.py` (P05/P95, $\mathbb{P}(\text{Top 3})$, std dev) | End-to-end CLI runs, multi-scenario Monte Carlo stability simulations, historical watchlist delta tracking. |

---

*This specification represents the frozen, quantitatively calibrated architecture for the YouTube Niche Opportunity Search Engine.*

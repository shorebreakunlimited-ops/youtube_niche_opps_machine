"""Monte Carlo sensitivity and ranking stability simulation."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import numpy as np


@dataclass
class NicheStabilityMetrics:
    name: str
    baseline_rank: int
    baseline_score: float
    mean_score: float
    std_score: float
    p05_score: float
    p95_score: float
    min_score: float
    max_score: float
    mean_rank: float
    std_rank: float
    top1_probability: float
    top3_probability: float
    rank_variance: float


@dataclass
class SensitivityReport:
    iterations: int
    perturbation_pct: float
    average_spearman_rank_correlation: float
    candidate_metrics: List[NicheStabilityMetrics]
    weight_samples: Dict[str, List[float]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "iterations": self.iterations,
            "perturbation_pct": self.perturbation_pct,
            "average_spearman_rank_correlation": round(self.average_spearman_rank_correlation, 4),
            "candidates": [
                {
                    "name": m.name,
                    "baseline_rank": m.baseline_rank,
                    "baseline_score": round(m.baseline_score, 2),
                    "mean_score": round(m.mean_score, 2),
                    "std_score": round(m.std_score, 2),
                    "p05_score": round(m.p05_score, 2),
                    "p95_score": round(m.p95_score, 2),
                    "mean_rank": round(m.mean_rank, 2),
                    "top1_prob": round(m.top1_probability, 3),
                    "top3_prob": round(m.top3_probability, 3),
                }
                for m in self.candidate_metrics
            ],
        }


def _spearman_rank_correlation(ranks_a: List[float], ranks_b: List[float]) -> float:
    """Compute Spearman's rank correlation coefficient between two rank assignments."""
    n = len(ranks_a)
    if n <= 1:
        return 1.0
    arr_a = np.array(ranks_a, dtype=float)
    arr_b = np.array(ranks_b, dtype=float)
    # Pearson correlation of ranks
    cov = np.cov(arr_a, arr_b)
    std_a = np.std(arr_a)
    std_b = np.std(arr_b)
    if std_a == 0 or std_b == 0:
        return 1.0
    corr = cov[0, 1] / (std_a * std_b)
    return float(max(-1.0, min(1.0, corr)))


def simulate_monte_carlo_sensitivity(
    cohort_scores: List[Dict[str, Any]],
    base_weights: Optional[Dict[str, float]] = None,
    iterations: int = 500,
    perturbation_pct: float = 0.20,
    random_seed: int = 42,
) -> SensitivityReport:
    """Run Monte Carlo simulation perturbing component weights to evaluate ranking stability.
    
    Weights are perturbed independently within +/- perturbation_pct and normalized to sum to 1.0.
    """
    if not cohort_scores:
        return SensitivityReport(
            iterations=0,
            perturbation_pct=perturbation_pct,
            average_spearman_rank_correlation=1.0,
            candidate_metrics=[],
        )

    rng = np.random.default_rng(random_seed)

    default_weights = {
        "demand": 0.25,
        "supply": 0.20,
        "acceleration": 0.18,
        "breakout": 0.20,
        "repeatability": 0.10,
        "durability": 0.07,
    }
    weights_dict = base_weights or default_weights
    weight_keys = list(weights_dict.keys())
    base_w_arr = np.array([weights_dict[k] for k in weight_keys], dtype=float)
    base_w_arr /= np.sum(base_w_arr)  # ensure sum=1

    # Compute baseline scores and ranks
    baseline_scores = []
    for item in cohort_scores:
        score = sum(
            weights_dict.get(k, 0.0) * float(item.get(k, 50.0)) for k in weight_keys
        )
        score -= float(item.get("outlier_penalty", 0.0))
        baseline_scores.append(max(0.0, min(100.0, score)))

    n_candidates = len(cohort_scores)
    # Compute baseline 1-based ranks (1 is highest score)
    sorted_baseline_indices = np.argsort(-np.array(baseline_scores))
    baseline_ranks = [0] * n_candidates
    for r, idx in enumerate(sorted_baseline_indices, start=1):
        baseline_ranks[idx] = r

    # Storage for simulation outcomes
    sim_scores = [[] for _ in range(n_candidates)]
    sim_ranks = [[] for _ in range(n_candidates)]
    spearman_corrs = []
    weight_samples_record: Dict[str, List[float]] = {k: [] for k in weight_keys}

    for _ in range(iterations):
        # Draw perturbation factor uniformly in [1 - perturbation_pct, 1 + perturbation_pct]
        perturbations = rng.uniform(
            1.0 - perturbation_pct, 1.0 + perturbation_pct, size=len(base_w_arr)
        )
        draw_weights = base_w_arr * perturbations
        draw_weights /= np.sum(draw_weights)

        for k_idx, k in enumerate(weight_keys):
            weight_samples_record[k].append(float(draw_weights[k_idx]))

        draw_scores = []
        for item in cohort_scores:
            s = sum(
                draw_weights[i] * float(item.get(weight_keys[i], 50.0))
                for i in range(len(weight_keys))
            )
            s -= float(item.get("outlier_penalty", 0.0))
            clamped_s = max(0.0, min(100.0, s))
            draw_scores.append(clamped_s)

        # Compute ranks for this draw
        sorted_draw_indices = np.argsort(-np.array(draw_scores))
        draw_ranks = [0] * n_candidates
        for r, idx in enumerate(sorted_draw_indices, start=1):
            draw_ranks[idx] = r
            sim_scores[idx].append(draw_scores[idx])
            sim_ranks[idx].append(r)

        # Correlation between baseline ranks and draw ranks
        corr = _spearman_rank_correlation(baseline_ranks, draw_ranks)
        spearman_corrs.append(corr)

    # Compile candidate stability metrics
    metrics_list: List[NicheStabilityMetrics] = []
    for idx, item in enumerate(cohort_scores):
        name = item.get("name") or item.get("niche_name") or f"candidate_{idx+1}"
        scores_arr = np.array(sim_scores[idx])
        ranks_arr = np.array(sim_ranks[idx])

        metric = NicheStabilityMetrics(
            name=name,
            baseline_rank=baseline_ranks[idx],
            baseline_score=baseline_scores[idx],
            mean_score=float(np.mean(scores_arr)),
            std_score=float(np.std(scores_arr)),
            p05_score=float(np.percentile(scores_arr, 5)),
            p95_score=float(np.percentile(scores_arr, 95)),
            min_score=float(np.min(scores_arr)),
            max_score=float(np.max(scores_arr)),
            mean_rank=float(np.mean(ranks_arr)),
            std_rank=float(np.std(ranks_arr)),
            top1_probability=float(np.sum(ranks_arr == 1) / iterations),
            top3_probability=float(np.sum(ranks_arr <= 3) / iterations),
            rank_variance=float(np.var(ranks_arr)),
        )
        metrics_list.append(metric)

    # Sort candidates by baseline rank
    metrics_list.sort(key=lambda m: m.baseline_rank)

    return SensitivityReport(
        iterations=iterations,
        perturbation_pct=perturbation_pct,
        average_spearman_rank_correlation=float(np.mean(spearman_corrs)),
        candidate_metrics=metrics_list,
        weight_samples=weight_samples_record,
    )

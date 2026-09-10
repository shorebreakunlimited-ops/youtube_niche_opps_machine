"""Tests for Monte Carlo sensitivity simulation."""

import pytest
from src.simulation.sensitivity import simulate_monte_carlo_sensitivity


def test_monte_carlo_simulation_metrics():
    cohort = [
        {"name": "Niche A (Strong)", "demand": 85.0, "supply": 80.0, "acceleration": 75.0, "breakout": 85.0, "repeatability": 80.0, "durability": 70.0},
        {"name": "Niche B (Moderate)", "demand": 60.0, "supply": 55.0, "acceleration": 50.0, "breakout": 55.0, "repeatability": 60.0, "durability": 50.0},
        {"name": "Niche C (Weak)", "demand": 30.0, "supply": 35.0, "acceleration": 25.0, "breakout": 20.0, "repeatability": 30.0, "durability": 20.0},
    ]

    report = simulate_monte_carlo_sensitivity(
        cohort_scores=cohort,
        iterations=200,
        perturbation_pct=0.20,
        random_seed=123,
    )

    assert report.iterations == 200
    assert len(report.candidate_metrics) == 3
    assert report.average_spearman_rank_correlation > 0.90  # Clear separation should yield high rank stability

    m_a = report.candidate_metrics[0]
    m_b = report.candidate_metrics[1]
    m_c = report.candidate_metrics[2]

    assert m_a.name == "Niche A (Strong)"
    assert m_a.baseline_rank == 1
    assert m_a.top1_probability > 0.95
    assert m_a.mean_score > m_b.mean_score > m_c.mean_score
    assert m_a.p05_score <= m_a.mean_score <= m_a.p95_score


def test_monte_carlo_empty_cohort():
    report = simulate_monte_carlo_sensitivity([])
    assert report.iterations == 0
    assert len(report.candidate_metrics) == 0

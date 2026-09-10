"""Tests for 15-axis topic depth and guarded runway analysis."""

import pytest
from src.validation.topic_depth import UNIVERSAL_15_AXES, evaluate_topic_depth_and_runway


def test_universal_15_axes_structure():
    """Verify all 15 universal domain-neutral axes exist with valid structures."""
    assert len(UNIVERSAL_15_AXES) == 15
    for key, data in UNIVERSAL_15_AXES.items():
        assert "axis_id" in data
        assert "name" in data
        assert "keywords" in data
        assert len(data["keywords"]) >= 3
        assert "template" in data
        assert "{seed}" in data["template"]


def test_evaluate_topic_depth_and_runway_calculation():
    """Verify topic depth coverage, entropy ratio, and runway estimation."""
    seed = "cursor ai"
    titles = [
        "Cursor AI Tutorial for Beginners",
        "Cursor AI vs GitHub Copilot 2026",
        "5 Costly Mistakes When Using Cursor AI",
        "Full Step-by-Step Cursor AI Workflow",
        "How to Fix Common Cursor AI Errors",
        "Advanced Cursor AI System Architecture",
    ]
    suggestions = [
        "cursor ai tutorial",
        "cursor ai tips and tricks",
        "cursor ai for python",
        "cursor ai rules",
        "cursor ai pricing",
    ]

    res = evaluate_topic_depth_and_runway(seed, titles, suggestions)

    assert res["seed_topic"] == "cursor ai"
    assert res["total_axes"] == 15
    assert res["axes_covered_count"] >= 4
    # Guarded entropy ratio should be valid in [0.0, 1.0]
    assert 0.0 <= res["entropy_ratio"] <= 1.0
    # Guarded inter-cluster distance in [0.0, 1.0]
    assert 0.0 <= res["inter_cluster_distance"] <= 1.0
    # Runway should be at least length of templates + suggestions
    assert res["estimated_video_runway"] >= 15
    assert 0.0 <= res["repeatability_score"] <= 100.0
    assert len(res["generated_video_angles"]) == 15


def test_single_cluster_guarded_entropy():
    """Verify single cluster returns guarded 1.0 entropy ratio."""
    from src.scoring.statistics import guarded_entropy_ratio

    assert guarded_entropy_ratio([]) == 1.0
    assert guarded_entropy_ratio([10]) == 1.0
    assert guarded_entropy_ratio([0, 15, 0]) == 1.0

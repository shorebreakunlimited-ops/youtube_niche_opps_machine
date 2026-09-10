"""Operational production feasibility scoring for solo AI creators."""

from typing import Dict, Optional


def compute_production_risk(
    niche_text: str,
    custom_ratings: Optional[Dict[str, float]] = None,
) -> float:
    """Compute Production Risk Score in [0, 100].
    
    Production Feasibility = 100 - Production Risk Score.
    Covers:
    - Research burden / fact-checking (0-25)
    - Original live-camera footage burden (0-25)
    - 3D animation / complex simulation burden (0-25)
    - Audio/editing complexity (0-25)
    """
    if custom_ratings:
        research = custom_ratings.get("research_burden", 10.0)
        camera = custom_ratings.get("camera_footage_need", 10.0)
        animation = custom_ratings.get("animation_burden", 10.0)
        editing = custom_ratings.get("editing_complexity", 10.0)
        return float(min(100.0, max(0.0, research + camera + animation + editing)))

    # Heuristic analysis from keywords
    text = niche_text.lower()
    research = 12.0
    camera = 5.0
    animation = 8.0
    editing = 10.0

    if any(k in text for k in ["disaster", "engineering", "investigation", "mystery", "history"]):
        research += 8.0
    if any(k in text for k in ["vlog", "travel", "street", "interview", "irl", "live"]):
        camera += 15.0
    if any(k in text for k in ["3d", "simulation", "cgi", "render", "animated"]):
        animation += 12.0
    if any(k in text for k in ["reconstruction", "documentary", "deep dive"]):
        editing += 6.0

    total_risk = research + camera + animation + editing
    return float(min(100.0, max(0.0, total_risk)))

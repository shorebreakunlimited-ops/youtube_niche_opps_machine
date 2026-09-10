"""Copyright and intellectual property risk scoring."""

from typing import Dict, Optional


def compute_rights_risk(
    niche_text: str,
    custom_ratings: Optional[Dict[str, float]] = None,
) -> float:
    """Compute Rights Risk Score in [0, 100].
    
    Rights Safety = 100 - Rights Risk Score.
    Covers:
    - TV / movie footage dependence (0-30)
    - Pro sports footage dependence (0-30)
    - Commercial music dependence (0-20)
    - Celebrity likeness / privacy risk (0-20)
    """
    if custom_ratings:
        media = custom_ratings.get("tv_movie_footage", 5.0)
        sports = custom_ratings.get("sports_footage", 0.0)
        music = custom_ratings.get("commercial_music", 5.0)
        celebrity = custom_ratings.get("celebrity_privacy", 5.0)
        return float(min(100.0, max(0.0, media + sports + music + celebrity)))

    text = niche_text.lower()
    media = 5.0
    sports = 0.0
    music = 5.0
    celebrity = 5.0

    if any(k in text for k in ["movie", "film", "cinema", "tv show", "netflix", "anime"]):
        media += 20.0
    if any(k in text for k in ["nfl", "nba", "football", "soccer", "ufc", "boxing", "sports", "f1"]):
        sports += 25.0
    if any(k in text for k in ["music", "concert", "song", "album"]):
        music += 15.0
    if any(k in text for k in ["celebrity", "drama", "gossip", "paparazzi"]):
        celebrity += 15.0

    total_risk = media + sports + music + celebrity
    return float(min(100.0, max(0.0, total_risk)))

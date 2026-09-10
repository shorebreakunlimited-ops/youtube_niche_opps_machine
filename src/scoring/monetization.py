"""Commercial attractiveness scoring (monetization, sponsors, affiliate)."""

from typing import Dict, Optional


def compute_commercial_attractiveness(
    niche_text: str,
    custom_ratings: Optional[Dict[str, float]] = None,
) -> float:
    """Compute Commercial Attractiveness Score in [0, 100].
    
    Combines:
    - Ad rate / CPM index (40%)
    - Sponsor affinity (35%)
    - Affiliate viability (25%)
    """
    if custom_ratings:
        ad = custom_ratings.get("ad_rate_index", 50.0)
        sponsor = custom_ratings.get("sponsor_affinity", 50.0)
        affiliate = custom_ratings.get("affiliate_viability", 50.0)
        return float(min(100.0, max(0.0, 0.40 * ad + 0.35 * sponsor + 0.25 * affiliate)))

    text = niche_text.lower()
    ad = 50.0
    sponsor = 45.0
    affiliate = 40.0

    # Finance, tech, software, B2B have high CPMs and high sponsor interest
    if any(k in text for k in ["finance", "investing", "crypto", "business", "saas", "software"]):
        ad += 35.0
        sponsor += 35.0
        affiliate += 40.0
    elif any(k in text for k in ["engineering", "tech", "hardware", "productivity"]):
        ad += 20.0
        sponsor += 30.0
        affiliate += 25.0
    elif any(k in text for k in ["gaming", "animation", "memes", "comedy"]):
        ad -= 15.0
        affiliate -= 20.0

    score = 0.40 * ad + 0.35 * sponsor + 0.25 * affiliate
    return float(min(100.0, max(0.0, score)))

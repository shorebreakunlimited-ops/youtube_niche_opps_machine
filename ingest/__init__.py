"""Body-cam source triage and gated media ingest."""

from __future__ import annotations

REVIEW_STATUSES = (
    "new",
    "watch",
    "download",
    "reject",
    "episode_candidate",
)

DOWNLOADABLE_STATUSES = frozenset({"download", "episode_candidate"})

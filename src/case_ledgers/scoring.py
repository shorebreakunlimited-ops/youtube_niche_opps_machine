"""Reproducible candidate scoring and poison-signal rules."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

SCORE_WEIGHTS = {
    "novelty": 20,
    "evidence": 20,
    "decision_chain": 15,
    "aftermath": 15,
    "packaging": 15,
    "production_fit": 10,
    "safety": 5,
}

SCORE_FIELDS = tuple(SCORE_WEIGHTS.keys())

POISON_FIELDS = (
    "poison_five_plus_over_500k",
    "poison_covered_by_major_creator",
    "poison_name_famous",
    "poison_heavily_clipped",
    "poison_no_new_update",
    "poison_heavily_politicized",
    "poison_needs_psych_claims",
    "poison_poor_footage",
)

STRONG_SOURCE_TYPES = (
    "bodycam_raw",
    "court_police_record",
    "independent_reporting",
    "legal_outcome",
)


class LedgerValidationError(ValueError):
    """Raised when ledger CSV rows fail validation."""


def _get(row: Any, key: str, default: Any = None) -> Any:
    if isinstance(row, Mapping):
        return row.get(key, default)
    return getattr(row, key, default)


def _as_int_0_10(value: Any, field: str) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError) as exc:
        raise LedgerValidationError(f"{field} must be an integer 0-10, got {value!r}") from exc
    if n < 0 or n > 10:
        raise LedgerValidationError(f"{field} must be an integer 0-10, got {n}")
    return n


def candidate_score(row: Any) -> int:
    """Weighted score on a 0-100 scale from 0-10 axis fields."""
    total_weight = sum(SCORE_WEIGHTS.values())
    weighted = 0.0
    for field, weight in SCORE_WEIGHTS.items():
        weighted += _as_int_0_10(_get(row, field), field) * weight
    return int(round((weighted / (10 * total_weight)) * 100))


compute_candidate_score = candidate_score


def count_poison_signals(row: Any) -> int:
    """Count structured poison-signal fields that are truthy."""
    return sum(1 for field in POISON_FIELDS if bool(_get(row, field, False)))


def verdict_from_score(score: int, poison_count: int = 0) -> str:
    """Map score + poison count to verdict. 2+ poison signals force avoid."""
    if poison_count >= 2:
        return "avoid"
    if score >= 75:
        return "strong"
    if score >= 60:
        return "maybe"
    return "avoid"


def required_source_types_present(source_types: Iterable[str]) -> bool:
    present = {str(t).strip().lower() for t in source_types}
    return all(required in present for required in STRONG_SOURCE_TYPES)


def youtube_is_verified(row: Any) -> bool:
    """True only when YouTube metrics were pulled from a real data source."""
    if str(_get(row, "data_source", "")).strip().lower() in {"", "unknown", "none", "null"}:
        return False
    for field in ("videos_reviewed", "videos_over_500k"):
        value = _get(row, field)
        if value is None or str(value).strip().lower() in {"", "unknown", "null", "none"}:
            return False
    explicit = _get(row, "youtube_verified", None)
    if explicit is not None and str(explicit).strip() != "":
        return str(explicit).strip().lower() in {"1", "true", "yes", "y"}
    return True


def assert_score_and_verdict_match(row: Any) -> None:
    expected_score = candidate_score(row)
    expected_poison = count_poison_signals(row)
    expected_verdict = verdict_from_score(expected_score, expected_poison)

    stored_score = int(_get(row, "candidate_score"))
    stored_poison = int(_get(row, "poison_signal_count"))
    stored_verdict = str(_get(row, "verdict")).strip().lower()

    case_id = _get(row, "case_id", "<unknown>")
    if stored_score != expected_score:
        raise LedgerValidationError(
            f"{case_id}: candidate_score {stored_score} != calculated {expected_score}"
        )
    if stored_poison != expected_poison:
        raise LedgerValidationError(
            f"{case_id}: poison_signal_count {stored_poison} != calculated {expected_poison}"
        )
    if stored_verdict != expected_verdict:
        raise LedgerValidationError(
            f"{case_id}: verdict {stored_verdict!r} != calculated {expected_verdict!r}"
        )
    if expected_poison >= 2 and stored_verdict in {"strong", "maybe"}:
        raise LedgerValidationError(
            f"{case_id}: poison_signal_count={expected_poison} cannot keep verdict={stored_verdict}"
        )

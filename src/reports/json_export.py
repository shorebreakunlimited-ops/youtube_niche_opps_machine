"""JSON serialization for validation and discovery results."""

from dataclasses import asdict
import json
from typing import Any, Dict, List
from src.models import ValidationResult


def export_validation_to_json(result: ValidationResult, indent: int = 2) -> str:
    """Serialize a ValidationResult dataclass into a JSON string."""
    data = asdict(result)
    # Convert datetime objects to ISO strings
    if data.get("validated_at"):
        data["validated_at"] = str(data["validated_at"])
    return json.dumps(data, indent=indent, default=str)


def export_discovery_to_json(leaderboard: List[Dict[str, Any]], indent: int = 2) -> str:
    """Serialize discovery leaderboard into a clean JSON string."""
    clean_entries = []
    for entry in leaderboard:
        item = {k: v for k, v in entry.items() if k != "validation_result"}
        clean_entries.append(item)
    return json.dumps(clean_entries, indent=indent, default=str)

"""Load and filter config/sources.csv for safe-by-default ingest."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True)
class Source:
    source_name: str
    source_url: str
    source_type: str
    priority: int
    notes: str
    enabled: bool

    @property
    def is_video_list(self) -> bool:
        return self.source_type.strip().lower() in {"video_list", "videolist", "list"}

    @property
    def is_channel(self) -> bool:
        return self.source_type.strip().lower() == "channel"


def _parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def load_sources(path: Path | str) -> list[Source]:
    path = Path(path)
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        required = {
            "source_name",
            "source_url",
            "source_type",
            "priority",
            "notes",
            "enabled",
        }
        if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
            raise ValueError(
                f"sources.csv missing required columns {sorted(required)}; "
                f"got {reader.fieldnames}"
            )
        sources: list[Source] = []
        for row in reader:
            name = (row.get("source_name") or "").strip()
            if not name or name.startswith("#"):
                continue
            sources.append(
                Source(
                    source_name=name,
                    source_url=(row.get("source_url") or "").strip(),
                    source_type=(row.get("source_type") or "").strip(),
                    priority=int((row.get("priority") or "99").strip() or 99),
                    notes=(row.get("notes") or "").strip(),
                    enabled=_parse_bool(row.get("enabled") or ""),
                )
            )
    sources.sort(key=lambda s: (s.priority, s.source_name.lower()))
    return sources


def select_sources(
    sources: Sequence[Source],
    *,
    include_disabled: bool = False,
    source_names: Sequence[str] | None = None,
    enabled_only_default: bool = True,
) -> list[Source]:
    """
    Default: only enabled sources.
    Full channels require --include-disabled and an explicit --source name.
    """
    selected: Iterable[Source] = list(sources)

    if source_names:
        wanted = {n.strip().lower() for n in source_names if n.strip()}
        selected = [s for s in selected if s.source_name.lower() in wanted]
        missing = wanted - {s.source_name.lower() for s in selected}
        if missing:
            raise ValueError(f"Unknown --source name(s): {sorted(missing)}")

    selected = list(selected)

    if not include_disabled and enabled_only_default:
        disabled_requested = [s for s in selected if not s.enabled]
        selected = [s for s in selected if s.enabled]
        if not selected and disabled_requested:
            names = ", ".join(s.source_name for s in disabled_requested)
            raise ValueError(
                f"Source(s) disabled in config/sources.csv: {names}. "
                "Pass --include-disabled --source NAME for an intentional run, "
                "and set --max-index-videos for a small index test first."
            )

    if include_disabled and not source_names:
        raise ValueError(
            "--include-disabled requires explicit --source NAME "
            "(refusing to open every disabled full channel)."
        )

    if not selected:
        raise ValueError(
            "No sources selected. Enable a safe source in config/sources.csv "
            "or pass --include-disabled --source NAME for an intentional full-channel run."
        )

    if not include_disabled:
        disabled_channels = [s for s in selected if (not s.enabled) and s.is_channel]
        if disabled_channels:
            names = ", ".join(s.source_name for s in disabled_channels)
            raise ValueError(
                f"Refusing disabled channel source(s) without --include-disabled: {names}"
            )

    return selected

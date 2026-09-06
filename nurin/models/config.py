from __future__ import annotations

import dataclasses
from pathlib import Path

from nurin.models.target import Target

DEFAULT_UP_ACTIONS = ["echo up"]
DEFAULT_DOWN_ACTIONS = ["echo down"]


@dataclasses.dataclass(frozen=True)
class Config:
    down_actions: list[str] = dataclasses.field(
        default_factory=DEFAULT_DOWN_ACTIONS.copy,
    )
    down_check_interval: int = 5
    down_count: int = 3
    event_log: Path | None = None
    max_cycles: int | None = None
    targets: list[Target] = dataclasses.field(default_factory=list)
    regular_check_interval: int = 30
    reset_after_down_action: bool = False
    sleep_jitter: float = 0.1
    # Download-speed probing; off unless there is at least one URL to fetch.
    speed_test_urls: list[str] = dataclasses.field(default_factory=list)
    speed_test_interval: float = 300
    speed_test_timeout: float = 30
    speed_test_max_bytes: int = 10 * 1024 * 1024
    up_actions: list[str] = dataclasses.field(
        default_factory=DEFAULT_UP_ACTIONS.copy,
    )

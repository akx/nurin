from __future__ import annotations

import dataclasses

DEFAULT_UP_ACTIONS = ["echo up"]
DEFAULT_DOWN_ACTIONS = ["echo down"]


@dataclasses.dataclass(frozen=True)
class Config:
    down_actions: list[str] = dataclasses.field(
        default_factory=DEFAULT_DOWN_ACTIONS.copy,
    )
    down_check_interval: int = 5
    down_count: int = 3
    max_cycles: int | None = None
    ping_targets: list[str] = dataclasses.field(default_factory=list)
    regular_check_interval: int = 30
    reset_after_down_action: bool = False
    sleep_jitter: float = 0.1
    up_actions: list[str] = dataclasses.field(
        default_factory=DEFAULT_UP_ACTIONS.copy,
    )


@dataclasses.dataclass()
class State:
    down_check_counter: int = 0
    up_actions_primed: bool = False
    cycles: int = 0

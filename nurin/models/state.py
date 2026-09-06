from __future__ import annotations

import dataclasses

from nurin.models.outage import Outage


@dataclasses.dataclass()
class State:
    down_check_counter: int = 0
    up_actions_primed: bool = False
    cycles: int = 0
    outage: Outage | None = None
    # None means "due now", so the first eligible cycle takes a baseline sample.
    next_speed_test_epoch: float | None = None
    # URLs left in the current shuffle; refilled (and reshuffled) when empty.
    speed_test_pool: list[str] = dataclasses.field(default_factory=list)

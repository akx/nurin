from __future__ import annotations

import dataclasses

from nurin.models.outage import Outage


@dataclasses.dataclass()
class State:
    down_check_counter: int = 0
    up_actions_primed: bool = False
    cycles: int = 0
    outage: Outage | None = None

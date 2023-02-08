from __future__ import annotations

import dataclasses


@dataclasses.dataclass()
class State:
    down_check_counter: int = 0
    up_actions_primed: bool = False
    cycles: int = 0

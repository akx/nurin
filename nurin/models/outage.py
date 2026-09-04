from __future__ import annotations

import dataclasses

from nurin.models.target import Target


@dataclasses.dataclass()
class Outage:
    """
    An outage in progress: from the first failed check to the next successful one.

    Tracked separately from `down_check_counter` because that counter is zeroed
    mid-outage by --reset-after-down-action.
    """

    start_epoch: float
    target: Target
    last_failure_epoch: float
    failed_checks: int = 0
    down_actions: int = 0

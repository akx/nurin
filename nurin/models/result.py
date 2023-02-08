from __future__ import annotations

import dataclasses
from subprocess import CompletedProcess

from nurin.models.target import Target


@dataclasses.dataclass(frozen=True)
class CheckResult:
    target: Target
    timeout: float
    duration: float
    success: bool
    count: int = 1


@dataclasses.dataclass(frozen=True)
class CommandResult:
    proc: CompletedProcess | None
    stdout: str
    duration: float

    @property
    def timed_out(self) -> bool:
        return self.proc is None

    @property
    def success(self) -> bool:
        return self.proc is not None and self.proc.returncode == 0

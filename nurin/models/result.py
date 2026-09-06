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


@dataclasses.dataclass(frozen=True)
class SpeedResult:
    """
    One download-speed measurement; `truncated` says the sample was cut short at
    the byte or time cap rather than being a whole file.
    """

    url: str
    bytes: int
    duration: float
    success: bool
    ttfb: float | None = None
    error: str | None = None
    truncated: bool = False

    @property
    def bytes_per_second(self) -> float:
        if not self.duration:
            return 0.0
        return self.bytes / self.duration

    @property
    def mbit_per_second(self) -> float:
        return self.bytes_per_second * 8 / 1_000_000

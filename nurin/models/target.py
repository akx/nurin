from __future__ import annotations

import abc
import dataclasses
from typing import ClassVar


class Target(metaclass=abc.ABCMeta):
    kind: ClassVar[str]

    @property
    @abc.abstractmethod
    def value(self) -> str:
        """What is being checked; `kind:value` identifies the target in event logs."""


@dataclasses.dataclass(frozen=True)
class PingTarget(Target):
    kind: ClassVar[str] = "ping"
    host: str

    @property
    def value(self) -> str:
        return self.host


@dataclasses.dataclass(frozen=True)
class URLTarget(Target):
    kind: ClassVar[str] = "url"
    url: str

    @property
    def value(self) -> str:
        return self.url

from __future__ import annotations

import abc
import dataclasses


class Target(metaclass=abc.ABCMeta):  # noqa: B024
    pass


@dataclasses.dataclass(frozen=True)
class PingTarget(Target):
    host: str


@dataclasses.dataclass(frozen=True)
class URLTarget(Target):
    url: str

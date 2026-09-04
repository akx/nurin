from __future__ import annotations

import datetime
import json
import logging
from typing import Any

from nurin.__about__ import __version__
from nurin.models.config import Config
from nurin.models.outage import Outage
from nurin.models.target import Target

log = logging.getLogger(__name__)

# Event schema notes (kept compatible with distill_journal.py's output, so live
# logs and journal-distilled history can be concatenated and analyzed together):
#
#   {"type": "down",  ...}  connectivity lost, timestamped at the first failed check
#   {"type": "up",    ...}  connectivity back; a self-contained record of the outage
#   {"type": "start"/"stop"}  monitor lifecycle, so coverage gaps are derivable
#
# `gap` events are not written here: only an outside observer comparing a "stop"
# (or a truncated log) with the next "start" can tell how long we were away.


def format_ts(epoch: float) -> str:
    return datetime.datetime.fromtimestamp(
        epoch,
        tz=datetime.timezone.utc,
    ).isoformat(timespec="milliseconds")


def format_target(target: Target) -> str:
    return f"{target.kind}:{target.value}"


def stamp(epoch: float, prefix: str = "") -> dict[str, Any]:
    """
    How every event says when it happened: milliseconds in the text form, and the
    raw epoch alongside it for arithmetic. Both are part of the schema contract.
    """
    return {f"{prefix}ts": format_ts(epoch), f"{prefix}epoch": round(epoch, 6)}


def down_event(outage: Outage) -> dict[str, Any]:
    return {
        "type": "down",
        **stamp(outage.start_epoch),
        "target": format_target(outage.target),
        "start_estimated": False,
    }


def up_event(
    outage: Outage,
    end_epoch: float,
    reason: str,
    *,
    end_estimated: bool = False,
) -> dict[str, Any]:
    return {
        "type": "up",
        **stamp(end_epoch),
        **stamp(outage.start_epoch, "down_"),
        "duration_s": round(end_epoch - outage.start_epoch, 3),
        "failed_checks": outage.failed_checks,
        "down_actions": outage.down_actions,
        "target": format_target(outage.target),
        "reason": reason,
        # Constant for a live monitor -- it always witnesses its own outages
        # starting, and never restarts in the middle of one -- but written out
        # anyway so rows have the same shape as distilled ones.
        "start_estimated": False,
        "end_estimated": end_estimated,
        "spans_restart": False,
    }


def start_event(config: Config, epoch: float) -> dict[str, Any]:
    return {
        "type": "start",
        **stamp(epoch),
        "version": __version__,
        "targets": [format_target(target) for target in config.targets],
    }


def stop_event(epoch: float, reason: str) -> dict[str, Any]:
    return {
        "type": "stop",
        **stamp(epoch),
        "reason": reason,
    }


def write_event(config: Config, event: dict[str, Any]) -> None:
    """
    Append one event to the configured event log (if any).
    """
    if not config.event_log:
        return
    try:
        with config.event_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except OSError as e:
        # A full disk or a bad path must not take the monitor down.
        log.error("Unable to write event to %s: %s", config.event_log, e)

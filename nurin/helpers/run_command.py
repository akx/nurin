from __future__ import annotations

import logging
import shlex
import subprocess
import time

from nurin.models.result import CommandResult

log = logging.getLogger(__name__)


def run_command(
    command: str | list[str],
    *,
    timeout: float,
) -> CommandResult:
    """
    Run a command, record the duration, and return the output.
    """
    command_str = shlex.join(command)
    log.debug("Running %s", command_str)
    t0 = time.time()
    try:
        proc = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as te:
        t1 = time.time()
        log.warning("%s: Timed out; output: %s", command_str, te.stdout)
        return CommandResult(
            duration=t1 - t0,
            proc=None,
            stdout=(te.stdout or b"").decode("utf-8", errors="replace"),
        )
    t1 = time.time()
    duration = t1 - t0
    return CommandResult(
        duration=duration,
        proc=proc,
        stdout=(proc.stdout or b"").decode("utf-8", errors="replace"),
    )

import dataclasses
import logging
import shlex
import subprocess
import sys
import time

log = logging.getLogger(__name__)


@dataclasses.dataclass
class PingResult:
    target: str
    count: int
    packet_timeout: float
    duration: float
    success: bool


def ping(
    ping_target: str, *, packet_timeout: float = 0.5, count: int = 2
) -> PingResult:
    if sys.platform == "win32":
        ping_cmd = [
            "ping",
            "/n",
            str(count),
            # TODO: implement timeout?
            ping_target,
        ]
    elif sys.platform == "linux":
        ping_cmd = [
            "ping",
            "-c",
            str(count),
            "-W",
            str(
                packet_timeout
            ),  # Time to wait for a response, in seconds. Real number allowed with dot...
            ping_target,
        ]
    elif sys.platform == "darwin":
        ping_cmd = [
            "ping",
            "-c",
            str(count),
            "-W",
            str(
                packet_timeout * 1000
            ),  # "Time in milliseconds to wait for a reply for each packet sent."
            ping_target,
        ]
    else:
        raise NotImplementedError(f"Unsupported platform: {sys.platform}")
    log.debug("Running %s", shlex.join(ping_cmd))
    t0 = time.time()
    try:
        proc = subprocess.run(
            ping_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            errors="replace",
            timeout=packet_timeout * (count + 2),
        )
    except subprocess.TimeoutExpired as te:
        t1 = time.time()
        success = False
        log.warning("Ping timed out; output: %s", te.stdout)
    else:
        t1 = time.time()
        success = proc.returncode == 0
        if not success:
            log.warning("Ping failed; output: %s", proc.stdout)
        else:
            log.debug("Pinging %s succeeded", ping_target)
    return PingResult(
        count=count,
        duration=t1 - t0,
        packet_timeout=packet_timeout,
        success=success,
        target=ping_target,
    )

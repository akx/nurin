import logging
import sys

from nurin.models.result import CheckResult
from nurin.models.target import PingTarget
from nurin.helpers.run_command import run_command

log = logging.getLogger(__name__)


def ping(
    ping_target: PingTarget,
    *,
    packet_timeout: float = 0.5,
    count: int = 2,
) -> CheckResult:
    host = ping_target.host
    if sys.platform == "win32":
        ping_cmd = [
            "ping",
            "/n",
            str(count),
            # TODO: implement timeout?
            host,
        ]
    elif sys.platform == "linux":
        ping_cmd = [
            "ping",
            "-c",
            str(count),
            "-W",
            # "Time to wait for a response, in seconds. Real number allowed with dot..."
            str(packet_timeout),
            host,
        ]
    elif sys.platform == "darwin":
        ping_cmd = [
            "ping",
            "-c",
            str(count),
            "-W",
            # "Time in milliseconds to wait for a reply for each packet sent."
            str(packet_timeout * 1000),
            host,
        ]
    else:
        raise NotImplementedError(f"Unsupported platform: {sys.platform}")
    timeout = packet_timeout * (count + 2)
    res = run_command(ping_cmd, timeout=timeout)
    if res.timed_out:
        log.warning("Ping timed out")
    elif not res.success:
        log.warning("Ping failed; output: %s", res.stdout)
    else:
        log.debug("Pinging %s succeeded", host)
    return CheckResult(
        count=count,
        duration=res.duration,
        success=res.success,
        target=ping_target,
        timeout=packet_timeout,
    )

import logging
import os
import shutil

from nurin.models.result import CheckResult
from nurin.models.target import URLTarget
from nurin.helpers.run_command import run_command

wget = shutil.which("wget")
curl = shutil.which("curl")

log = logging.getLogger(__name__)


def check_url(url_target: URLTarget, timeout: float = 10) -> CheckResult:
    if wget:
        cmd = [wget, "-q", "-O", os.devnull, url_target.url]
    elif curl:
        cmd = [curl, "-s", "-o", os.devnull, url_target.url]
    else:
        raise NotImplementedError("Neither wget nor curl found")
    res = run_command(cmd, timeout=timeout)
    if res.timed_out:
        log.warning("URL fetch timed out")
    elif not res.success:
        log.warning("URL fetch failed; output: %s", res.stdout)
    else:
        log.debug("Fetching %s succeeded", url_target.url)
    return CheckResult(
        count=1,
        duration=res.duration,
        success=res.success,
        target=url_target,
        timeout=timeout,
    )

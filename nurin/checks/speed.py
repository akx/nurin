from __future__ import annotations

import http.client
import logging
import time
import urllib.error
import urllib.request

from nurin.__about__ import __version__
from nurin.models.result import SpeedResult

log = logging.getLogger(__name__)

CHUNK_SIZE = 65536


def measure_download_speed(
    url: str,
    *,
    timeout: float = 30,
    max_bytes: int = 0,
) -> SpeedResult:
    """
    Download `url` and measure how fast it came in.

    The download is cut short once `max_bytes` have arrived or `timeout` seconds
    have elapsed, whichever comes first -- a capped sample is exactly what we
    want, and it keeps a huge file (or a trickle that never ends) from stalling
    the monitor. `timeout` doubles as the socket timeout, so a connection that
    goes quiet mid-transfer fails rather than hanging.
    """
    t0 = time.monotonic()
    downloaded = 0
    ttfb: float | None = None
    truncated = False
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": f"nurin/{__version__}",
            # Ask for the wire, not for whatever a proxy has lying around.
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            while True:
                chunk = response.read(CHUNK_SIZE)
                if not chunk:
                    break
                if ttfb is None:
                    ttfb = time.monotonic() - t0
                downloaded += len(chunk)
                if max_bytes and downloaded >= max_bytes:
                    truncated = True
                    break
                if time.monotonic() - t0 >= timeout:
                    truncated = True
                    break
    except (OSError, http.client.HTTPException, ValueError) as e:
        duration = time.monotonic() - t0
        log.warning("Speed test %s failed after %.2f s: %s", url, duration, e)
        return SpeedResult(
            url=url,
            bytes=downloaded,
            duration=duration,
            ttfb=ttfb,
            success=False,
            error=f"{type(e).__name__}: {e}",
        )
    duration = time.monotonic() - t0
    result = SpeedResult(
        url=url,
        bytes=downloaded,
        duration=duration,
        ttfb=ttfb,
        success=True,
        truncated=truncated,
    )
    log.info(
        "Speed test %s: %.2f Mbit/s (%d bytes in %.2f s%s%s)",
        url,
        result.mbit_per_second,
        result.bytes,
        result.duration,
        f", ttfb {ttfb:.3f} s" if ttfb is not None else "",
        ", truncated" if truncated else "",
    )
    return result

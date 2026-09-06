from __future__ import annotations

import logging
from pathlib import Path

import click

from nurin.__about__ import __version__
from nurin.models.config import Config
from nurin.models.target import PingTarget, URLTarget

log = logging.getLogger(__name__)


@click.command(help="start tracking connectivity")
@click.option(
    "-p",
    "--ping-target",
    "ping_targets",
    multiple=True,
    default=[],
    help="Ping target; can be specified multiple times, and a random one is chosen each time.",
    metavar="IP/HOST",
)
@click.option(
    "-u",
    "--url-target",
    "url_targets",
    multiple=True,
    default=[],
    help="URL target; can be specified multiple times, and a random one is chosen each time.",
    metavar="URL",
)
@click.option(
    "-rci",
    "--regular-check-interval",
    default=30,
    type=float,
    help="Regular check interval (seconds)",
    metavar="SECONDS",
)
@click.option(
    "-dci",
    "--down-check-interval",
    default=5,
    type=float,
    help="Check interval when down counter > 0 (seconds)",
    metavar="SECONDS",
)
@click.option(
    "--sleep-jitter",
    default=0.1,
    type=float,
    help="Sleep jitter (multiplier, +/-)",
    metavar="MULTIPLIER",
)
@click.option(
    "--down-count",
    default=3,
    type=int,
    help="Number of consecutive failed pings before running down actions",
    metavar="NUM",
)
@click.option(
    "-da",
    "--down-action",
    "down_actions",
    multiple=True,
    default=["echo down"],
    help=(
        "Shell command to run when down counter > down-count; can be specified multiple times. "
        "All commands are run even if one fails."
    ),
)
@click.option(
    "--reset-after-down-action/--no-reset-after-down-action",
    default=False,
    help="Reset down count after running down actions?",
)
@click.option(
    "-ua",
    "--up-action",
    "up_actions",
    multiple=True,
    default=["echo up again"],
    help=(
        "Shell command to run when up again after down actions have been run; can be specified multiple times. "
        "All commands are run even if one fails."
    ),
)
@click.option(
    "--max-cycles",
    default=None,
    type=int,
    help="Maximum number of cycles to run.",
)
@click.option(
    "-s",
    "--speed-test-url",
    "speed_test_urls",
    multiple=True,
    default=[],
    help=(
        "Periodically download this URL and log the download speed; can be specified multiple times, "
        "and the URLs are used in shuffled order. Speed testing is off unless at least one is given."
    ),
    metavar="URL",
)
@click.option(
    "-sti",
    "--speed-test-interval",
    default=300,
    type=float,
    help="How often to run a speed test (seconds); a floor, since tests only happen between checks.",
    metavar="SECONDS",
)
@click.option(
    "--speed-test-timeout",
    default=30,
    type=float,
    help="Give up on (or cut short) a speed test download after this long (seconds).",
    metavar="SECONDS",
)
@click.option(
    "--speed-test-max-bytes",
    default=10 * 1024 * 1024,
    type=int,
    help="Stop a speed test download after this many bytes (0 for no limit).",
    metavar="BYTES",
)
@click.option(
    "-e",
    "--event-log",
    default=None,
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    help="Append connectivity events (down/up/start/stop, and speed samples) to this file as JSONL.",
    metavar="FILE",
)
def run(
    *,
    down_actions: tuple[str, ...],
    down_check_interval: int,
    down_count: int,
    event_log: Path | None,
    ping_targets: tuple[str, ...],
    url_targets: tuple[str, ...],
    regular_check_interval: int,
    reset_after_down_action: bool,
    sleep_jitter: float,
    speed_test_urls: tuple[str, ...],
    speed_test_interval: float,
    speed_test_timeout: float,
    speed_test_max_bytes: int,
    up_actions: tuple[str, ...],
    max_cycles: int | None,
) -> None:
    targets = [
        *(PingTarget(host=host) for host in ping_targets),
        *(URLTarget(url=url) for url in url_targets),
    ]
    if not targets:
        raise click.UsageError("No targets specified.")
    config = Config(
        down_actions=list(down_actions),
        down_check_interval=down_check_interval,
        down_count=down_count,
        event_log=event_log,
        targets=targets,
        regular_check_interval=regular_check_interval,
        reset_after_down_action=reset_after_down_action,
        sleep_jitter=sleep_jitter,
        speed_test_urls=list(speed_test_urls),
        speed_test_interval=speed_test_interval,
        speed_test_timeout=speed_test_timeout,
        speed_test_max_bytes=speed_test_max_bytes,
        up_actions=list(up_actions),
        max_cycles=max_cycles,
    )
    log.info("Hello, this is nurin %s. My configuration is %s", __version__, config)

    from nurin.run import run

    run(config)

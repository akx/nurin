from __future__ import annotations

import logging

import click

from nurin.models.config import Config
from nurin.models.target import PingTarget, URLTarget
from nurin.__about__ import __version__

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
    "--max-cycles", default=None, type=int, help="Maximum number of cycles to run.",
)
def run(
    *,
    down_actions: tuple[str, ...],
    down_check_interval: int,
    down_count: int,
    ping_targets: tuple[str, ...],
    url_targets: tuple[str, ...],
    regular_check_interval: int,
    reset_after_down_action: bool,
    sleep_jitter: float,
    up_actions: tuple[str, ...],
    max_cycles: int | None,
):
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
        targets=targets,
        regular_check_interval=regular_check_interval,
        reset_after_down_action=reset_after_down_action,
        sleep_jitter=sleep_jitter,
        up_actions=list(up_actions),
        max_cycles=max_cycles,
    )
    logging.info("Hello, this is nurin %s. My configuration is %s", __version__, config)

    from nurin.run import run
    run(config)

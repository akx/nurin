from __future__ import annotations

import logging

import click

from nurin.models import Config
from nurin.run import run
from nurin.__about__ import __version__

log = logging.getLogger(__name__)


@click.command(
    help="Network Up/Down monitor.\nTaasko se netti on nurin? Nurin se on!",
)
@click.option(
    "-p",
    "--ping-target",
    "ping_targets",
    multiple=True,
    default=["8.8.8.8"],
    help="Ping target; can be specified multiple times, and a random one is chosen each time.",
    metavar="IP/HOST",
)
@click.option(
    "--regular-check-interval",
    default=30,
    type=float,
    help="Regular check interval (seconds)",
    metavar="SECONDS",
)
@click.option(
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
    "--max-cycles", default=None, type=int, help="Maximum number of cycles to run."
)
@click.option("--debug", is_flag=True, help="Enable debug logging")
def cli(
    *,
    debug: bool,
    down_actions: tuple[str, ...],
    down_check_interval: int,
    down_count: int,
    ping_targets: tuple[str, ...],
    regular_check_interval: int,
    reset_after_down_action: bool,
    sleep_jitter: float,
    up_actions: tuple[str, ...],
    max_cycles: int | None,
) -> None:
    logging.basicConfig(
        level=(logging.DEBUG if debug else logging.INFO),
        format="%(asctime)s %(levelname)s: %(message)s",
    )
    config = Config(
        down_actions=list(down_actions),
        down_check_interval=down_check_interval,
        down_count=down_count,
        ping_targets=list(ping_targets),
        regular_check_interval=regular_check_interval,
        reset_after_down_action=reset_after_down_action,
        sleep_jitter=sleep_jitter,
        up_actions=list(up_actions),
        max_cycles=max_cycles,
    )
    logging.info("Hello, this is nurin %s. My configuration is %s", __version__, config)
    run(config)

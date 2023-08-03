from __future__ import annotations

import logging

import click

from nurin.cli.run import run


@click.group(
    help="Network Up/Down monitor.\nTaasko se netti on nurin? Nurin se on!",
)
@click.option("--debug", is_flag=True, help="Enable debug logging")
def cli(
    *,
    debug: bool,
) -> None:
    logging.basicConfig(
        level=(logging.DEBUG if debug else logging.INFO),
        format="%(asctime)s %(levelname)s: %(message)s",
    )


cli.add_command(run)

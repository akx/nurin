import logging
import random
import subprocess
from typing import Callable

from nurin.helpers import jittered_sleep
from nurin.models import Config, State
from nurin.network import ping

log = logging.getLogger(__name__)


def default_keep_checking(config: Config, state: State) -> bool:
    if not config.max_cycles:
        return True
    return state.cycles < config.max_cycles


def run(
    config: Config,
    keep_checking: Callable[[Config, State], bool] = default_keep_checking,
) -> None:
    state = State()
    try:
        while keep_checking(config, state):
            check_success = run_check_cycle(config, state)
            state.cycles += 1
            if check_success and state.up_actions_primed:
                state.up_actions_primed = False
                log.info("Up again! Running up actions.")
                run_action_list(config.up_actions)
            if state.down_check_counter >= config.down_count:
                log.info(
                    "Counter reached %d/%d, running down actions",
                    state.down_check_counter,
                    config.down_count,
                )
                run_action_list(config.down_actions)
                if config.reset_after_down_action:
                    state.down_check_counter = 0
                state.up_actions_primed = True
    except KeyboardInterrupt:
        log.info("Interrupted by user, exiting")
    log.info("Exiting after %d cycles", state.cycles)


def run_check_cycle(config: Config, state: State) -> bool:
    check_interval = (
        config.down_check_interval
        if state.down_check_counter > 0
        else config.regular_check_interval
    )
    jittered_sleep(check_interval, config.sleep_jitter)
    result = ping(random.choice(config.ping_targets))
    if not result.success:
        state.down_check_counter += 1
        log.info(
            "Ping failed to %s, counter %d",
            result.target,
            state.down_check_counter,
        )
    else:
        if state.down_check_counter:
            log.info(
                "Ping succeeded to %s; counter had been %d",
                result.target,
                state.down_check_counter,
            )
        state.down_check_counter = 0
    return result.success


def run_action_list(action_list: list[str]) -> None:
    for i, action in enumerate(action_list, 1):
        log.info(
            "Running action %d/%d: %s",
            i,
            len(action_list),
            action,
        )
        try:
            subprocess.run(action, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            log.error("Action failed with code %d", e.returncode)

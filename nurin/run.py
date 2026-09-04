import logging
import random
import subprocess
from collections.abc import Callable

from nurin.checks.ping import ping
from nurin.checks.url import check_url
from nurin.event_log import down_event, start_event, stop_event, up_event, write_event
from nurin.helpers import jittered_sleep, now_epoch
from nurin.models.config import Config
from nurin.models.outage import Outage
from nurin.models.state import State
from nurin.models.target import PingTarget, URLTarget

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
    write_event(config, start_event(config, now_epoch()))
    stop_reason = "done"
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
                if state.outage:
                    state.outage.down_actions += 1
                run_action_list(config.down_actions)
                if config.reset_after_down_action:
                    state.down_check_counter = 0
                state.up_actions_primed = True
    except KeyboardInterrupt:
        log.info("Interrupted by user, exiting")
        stop_reason = "interrupted"
    if state.outage:
        # Leaving mid-outage: all we know is that things were still broken at
        # the last failed check, so that is where the outage has to end.
        close_outage(config, state, state.outage.last_failure_epoch, "monitor_gone", end_estimated=True)
    write_event(config, stop_event(now_epoch(), stop_reason))
    log.info("Exiting after %d cycles", state.cycles)


def close_outage(
    config: Config,
    state: State,
    end_epoch: float,
    reason: str,
    *,
    end_estimated: bool = False,
) -> None:
    if state.outage:
        write_event(config, up_event(state.outage, end_epoch, reason, end_estimated=end_estimated))
        state.outage = None


def run_check_cycle(config: Config, state: State) -> bool:
    check_interval = config.down_check_interval if state.down_check_counter > 0 else config.regular_check_interval
    jittered_sleep(check_interval, config.sleep_jitter)
    target = random.choice(config.targets)
    if isinstance(target, PingTarget):
        result = ping(target)
    elif isinstance(target, URLTarget):
        result = check_url(target)
    else:
        raise NotImplementedError(f"Unknown target type: {target}")
    now = now_epoch()
    if not result.success:
        state.down_check_counter += 1
        outage = state.outage
        if outage is None:
            # First failed check: this is when connectivity was lost, whether or
            # not we end up failing often enough to run the down actions.
            outage = state.outage = Outage(start_epoch=now, target=target, last_failure_epoch=now)
            write_event(config, down_event(outage))
        outage.failed_checks += 1
        outage.last_failure_epoch = now
        log.info(
            "Target failed: %s, counter %d",
            target,
            state.down_check_counter,
        )
    else:
        close_outage(config, state, now, "recovered")
        if state.down_check_counter:
            log.info(
                "Success: %s; counter had been %d",
                target,
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

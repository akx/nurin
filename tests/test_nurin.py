import itertools
import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from nurin.__about__ import __version__
from nurin.cli import cli
from nurin.models.config import Config
from nurin.models.result import CheckResult
from nurin.models.target import URLTarget
from nurin.run import run


def test_ping(runner: CliRunner, run_spy) -> None:
    result = runner.invoke(
        cli,
        [
            "run",
            "--max-cycles=1",
            "--regular-check-interval=0",
            "--ping-target=localhost",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert run_spy.call_count == 1  # ping!


def test_http(runner: CliRunner, http_server, run_spy) -> None:
    _hs, port = http_server
    result = runner.invoke(
        cli,
        [
            "run",
            "--max-cycles=1",
            "--regular-check-interval=0",
            f"--url-target=http://localhost:{port}",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert run_spy.call_count == 1  # wget!


TARGET = URLTarget(url="http://nope.invalid")


def _run_with_event_log(
    monkeypatch: pytest.MonkeyPatch,
    event_log: Path,
    successes: list[bool],
    **config_kwargs,
) -> list[dict]:
    """Run one check per entry in `successes`, return the events that were logged."""
    results = iter(successes)

    def fake_check_url(url_target, timeout=10):
        return CheckResult(
            target=url_target,
            timeout=timeout,
            duration=0.125,
            success=next(results),
        )

    clock = itertools.count(1_000_000, 10)  # start, one per cycle, stop
    monkeypatch.setattr("nurin.run.check_url", fake_check_url)
    monkeypatch.setattr("nurin.run.now_epoch", lambda: float(next(clock)))
    run(
        Config(
            down_actions=[],
            down_check_interval=0,
            event_log=event_log,
            max_cycles=len(successes),
            regular_check_interval=0,
            targets=[TARGET],
            up_actions=[],
            **config_kwargs,
        ),
    )
    return [json.loads(line) for line in event_log.read_text().splitlines()]


def test_event_log_blip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # A single failed check never reaches down-count, but is still an outage.
    events = _run_with_event_log(
        monkeypatch,
        tmp_path / "events.jsonl",
        [False, True],
        down_count=3,
    )
    expected_start = {
        "type": "start",
        "ts": "1970-01-12T13:46:40.000+00:00",
        "epoch": 1000000.0,
        "version": __version__,
        "targets": ["url:http://nope.invalid"],
    }
    expected_down = {
        "type": "down",
        "ts": "1970-01-12T13:46:50.000+00:00",
        "epoch": 1000010.0,
        "target": "url:http://nope.invalid",
        "start_estimated": False,
    }
    expected_up = {
        "type": "up",
        "ts": "1970-01-12T13:47:00.000+00:00",
        "epoch": 1000020.0,
        "down_ts": "1970-01-12T13:46:50.000+00:00",
        "down_epoch": 1000010.0,
        "duration_s": 10.0,
        "failed_checks": 1,
        "down_actions": 0,
        "target": "url:http://nope.invalid",
        "reason": "recovered",
        "start_estimated": False,
        "end_estimated": False,
        "spans_restart": False,
    }
    assert [e["type"] for e in events] == ["start", "down", "up", "stop"]
    assert events[0] == expected_start
    assert events[1] == expected_down
    assert events[2] == expected_up
    assert events[3]["reason"] == "done"
    # The keys come out in the same order distill_journal.py writes them, so live
    # and distilled logs read identically.
    assert [list(e) for e in events[1:3]] == [list(expected_down), list(expected_up)]


def test_event_log_counts_down_actions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Six failures at down-count 3 with the counter resetting: two down actions,
    # and one down/up pair for the whole outage.
    events = _run_with_event_log(
        monkeypatch,
        tmp_path / "events.jsonl",
        [False] * 6 + [True],
        down_count=3,
        reset_after_down_action=True,
    )
    assert [e["type"] for e in events] == ["start", "down", "up", "stop"]
    up = events[2]
    assert up["failed_checks"] == 6
    assert up["down_actions"] == 2  # matches failed_checks // down_count
    assert up["duration_s"] == 60.0
    assert up["reason"] == "recovered"


def test_event_log_exit_mid_outage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = _run_with_event_log(
        monkeypatch,
        tmp_path / "events.jsonl",
        [False, False],
        down_count=3,
    )
    assert [e["type"] for e in events] == ["start", "down", "up", "stop"]
    up = events[2]
    assert up["reason"] == "monitor_gone"
    assert up["end_estimated"] is True
    # Ends at the last failed check, not at our own shutdown.
    assert up["epoch"] == 1000020.0
    assert up["duration_s"] == 10.0
    assert events[3]["epoch"] == 1000030.0


def test_event_log_appends(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    event_log = tmp_path / "events.jsonl"
    first = _run_with_event_log(monkeypatch, event_log, [True], down_count=3)
    both = _run_with_event_log(monkeypatch, event_log, [True], down_count=3)
    assert [e["type"] for e in first] == ["start", "stop"]
    assert [e["type"] for e in both] == ["start", "stop", "start", "stop"]

import itertools
import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from nurin.__about__ import __version__
from nurin.checks.speed import measure_download_speed
from nurin.cli import cli
from nurin.models.config import Config
from nurin.models.result import CheckResult, SpeedResult
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


def _fake_speed_result(url: str, **kwargs) -> SpeedResult:
    return SpeedResult(
        url=url,
        bytes=1_000_000,
        duration=2.0,
        ttfb=0.25,
        success=True,
        truncated=True,
        **kwargs,
    )


def _run_with_speed_tests(
    monkeypatch: pytest.MonkeyPatch,
    event_log: Path,
    cycles: int,
    **config_kwargs,
) -> tuple[list[dict], list[str]]:
    """Run `cycles` successful checks, return the events logged and the URLs fetched."""
    fetched: list[str] = []

    def fake_measure(url, *, timeout, max_bytes):
        fetched.append(url)
        return _fake_speed_result(url)

    def fake_check_url(url_target, timeout=10):
        return CheckResult(target=url_target, timeout=timeout, duration=0.125, success=True)

    clock = itertools.count(1_000_000, 10)
    monkeypatch.setattr("nurin.run.check_url", fake_check_url)
    monkeypatch.setattr("nurin.run.measure_download_speed", fake_measure)
    monkeypatch.setattr("nurin.run.now_epoch", lambda: float(next(clock)))
    run(
        Config(
            down_actions=[],
            down_check_interval=0,
            event_log=event_log,
            max_cycles=cycles,
            regular_check_interval=0,
            targets=[TARGET],
            up_actions=[],
            **config_kwargs,
        ),
    )
    events = [json.loads(line) for line in event_log.read_text().splitlines()]
    return events, fetched


def test_speed_test_off_without_urls(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    events, fetched = _run_with_speed_tests(monkeypatch, tmp_path / "events.jsonl", 2)
    assert not fetched
    assert [e["type"] for e in events] == ["start", "stop"]


def test_speed_test_event(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    events, fetched = _run_with_speed_tests(
        monkeypatch,
        tmp_path / "events.jsonl",
        1,
        speed_test_urls=["http://speed.invalid/file"],
        speed_test_interval=0,
    )
    assert fetched == ["http://speed.invalid/file"]
    assert [e["type"] for e in events] == ["start", "speed", "stop"]
    assert events[1] == {
        "type": "speed",
        "ts": "1970-01-12T13:47:00.000+00:00",
        "epoch": 1000020.0,
        "url": "http://speed.invalid/file",
        "success": True,
        "bytes": 1_000_000,
        "duration_s": 2.0,
        "ttfb_s": 0.25,
        "bytes_per_second": 500000.0,
        "mbit_per_second": 4.0,
        "truncated": True,
        "error": None,
    }


def test_speed_test_interval_is_respected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The fake clock ticks 10 s per epoch call, so an hour-long interval only
    # leaves room for the baseline sample.
    events, fetched = _run_with_speed_tests(
        monkeypatch,
        tmp_path / "events.jsonl",
        4,
        speed_test_urls=["http://speed.invalid/file"],
        speed_test_interval=3600,
    )
    assert len(fetched) == 1  # only the baseline sample is due
    assert [e["type"] for e in events] == ["start", "speed", "stop"]


def test_speed_test_urls_are_shuffled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    urls = [f"http://speed.invalid/{i}" for i in range(4)]
    _events, fetched = _run_with_speed_tests(
        monkeypatch,
        tmp_path / "events.jsonl",
        8,
        speed_test_urls=urls,
        speed_test_interval=0,
    )
    # Every URL is used equally often: two full shuffles of the four URLs.
    assert len(fetched) == 8
    assert sorted(fetched[:4]) == urls
    assert sorted(fetched[4:]) == urls


def test_speed_test_skipped_during_outage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    results = iter([True, False, False, True])

    def fake_check_url(url_target, timeout=10):
        return CheckResult(target=url_target, timeout=timeout, duration=0.125, success=next(results))

    fetched: list[str] = []

    def fake_measure(url, *, timeout, max_bytes):
        fetched.append(url)
        return _fake_speed_result(url)

    clock = itertools.count(1_000_000, 10)
    monkeypatch.setattr("nurin.run.check_url", fake_check_url)
    monkeypatch.setattr("nurin.run.measure_download_speed", fake_measure)
    monkeypatch.setattr("nurin.run.now_epoch", lambda: float(next(clock)))
    event_log = tmp_path / "events.jsonl"
    run(
        Config(
            down_actions=[],
            down_check_interval=0,
            down_count=99,
            event_log=event_log,
            max_cycles=4,
            regular_check_interval=0,
            targets=[TARGET],
            up_actions=[],
            speed_test_urls=["http://speed.invalid/file"],
            speed_test_interval=0,
        ),
    )
    # Cycles 2 and 3 are mid-outage, so only the two successful ones sample.
    assert len(fetched) == 2
    events = [json.loads(line) for line in event_log.read_text().splitlines()]
    assert [e["type"] for e in events] == ["start", "speed", "down", "up", "speed", "stop"]


def test_measure_download_speed(http_server, tmp_path: Path) -> None:
    _hs, port = http_server
    (tmp_path / "blob.bin").write_bytes(b"x" * 262144)
    result = measure_download_speed(f"http://localhost:{port}/blob.bin", timeout=10)
    assert result.success
    assert result.error is None
    assert result.bytes == 262144
    assert not result.truncated
    assert result.bytes_per_second > 0
    assert result.ttfb is not None


def test_measure_download_speed_truncates(http_server, tmp_path: Path) -> None:
    _hs, port = http_server
    (tmp_path / "blob.bin").write_bytes(b"x" * 262144)
    result = measure_download_speed(f"http://localhost:{port}/blob.bin", timeout=10, max_bytes=1024)
    assert result.success
    assert result.truncated
    assert 1024 <= result.bytes < 262144


def test_measure_download_speed_failure(http_server) -> None:
    _hs, port = http_server
    result = measure_download_speed(f"http://localhost:{port}/nope.bin", timeout=10)
    assert not result.success
    assert result.bytes == 0
    assert result.error and "HTTPError" in result.error


def test_speed_test_cli(runner: CliRunner, http_server, tmp_path: Path) -> None:
    _hs, port = http_server
    (tmp_path / "blob.bin").write_bytes(b"x" * 65536)
    event_log = tmp_path / "cli-events.jsonl"
    result = runner.invoke(
        cli,
        [
            "run",
            "--max-cycles=1",
            "--regular-check-interval=0",
            f"--url-target=http://localhost:{port}",
            f"--speed-test-url=http://localhost:{port}/blob.bin",
            "--speed-test-interval=0",
            f"--event-log={event_log}",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    events = [json.loads(line) for line in event_log.read_text().splitlines()]
    speed = next(e for e in events if e["type"] == "speed")
    assert speed["url"] == f"http://localhost:{port}/blob.bin"
    assert speed["success"] is True
    assert speed["bytes"] == 65536
    assert speed["mbit_per_second"] > 0

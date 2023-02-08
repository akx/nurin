from click.testing import CliRunner

from nurin.cli import cli


def test_ping(runner: CliRunner, run_spy) -> None:
    result = runner.invoke(
        cli,
        [
            "--max-cycles=1",
            "--regular-check-interval=0",
            "--ping-target=localhost",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert run_spy.call_count == 1  # ping!


def test_http(runner: CliRunner, http_server, run_spy) -> None:
    hs, port = http_server
    result = runner.invoke(
        cli,
        [
            "--max-cycles=1",
            "--regular-check-interval=0",
            f"--url-target=http://localhost:{port}",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert run_spy.call_count == 1  # wget!

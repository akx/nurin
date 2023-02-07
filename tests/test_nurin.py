from subprocess import run
from unittest.mock import patch

from click.testing import CliRunner

from nurin.cli import cli


def test_nurin() -> None:
    with patch("subprocess.run", wraps=run) as mock_run:
        runner = CliRunner()
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
        assert mock_run.call_count == 1  # ping!

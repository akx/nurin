import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest
from click.testing import CliRunner


@pytest.fixture(scope="session")
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def http_server(tmp_path: Path) -> Generator[tuple[subprocess.Popen, int], None, None]:
    http_server = None
    try:
        while True:  # find a free port
            port = random.randint(1024, 65535)
            http_server = subprocess.Popen(
                [sys.executable, "-m", "http.server", str(port)],
                cwd=tmp_path,
            )
            time.sleep(1)
            if http_server.poll() is None:  # still running, good
                yield (http_server, port)
                break
    finally:
        if http_server:
            http_server.terminate()


@pytest.fixture()
def run_spy() -> Generator[subprocess.Popen, None, None]:
    with patch("subprocess.run", wraps=subprocess.run) as run_spy:
        yield run_spy

import os
import socket
import subprocess
import time
from urllib.request import urlopen

import pytest
from fastapi.testclient import TestClient

# Ensure app import does not fail in test environments without a real key.
os.environ.setdefault("OPENAI_API_KEY", "test-key")

import main


@pytest.fixture
def client():
    with TestClient(main.create_app()) as test_client:
        yield test_client


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_healthcheck(url: str, timeout_seconds: float = 10.0) -> None:
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None

    while time.time() < deadline:
        try:
            with urlopen(url, timeout=1.0) as response:  # noqa: S310
                if response.status == 200:
                    return
        except Exception as exc:  # pragma: no cover - exercised in retries
            last_error = exc
        time.sleep(0.1)

    raise RuntimeError(f"Timed out waiting for test server healthcheck at {url}") from last_error


@pytest.fixture(scope="session")
def live_server_url():
    port = _find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env.setdefault("OPENAI_API_KEY", "test-key")

    server = subprocess.Popen(
        ["uv", "run", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(port)],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )

    try:
        _wait_for_healthcheck(f"{base_url}/health")
        yield base_url
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)

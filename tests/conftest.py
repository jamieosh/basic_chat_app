import os
import socket
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlopen

import pytest
from fastapi.testclient import TestClient

# Ensure app import does not fail in test environments without a real key.
os.environ.setdefault("OPENAI_API_KEY", "test-key")

import main
from utils.settings import RuntimeSettings


@dataclass(frozen=True)
class LiveServer:
    base_url: str
    database_path: Path


@pytest.fixture
def client(tmp_path):
    settings = RuntimeSettings(
        openai_api_key="test-key",
        openai_model="gpt-5-mini",
        openai_prompt_name="default",
        openai_temperature=1.0,
        openai_timeout_seconds=30.0,
        chat_database_path=tmp_path / "chat.db",
        cors_allowed_origins=["*"],
        cors_allow_credentials=False,
        cors_allowed_methods=["*"],
        cors_allowed_headers=["*"],
    )
    with TestClient(main.create_app(settings=settings)) as test_client:
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
def live_server():
    port = _find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env.setdefault("OPENAI_API_KEY", "test-key")
    with tempfile.TemporaryDirectory() as temp_dir:
        database_path = Path(temp_dir) / "chat.db"
        env["CHAT_DATABASE_PATH"] = os.path.join(temp_dir, "chat.db")
        server = subprocess.Popen(
            ["uv", "run", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(port)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )

        try:
            _wait_for_healthcheck(f"{base_url}/health")
            yield LiveServer(base_url=base_url, database_path=database_path)
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)


@pytest.fixture(scope="session")
def live_server_url(live_server):
    return live_server.base_url

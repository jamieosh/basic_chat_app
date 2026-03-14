import os

import pytest
from fastapi.testclient import TestClient

# Ensure app import does not fail in test environments without a real key.
os.environ.setdefault("OPENAI_API_KEY", "test-key")

import main


@pytest.fixture
def client():
    with TestClient(main.create_app()) as test_client:
        yield test_client

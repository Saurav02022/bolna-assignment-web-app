import os

# Pydantic settings read at import time; CallService requires non-empty IDs for /verify paths.
os.environ.setdefault("BOLNA_API_KEY", "pytest-nonempty-placeholder")
os.environ.setdefault("BOLNA_AGENT_ID", "pytest-nonempty-placeholder")

import pytest
from starlette.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client

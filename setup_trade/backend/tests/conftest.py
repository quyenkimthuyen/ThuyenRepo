from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.api.app import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

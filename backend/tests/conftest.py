from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings.config import Settings


@pytest.fixture(scope="session")
def mock_data_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "mock-data"


@pytest.fixture()
def client(mock_data_dir: Path) -> TestClient:
    settings = Settings(
        environment="test",
        mock_data_dir=mock_data_dir,
        cors_origins=("http://localhost",),
        demo_auth_enabled=True,
        ai_provider="fake",
        openai_model="unused",
        openai_base_url="https://api.openai.com/v1",
        openai_timeout_seconds=1.0,
        openai_api_key=None,
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def restricted_headers() -> dict[str, str]:
    return {
        "X-Demo-Role": "compliance",
        "X-Demo-Security-Classes": "public,internal,restricted",
        "X-Demo-Subject": "privacy-demo-user",
    }

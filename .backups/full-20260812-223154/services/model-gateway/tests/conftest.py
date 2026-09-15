from __future__ import annotations

from pathlib import Path

import pytest

from app.config import Settings


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    return Settings(
        app_environment="test",
        barmana_api_key="test-key",
        model_cache_path=tmp_path / "models-cache.json",
        usage_db_path=tmp_path / "usage.sqlite3",
        model_cache_ttl_seconds=300,
        max_retries=0,
        default_model="mistral-small-latest",
        fallback_models="fallback-a,fallback-b",
        max_fallback_attempts=3,
    )

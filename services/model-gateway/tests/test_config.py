from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_defaults_are_valid():
    settings = Settings(_env_file=None)

    assert settings.app_name
    assert settings.gateway_host
    assert settings.model_cache_path


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("app_name", "x" * 201),
        ("app_version", "x" * 65),
        ("gateway_host", "x" * 256),
        ("gateway_log_level", "x" * 33),
        ("barmana_models_path", "x" * 501),
        ("barmana_chat_path", "x" * 501),
        ("model_cache_path", "x" * 501),
        ("usage_db_path", "x" * 501),
    ],
)
def test_settings_reject_oversized_values(field: str, value: str):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field: value})

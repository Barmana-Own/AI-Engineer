from __future__ import annotations

import json

from app.config import Settings


def test_provider_profiles_parse_api_key_from_environment(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "secret-value")
    settings = Settings(
        provider_profiles_json=json.dumps(
            {
                "OpenRouter": {
                    "base_url": "https://openrouter.ai/api/v1",
                    "api_key_env": "OPENROUTER_API_KEY",
                    "default_model": "openai/gpt-4o-mini",
                    "fallback_models": "google/gemini-2.5-flash",
                }
            }
        )
    )

    profiles = settings.parsed_provider_profiles
    assert len(profiles) == 1
    assert profiles[0].name == "openrouter"
    assert profiles[0].configured is True
    assert profiles[0].api_key == "secret-value"
    assert settings.provider_configured is True

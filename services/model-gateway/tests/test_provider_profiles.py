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


def test_disabled_local_bridge_is_ignored_and_enabled_bridge_uses_local_key(monkeypatch):
    monkeypatch.setenv("CLIPROXYAPI_API_KEY", "local-secret")
    settings = Settings(
        local_bridge_profiles_json=json.dumps(
            {
                "codexproxy": {
                    "enabled": False,
                    "base_url": "http://127.0.0.1:8080/v1",
                    "api_key_env": "CLIPROXYAPI_API_KEY",
                },
                "cliproxyapi": {
                    "enabled": True,
                    "base_url": "http://127.0.0.1:8317/v1",
                    "api_key_env": "CLIPROXYAPI_API_KEY",
                },
            }
        )
    )

    profiles = settings.parsed_provider_profiles

    assert [profile.name for profile in profiles] == ["cliproxyapi"]
    assert profiles[0].base_url == "http://127.0.0.1:8317/v1"
    assert profiles[0].configured is True

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import uuid4

import httpx
from pydantic import ValidationError

from app.config import Settings
from app.exceptions import (
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderRateLimitError,
    ProviderModelUnavailableError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.providers.base import ModelProvider
from app.schemas import (
    ChatMessage,
    ProviderChatResponse,
    ProviderModelList,
)

logger = logging.getLogger(__name__)


class BarmanaProvider(ModelProvider):
    name = "barmana"

    def __init__(
        self,
        settings: Settings,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings
        self._owns_client = client is None

        if client is not None:
            self._client = client
            return

        timeout = httpx.Timeout(
            connect=settings.connect_timeout_seconds,
            read=settings.read_timeout_seconds,
            write=settings.write_timeout_seconds,
            pool=settings.pool_timeout_seconds,
        )
        limits = httpx.Limits(
            max_connections=10,
            max_keepalive_connections=5,
            keepalive_expiry=30.0,
        )

        self._client = httpx.AsyncClient(
            base_url=settings.normalized_base_url,
            timeout=timeout,
            limits=limits,
            follow_redirects=False,
            headers={
                "Accept": "application/json",
                "User-Agent": f"ai-engineer-model-gateway/{settings.app_version}",
            },
        )

    def _auth_headers(self) -> dict[str, str]:
        secret = self._settings.barmana_api_key
        if secret is None or not secret.get_secret_value().strip():
            raise ProviderConfigurationError(
                "Barmana API key is not configured in the gateway process."
            )

        api_key = secret.get_secret_value().strip()
        mode = self._settings.barmana_auth_mode

        if mode == "bearer":
            return {"Authorization": f"Bearer {api_key}"}
        if mode == "x-api-key":
            return {"x-api-key": api_key}
        return {"api-key": api_key}

    async def list_models(self) -> ProviderModelList:
        payload = await self._request_json(
            method="GET",
            path=self._settings.barmana_models_path,
        )

        try:
            return ProviderModelList.model_validate(payload)
        except ValidationError as exc:
            raise ProviderResponseError(
                "The provider returned an invalid model-list response.",
                details={"validation_error_count": exc.error_count()},
            ) from exc

    async def chat_completion(
        self,
        *,
        model: str,
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: int,
        tools: list[dict] | None = None,
        tool_choice: str | dict | None = None,
        response_format: dict | None = None,
    ) -> ProviderChatResponse:
        body = {
            "model": model,
            "messages": [message.model_dump() for message in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if tools:
            body["tools"] = tools
        if tool_choice is not None:
            body["tool_choice"] = tool_choice
        if response_format is not None:
            body["response_format"] = response_format

        payload = await self._request_json(
            method="POST",
            path=self._settings.barmana_chat_path,
            json_body=body,
        )

        try:
            parsed = ProviderChatResponse.model_validate(payload)
        except ValidationError as exc:
            raise ProviderResponseError(
                "The provider returned an invalid chat response.",
                details={"validation_error_count": exc.error_count()},
            ) from exc

        if not parsed.choices:
            raise ProviderResponseError(
                "The provider chat response did not contain any choices."
            )

        return parsed

    async def _request_json(
        self,
        *,
        method: str,
        path: str,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        request_id = str(uuid4())
        headers = {
            **self._auth_headers(),
            "X-Request-ID": request_id,
        }

        attempts = self._settings.max_retries + 1

        for attempt_index in range(attempts):
            try:
                response = await self._client.request(
                    method,
                    path,
                    headers=headers,
                    json=json_body,
                )
            except httpx.TimeoutException as exc:
                if attempt_index + 1 < attempts:
                    await self._sleep_before_retry(attempt_index)
                    continue
                raise ProviderTimeoutError(
                    "The provider did not respond before the configured timeout."
                ) from exc
            except httpx.RequestError as exc:
                if attempt_index + 1 < attempts:
                    await self._sleep_before_retry(attempt_index)
                    continue
                raise ProviderUnavailableError(
                    "The provider could not be reached."
                ) from exc

            if response.status_code in {401, 403}:
                raise ProviderAuthenticationError(
                    "The provider rejected the configured API credentials."
                )

            if response.status_code == 429:
                if attempt_index + 1 < attempts:
                    await self._sleep_before_retry(attempt_index)
                    continue
                raise ProviderRateLimitError(
                    "The provider rate limit was reached.",
                    details={"upstream_status": response.status_code},
                )

            if response.status_code == 504:
                if attempt_index + 1 < attempts:
                    await self._sleep_before_retry(attempt_index)
                    continue
                raise ProviderTimeoutError(
                    "The selected upstream model timed out.",
                    details={
                        "upstream_status": response.status_code,
                        "upstream_error": self._safe_error_preview(response),
                    },
                )

            if response.status_code >= 500:
                if attempt_index + 1 < attempts:
                    await self._sleep_before_retry(attempt_index)
                    continue
                raise ProviderUnavailableError(
                    f"The provider returned HTTP {response.status_code}.",
                    details={
                        "upstream_status": response.status_code,
                        "upstream_error": self._safe_error_preview(response),
                    },
                )

            if response.status_code in {400, 404, 422}:
                error_preview = self._safe_error_preview(response)

                if self._is_model_unavailable_error(error_preview):
                    raise ProviderModelUnavailableError(
                        "The selected provider model is unavailable.",
                        details={
                            "upstream_status": response.status_code,
                            "upstream_error": error_preview,
                        },
                    )

                raise ProviderResponseError(
                    f"The provider returned HTTP {response.status_code}.",
                    details={
                        "upstream_status": response.status_code,
                        "upstream_error": error_preview,
                    },
                )

            if response.status_code >= 400:
                raise ProviderResponseError(
                    f"The provider returned HTTP {response.status_code}.",
                    details={
                        "upstream_status": response.status_code,
                        "upstream_error": self._safe_error_preview(response),
                    },
                )

            try:
                payload = response.json()
            except ValueError as exc:
                raise ProviderResponseError(
                    "The provider response was not valid JSON."
                ) from exc

            if not isinstance(payload, dict):
                raise ProviderResponseError(
                    "The provider JSON response must be an object."
                )

            return payload

        raise ProviderUnavailableError(
            "The provider request failed after all retries."
        )

    @staticmethod
    def _safe_error_preview(response: httpx.Response) -> str | None:
        try:
            preview = response.text.strip().replace("\r", " ").replace("\n", " ")
        except Exception:
            return None

        if not preview:
            return None

        return preview[:800]

    @staticmethod
    def _is_model_unavailable_error(error_preview: str | None) -> bool:
        if not error_preview:
            return False

        normalized = error_preview.casefold()
        markers = (
            "no such model",
            "model_not_found",
            "model not found",
            "unknown model",
            "invalid model",
            "\"code\":5007",
        )
        return any(marker in normalized for marker in markers)

    async def _sleep_before_retry(self, attempt_index: int) -> None:
        delay = self._settings.retry_base_delay_seconds * (2**attempt_index)
        await asyncio.sleep(delay)

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import urlsplit
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
        self._ollama_native = self._is_native_ollama_url(settings.normalized_base_url)

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

    @staticmethod
    def _is_native_ollama_url(base_url: str) -> bool:
        try:
            parsed = urlsplit(base_url)
            host = (parsed.hostname or "").casefold().rstrip(".")
            return (
                parsed.scheme.casefold() == "http"
                and host in {"127.0.0.1", "localhost", "::1"}
                and parsed.port == 11434
            )
        except ValueError:
            return False


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
        if self._ollama_native:
            payload = await self._request_json(
                method="POST",
                path="../api/chat",
                json_body=self._build_ollama_body(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    tools=tools,
                    tool_choice=tool_choice,
                    response_format=response_format,
                ),
            )
            return self._parse_ollama_response(payload, requested_model=model)

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

    @staticmethod
    def _build_ollama_body(
        *,
        model: str,
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: int,
        tools: list[dict] | None,
        tool_choice: str | dict | None,
        response_format: dict | None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": model,
            "messages": [message.model_dump() for message in messages],
            "stream": False,
            "think": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if tools and tool_choice != "none":
            body["tools"] = tools
        if response_format:
            native_format = BarmanaProvider._native_response_format(response_format)
            if native_format is not None:
                body["format"] = native_format
        return body

    @staticmethod
    def _native_response_format(response_format: dict[str, Any]) -> str | dict[str, Any] | None:
        response_type = response_format.get("type")
        if response_type == "json_object":
            return "json"
        if response_type == "json_schema":
            schema = response_format.get("json_schema")
            if isinstance(schema, dict) and isinstance(schema.get("schema"), dict):
                return schema["schema"]
        return None

    @staticmethod
    def _parse_ollama_response(
        payload: dict[str, Any],
        *,
        requested_model: str,
    ) -> ProviderChatResponse:
        native_message = payload.get("message")
        if not isinstance(native_message, dict):
            native_message = {
                "role": "assistant",
                "content": str(payload.get("response") or ""),
            }
        else:
            native_message = dict(native_message)
            native_message.setdefault("role", "assistant")
            if native_message.get("content") is None:
                native_message["content"] = ""

        normalized: dict[str, Any] = {
            "id": str(payload.get("id") or f"ollama-{uuid4().hex}"),
            "object": "chat.completion",
            "model": str(payload.get("model") or requested_model),
            "choices": [
                {
                    "index": 0,
                    "message": native_message,
                    "finish_reason": payload.get("done_reason")
                    or ("stop" if payload.get("done") else None),
                }
            ],
        }

        prompt_tokens = payload.get("prompt_eval_count")
        completion_tokens = payload.get("eval_count")
        usage: dict[str, int] = {}
        if isinstance(prompt_tokens, int) and prompt_tokens >= 0:
            usage["prompt_tokens"] = prompt_tokens
        if isinstance(completion_tokens, int) and completion_tokens >= 0:
            usage["completion_tokens"] = completion_tokens
        if usage:
            usage["total_tokens"] = usage.get("prompt_tokens", 0) + usage.get(
                "completion_tokens", 0
            )
            normalized["usage"] = usage

        try:
            parsed = ProviderChatResponse.model_validate(normalized)
        except ValidationError as exc:
            raise ProviderResponseError(
                "The provider returned an invalid native Ollama chat response.",
                details={"validation_error_count": exc.error_count()},
            ) from exc

        if not parsed.choices:
            raise ProviderResponseError(
                "The provider native Ollama response did not contain any choices."
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

            response_bytes = len(response.content)
            if response_bytes > self._settings.max_provider_response_bytes:
                raise ProviderResponseError(
                    "The provider response exceeded the configured byte limit.",
                    details={
                        "response_bytes": response_bytes,
                        "max_response_bytes": self._settings.max_provider_response_bytes,
                    },
                )

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

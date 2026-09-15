"""Multi-provider routing for configured OpenAI-compatible endpoints."""

from __future__ import annotations

import asyncio

from app.providers.base import ModelProvider, ProviderProfile
MAX_CATALOG_MODELS = 1000

from app.schemas import (
    ChatMessage,
    ProviderChatResponse,
    ProviderModel,
    ProviderModelList,
)


class ProviderPool(ModelProvider):
    """Route qualified model ids to a configured provider profile."""

    def __init__(
        self,
        providers: dict[str, ModelProvider],
        profiles: tuple[ProviderProfile, ...],
        *,
        default_name: str,
    ) -> None:
        self._providers = dict(providers)
        self._profiles = {profile.name: profile for profile in profiles}
        self._default_name = default_name if default_name in self._providers else next(iter(self._providers))
        self.name = "pool:" + ",".join(self._providers)

    @property
    def configured(self) -> bool:
        return bool(self._providers)

    @property
    def candidate_models(self) -> tuple[str, ...]:
        candidates: list[str] = []
        for profile in self._profiles.values():
            for model in (profile.default_model, *profile.fallback_models):
                if model and profile.name in self._providers:
                    qualified = f"{profile.name}/{model}"
                    if qualified not in candidates:
                        candidates.append(qualified)
        return tuple(candidates)

    def _resolve(self, model: str) -> tuple[ModelProvider, str, str]:
        if "/" in model:
            provider_name, provider_model = model.split("/", 1)
            provider = self._providers.get(provider_name)
            if provider is not None and provider_model:
                return provider, provider_model, provider_name
        return self._providers[self._default_name], model, self._default_name

    async def list_models(self) -> ProviderModelList:
        catalog: list[ProviderModel] = []
        for provider_name, provider in self._providers.items():
            if len(catalog) >= MAX_CATALOG_MODELS:
                break
            result = await provider.list_models()
            for model in result.data:
                if len(catalog) >= MAX_CATALOG_MODELS:
                    break
                catalog.append(
                    model.model_copy(
                        update={
                            "id": f"{provider_name}/{model.id}",
                            "providers": sorted({provider_name, *model.providers}),
                        }
                    )
                )
        return ProviderModelList(object="list", data=catalog)

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
        provider, provider_model, _provider_name = self._resolve(model)
        response = await provider.chat_completion(
            model=provider_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            tool_choice=tool_choice,
            response_format=response_format,
        )
        return response.model_copy(update={"model": model})

    async def close(self) -> None:
        await asyncio.gather(*(provider.close() for provider in self._providers.values()))


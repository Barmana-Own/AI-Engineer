from __future__ import annotations

import asyncio
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.schemas import GatewayModelList, ProviderModelList

_CACHE_MAX_BYTES = 4 * 1024 * 1024


class ModelCatalogCache:
    """Small in-memory cache with a sanitized JSON disk fallback."""

    def __init__(self, path: Path, ttl_seconds: int) -> None:
        self._path = path
        self._ttl = timedelta(seconds=ttl_seconds)
        self._memory: GatewayModelList | None = None
        self._lock = asyncio.Lock()

    async def get_fresh(self) -> GatewayModelList | None:
        async with self._lock:
            entry = self._memory
            if entry is None:
                entry = await asyncio.to_thread(self._read_from_disk)
                self._memory = entry

            if entry is None:
                return None

            if datetime.now(UTC) - entry.fetched_at > self._ttl:
                return None

            return entry.model_copy(update={"cached": True, "stale": False})

    async def get_stale(self) -> GatewayModelList | None:
        async with self._lock:
            entry = self._memory
            if entry is None:
                entry = await asyncio.to_thread(self._read_from_disk)
                self._memory = entry

            if entry is None:
                return None

            return entry.model_copy(update={"cached": True, "stale": True})

    async def set(self, payload: ProviderModelList, *, source: str = "barmana") -> GatewayModelList:
        entry = GatewayModelList(
            source=source,
            cached=False,
            stale=False,
            fetched_at=datetime.now(UTC),
            data=payload.data,
        )

        async with self._lock:
            await asyncio.to_thread(self._write_to_disk, entry)
            self._memory = entry

        return entry

    def _read_from_disk(self) -> GatewayModelList | None:
        if not self._path.exists():
            return None

        try:
            raw = self._path.read_bytes()
            if len(raw) > _CACHE_MAX_BYTES:
                return None
            return GatewayModelList.model_validate(json.loads(raw))
        except (OSError, ValueError, UnicodeError):
            return None

    def _write_to_disk(self, entry: GatewayModelList) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self._path.with_suffix(self._path.suffix + ".tmp")

        serialized = json.dumps(
            entry.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")
        if len(serialized) > _CACHE_MAX_BYTES:
            raise ValueError(
                f"Model catalog cache exceeds {_CACHE_MAX_BYTES} bytes."
            )
        temporary_path.write_bytes(serialized)
        os.replace(temporary_path, self._path)

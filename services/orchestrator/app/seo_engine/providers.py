"""Provider-neutral adapters for WordPress, Rank Math, and Search Console."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlencode, urlsplit

from .security import UnsafeTargetError, validate_url


class WordPressAdapter(Protocol):
    def list_posts(self, *, status: str = "draft", limit: int = 50) -> list[dict[str, Any]]: ...
    def create_draft(self, *, title: str, content: str, metadata: dict[str, str] | None = None) -> dict[str, Any]: ...
    def update_draft(self, post_id: str, *, content: str, metadata: dict[str, str] | None = None) -> dict[str, Any]: ...
    def publish(self, post_id: str) -> dict[str, Any]: ...


class MockWordPressAdapter:
    """Deterministic draft-first adapter used by tests and local workflows."""

    def __init__(self, base_url: str) -> None:
        self.base_url = validate_url(base_url, allow_local=True)
        self._posts: dict[str, dict[str, Any]] = {}

    def list_posts(self, *, status: str = "draft", limit: int = 50) -> list[dict[str, Any]]:
        return [dict(item) for item in list(self._posts.values()) if item["status"] == status][: max(1, min(limit, 100))]

    def create_draft(self, *, title: str, content: str, metadata: dict[str, str] | None = None) -> dict[str, Any]:
        post_id = str(len(self._posts) + 1)
        result = {"id": post_id, "title": str(title)[:500], "content": str(content), "metadata": dict(metadata or {}), "status": "draft"}
        self._posts[post_id] = result
        return dict(result)

    def update_draft(self, post_id: str, *, content: str, metadata: dict[str, str] | None = None) -> dict[str, Any]:
        existing = self._posts.get(str(post_id))
        if not existing or existing["status"] != "draft":
            raise KeyError(post_id)
        existing["content"] = str(content)
        existing["metadata"] = dict(metadata or existing.get("metadata", {}))
        return dict(existing)

    def publish(self, post_id: str) -> dict[str, Any]:
        raise PermissionError("Direct WordPress publishing is disabled; request an owner-approved deployment action.")


class SearchConsoleProvider(Protocol):
    mode: str

    def query(self, *, site_url: str, start_date: str, end_date: str, dimensions: tuple[str, ...] = ("query", "page")) -> dict[str, Any]: ...


@dataclass(frozen=True)
class NoDataSearchConsoleProvider:
    mode: str = "no_data"

    def query(self, *, site_url: str, start_date: str, end_date: str, dimensions: tuple[str, ...] = ("query", "page")) -> dict[str, Any]:
        return {"mode": self.mode, "data_available": False, "rows": [], "reason": "Search Console credentials/provider are not configured."}


@dataclass(frozen=True)
class MockSearchConsoleProvider:
    mode: str = "mock"

    def query(self, *, site_url: str, start_date: str, end_date: str, dimensions: tuple[str, ...] = ("query", "page")) -> dict[str, Any]:
        return {"mode": self.mode, "data_available": False, "rows": [], "reason": "Deterministic mock provider; no real analytics claim is made.", "dimensions": list(dimensions)}


def validate_wordpress_base_url(base_url: str, *, allow_local: bool = False, allowed_hosts: set[str] | None = None) -> str:
    value = validate_url(base_url, allow_local=allow_local, allowed_hosts=allowed_hosts, require_https_for_non_local=not allow_local)
    if urlsplit(value).path not in {"", "/"}:
        return value.rstrip("/")
    return value.rstrip("/")

class RestWordPressAdapter:
    """Bounded WordPress REST adapter with draft-first publication policy.

    Credentials are held only by the server-side adapter. They are never
    serialized into findings, task prompts, or URLs.
    """

    def __init__(
        self,
        base_url: str,
        *,
        username: str,
        application_password: str,
        allowed_hosts: set[str] | None = None,
        allow_local: bool = False,
        timeout_seconds: float = 15.0,
    ) -> None:
        self.base_url = validate_wordpress_base_url(base_url, allow_local=allow_local, allowed_hosts=allowed_hosts)
        if not username.strip() or not application_password.strip():
            raise ValueError("WordPress credentials must be provided through secure server configuration.")
        self._username = username
        self._application_password = application_password
        self._timeout_seconds = max(1.0, min(float(timeout_seconds), 60.0))

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any] | list[dict[str, Any]]:
        import httpx

        target = validate_url(f"{self.base_url}/wp-json/wp/v2/{path.lstrip('/')}", allow_local=True)
        with httpx.Client(timeout=self._timeout_seconds, follow_redirects=False) as client:
            response = client.request(method, target, auth=(self._username, self._application_password), json=payload)
            if response.status_code >= 400:
                raise RuntimeError(f"WordPress request failed with status {response.status_code}.")
            value = response.json()
            if not isinstance(value, (dict, list)):
                raise RuntimeError("WordPress returned an unsupported response.")
            return value

    def list_posts(self, *, status: str = "draft", limit: int = 50) -> list[dict[str, Any]]:
        status_value = str(status).strip().casefold()
        if status_value not in {"draft", "future", "pending", "private", "publish"}:
            raise ValueError("Unsupported WordPress post status.")
        value = self._request(
            "GET",
            "posts?" + urlencode({"status": status_value, "per_page": max(1, min(limit, 100))}),
        )
        return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []

    def create_draft(self, *, title: str, content: str, metadata: dict[str, str] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"title": str(title)[:500], "content": str(content), "status": "draft"}
        if metadata:
            payload["meta"] = {str(key)[:100]: str(value)[:2_000] for key, value in metadata.items()}
        value = self._request("POST", "posts", payload)
        if not isinstance(value, dict):
            raise RuntimeError("WordPress did not return a draft post object.")
        return value

    def update_draft(self, post_id: str, *, content: str, metadata: dict[str, str] | None = None) -> dict[str, Any]:
        if not str(post_id).isdigit():
            raise ValueError("WordPress post_id must be numeric.")
        payload: dict[str, Any] = {"content": str(content)}
        if metadata:
            payload["meta"] = {str(key)[:100]: str(value)[:2_000] for key, value in metadata.items()}
        value = self._request("POST", f"posts/{int(post_id)}", payload)
        if not isinstance(value, dict):
            raise RuntimeError("WordPress did not return an updated draft object.")
        return value

    def publish(self, post_id: str) -> dict[str, Any]:
        raise PermissionError("Direct WordPress publishing is disabled; request an owner-approved deployment action.")

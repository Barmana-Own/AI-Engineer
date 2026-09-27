"""Outbound SEO inspection safety boundaries.

This module is intentionally independent from the Local Agent.  It only
performs bounded, read-only retrieval; production mutations must still go
through the existing Agent Worker and Local Agent policy.
"""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit, urlunsplit



class UnsafeTargetError(ValueError):
    """Raised when a URL is outside the declared SEO inspection scope."""


def _host_is_private(host: str) -> bool:
    try:
        address = ipaddress.ip_address(host)
        return address.is_private or address.is_loopback or address.is_link_local or address.is_reserved
    except ValueError:
        pass
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, None)}
    except (OSError, socket.gaierror):
        return False
    for address in addresses:
        try:
            parsed = ipaddress.ip_address(address)
        except ValueError:
            continue
        if parsed.is_private or parsed.is_loopback or parsed.is_link_local or parsed.is_reserved:
            return True
    return False


def validate_url(
    value: str,
    *,
    allowed_hosts: set[str] | None = None,
    allow_local: bool = False,
    require_https_for_non_local: bool = False,
) -> str:
    """Validate and canonicalize an inspection URL before any network call."""

    raw = str(value or "").strip()
    parsed = urlsplit(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise UnsafeTargetError("SEO targets must use an HTTP or HTTPS URL with a hostname.")
    if parsed.username or parsed.password or parsed.fragment:
        raise UnsafeTargetError("Credentials and fragments are not allowed in SEO targets.")
    host = parsed.hostname.casefold().rstrip(".")
    is_local = host in {"localhost", "127.0.0.1", "::1"} or _host_is_private(host)
    if is_local and not allow_local:
        raise UnsafeTargetError("Private and local network targets require explicit local inspection mode.")
    if require_https_for_non_local and not is_local and parsed.scheme != "https":
        raise UnsafeTargetError("Non-local SEO targets must use HTTPS.")
    if allowed_hosts and host not in {item.casefold().rstrip(".") for item in allowed_hosts}:
        raise UnsafeTargetError("SEO target host is not in the declared allowlist.")
    port = parsed.port
    if port is not None and not 1 <= port <= 65535:
        raise UnsafeTargetError("Invalid target port.")
    normalized_path = parsed.path or "/"
    return urlunsplit((parsed.scheme.lower(), parsed.netloc, normalized_path, parsed.query, ""))


def same_host(base_url: str, candidate_url: str) -> bool:
    base = urlsplit(base_url).hostname
    candidate = urlsplit(candidate_url).hostname
    return bool(base and candidate and base.casefold().rstrip(".") == candidate.casefold().rstrip("."))


@dataclass(frozen=True)
class SafeHttpResponse:
    url: str
    status_code: int
    headers: dict[str, str]
    body: bytes
    redirected_to: str | None = None


class SafeHttpClient:
    """Small bounded HTTP reader with same-host redirect enforcement."""

    def __init__(
        self,
        *,
        allowed_hosts: set[str] | None = None,
        allow_local: bool = False,
        timeout_seconds: float = 10.0,
        max_response_bytes: int = 2_000_000,
    ) -> None:
        self.allowed_hosts = allowed_hosts
        self.allow_local = allow_local
        self.timeout_seconds = max(0.5, min(float(timeout_seconds), 120.0))
        self.max_response_bytes = max(10_000, min(int(max_response_bytes), 20_000_000))

    def fetch(self, url: str, *, base_url: str | None = None) -> SafeHttpResponse:
        safe_url = validate_url(url, allowed_hosts=self.allowed_hosts, allow_local=self.allow_local)
        if base_url and not same_host(base_url, safe_url):
            raise UnsafeTargetError("Requested URL is outside the declared site host.")
        headers = {
            "User-Agent": "AI-Engineer-SEO-Audit/1.0 (+evidence-only)",
            "Accept": "text/html,application/xhtml+xml,application/xml,text/plain;q=0.8,*/*;q=0.1",
        }
        import httpx

        with httpx.Client(timeout=self.timeout_seconds, follow_redirects=False, headers=headers) as client:
            with client.stream("GET", safe_url) as response:
                chunks: list[bytes] = []
                total = 0
                for chunk in response.iter_bytes():
                    remaining = self.max_response_bytes - total
                    if remaining <= 0:
                        break
                    chunks.append(chunk[:remaining])
                    total += min(len(chunk), remaining)
                    if len(chunk) >= remaining:
                        break
                body = b"".join(chunks)
                location = response.headers.get("location")
                redirected_to: str | None = None
                if location:
                    redirected_to = urljoin(safe_url, location)
                    validate_url(redirected_to, allowed_hosts=self.allowed_hosts, allow_local=self.allow_local)
                    if not same_host(safe_url, redirected_to):
                        raise UnsafeTargetError("Cross-host redirects are not allowed during SEO crawling.")
                return SafeHttpResponse(
                    url=safe_url,
                    status_code=response.status_code,
                    headers={str(key).lower(): str(value) for key, value in response.headers.items()},
                    body=body,
                    redirected_to=redirected_to,
                )

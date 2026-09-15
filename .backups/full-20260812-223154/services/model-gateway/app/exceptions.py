from __future__ import annotations


class GatewayError(Exception):
    status_code = 500
    code = "gateway_error"
    retryable = False

    def __init__(self, message: str, *, details: dict[str, object] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details


class ProviderConfigurationError(GatewayError):
    status_code = 503
    code = "provider_not_configured"


class ProviderAuthenticationError(GatewayError):
    status_code = 502
    code = "provider_authentication_failed"


class ProviderTimeoutError(GatewayError):
    status_code = 504
    code = "provider_timeout"
    retryable = True


class ProviderRateLimitError(GatewayError):
    status_code = 503
    code = "provider_rate_limited"
    retryable = True


class ProviderModelUnavailableError(GatewayError):
    """The provider accepted the request but rejected its selected model."""

    status_code = 502
    code = "provider_model_unavailable"
    retryable = True


class ProviderUnavailableError(GatewayError):
    status_code = 502
    code = "provider_unavailable"
    retryable = True


class ProviderResponseError(GatewayError):
    status_code = 502
    code = "provider_invalid_response"


class NoModelSucceededError(GatewayError):
    status_code = 502
    code = "no_model_succeeded"
    retryable = True

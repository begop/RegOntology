from __future__ import annotations

from typing import Any


class DomainError(Exception):
    code = "domain_error"
    status_code = 400
    public_message = "요청을 처리할 수 없습니다."

    def __init__(self, message: str | None = None, details: list[dict[str, Any]] | None = None):
        super().__init__(message or self.public_message)
        self.details = details or []


class NotFoundError(DomainError):
    code = "not_found"
    status_code = 404
    public_message = "요청한 리소스를 찾을 수 없습니다."


class ForbiddenError(DomainError):
    code = "forbidden"
    status_code = 403
    public_message = "요청한 작업을 수행할 권한이 없습니다."


class ConfigurationError(DomainError):
    code = "configuration_error"
    status_code = 503
    public_message = "서비스 구성이 준비되지 않았습니다."


class ProviderUnavailableError(DomainError):
    code = "provider_unavailable"
    status_code = 503
    public_message = "AI 제공자를 일시적으로 사용할 수 없습니다."


class InvalidRequestError(DomainError):
    code = "invalid_request"
    status_code = 400
    public_message = "요청 값이 올바르지 않습니다."

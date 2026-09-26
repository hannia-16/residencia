from src.exceptions import AppError


class AIError(AppError):
    status_code = 502
    code = "ai_error"
    message = "The AI provider returned an error."


class AINotConfigured(AIError):
    status_code = 503
    code = "ai_not_configured"
    message = "The AI provider is not configured on this server."


class AIUpstreamError(AIError):
    code = "ai_upstream_error"
    message = "The AI provider is unreachable or returned an error."


class AIRequestError(AIError):
    code = "ai_request_rejected"
    message = "The AI provider rejected the request."


class AIRateLimited(AIError):
    status_code = 429
    code = "ai_rate_limited"
    message = "The AI provider rate limit has been reached."


class AITimeout(AIError):
    status_code = 504
    code = "ai_timeout"
    message = "The AI provider did not respond in time."


class AIResponseError(AIError):
    code = "ai_invalid_response"
    message = "The AI provider returned a response that could not be parsed."

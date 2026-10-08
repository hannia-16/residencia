from src.exceptions import AppError


class SpeechError(AppError):
    status_code = 502
    code = "speech_error"
    message = "The speech service returned an error."


class SpeechNotConfigured(SpeechError):
    status_code = 503
    code = "speech_not_configured"
    message = "The speech-to-text service is not configured on this server."


class SpeechUpstreamError(SpeechError):
    code = "speech_upstream_error"
    message = "The speech service is unreachable or returned an error."


class SpeechRequestError(SpeechError):
    code = "speech_request_rejected"
    message = "The speech service rejected the audio."


class SpeechRateLimited(SpeechError):
    status_code = 429
    code = "speech_rate_limited"
    message = "The speech service rate limit has been reached."


class SpeechTimeout(SpeechError):
    status_code = 504
    code = "speech_timeout"
    message = "The speech service did not respond in time."


class SpeechResponseError(SpeechError):
    code = "speech_invalid_response"
    message = "The speech service returned a response that could not be parsed."

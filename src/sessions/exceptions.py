from src.exceptions import AppError


class SessionError(AppError):
    status_code = 404
    code = "session_error"
    message = "The session could not be processed."


class SessionNotFound(SessionError):
    code = "session_not_found"
    message = "No session matches the given identifier."


class SessionUnavailable(SessionError):
    status_code = 410
    code = "session_not_available"
    message = "This session is older than 30 days and is no longer available."


class SessionConcluded(SessionError):
    status_code = 409
    code = "session_concluded"
    message = "This session was already closed."


class SessionNotActive(SessionError):
    status_code = 409
    code = "session_not_active"
    message = "This session is not active."


class SessionNotPaused(SessionError):
    status_code = 409
    code = "session_not_paused"
    message = "This session is not paused."


class FeedbackNotAvailable(SessionError):
    code = "feedback_not_available"
    message = "The feedback report becomes available once the session is closed."


class EvaluationNotAllowed(SessionError):
    status_code = 409
    code = "evaluation_not_allowed"
    message = "The session must be closed before it can be evaluated."


class EvaluationAlreadySubmitted(SessionError):
    status_code = 409
    code = "evaluation_already_submitted"
    message = "This session was already evaluated."


class TurnFailed(SessionError):
    status_code = 502
    code = "turn_failed"
    message = "The AI provider did not return a valid turn. Please try again."


class AudioTooLarge(SessionError):
    status_code = 413
    code = "audio_too_large"
    message = "The audio file exceeds the maximum allowed size."


class UnsupportedAudioFormat(SessionError):
    status_code = 415
    code = "unsupported_audio_format"
    message = "The audio format is not supported."


class EmptyTranscription(SessionError):
    status_code = 422
    code = "empty_transcription"
    message = "No speech could be detected in the audio."

from typing import Annotated

from fastapi import Depends, Request

from src.speech.client import SpeechToText


def get_speech_client(request: Request) -> SpeechToText:
    return request.app.state.speech_client


SpeechClient = Annotated[SpeechToText, Depends(get_speech_client)]

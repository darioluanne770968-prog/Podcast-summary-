"""语音转文字模块"""

from .whisper_engine import WhisperTranscriber, TranscriptionResult, Segment
from .diarization import SpeakerDiarizer, DiarizedSegment

__all__ = [
    "WhisperTranscriber",
    "TranscriptionResult",
    "Segment",
    "SpeakerDiarizer",
    "DiarizedSegment",
]

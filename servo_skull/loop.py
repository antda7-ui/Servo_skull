"""Composable Phase 1 voice loop."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .audio import AudioAdapter
from .ollama import OllamaAdapter
from .push_to_talk import PushToTalkRecorder
from .tts import PiperAdapter, SoxEffectsAdapter
from .whisper import WhisperAdapter


class VoiceLoopError(RuntimeError):
    """A recoverable failure during one voice turn."""


@dataclass(frozen=True)
class TurnResult:
    transcript: str
    response: str
    audio_path: Path | None


class VoiceLoop:
    def __init__(
        self,
        recorder: PushToTalkRecorder,
        whisper: WhisperAdapter,
        ollama: OllamaAdapter,
        piper: PiperAdapter,
        effects: SoxEffectsAdapter,
        audio: AudioAdapter,
        status: Callable[[str], None] = print,
        effects_enabled: bool = True,
        debug_directory: Path | None = None,
    ):
        self.recorder = recorder
        self.whisper = whisper
        self.ollama = ollama
        self.piper = piper
        self.effects = effects
        self.audio = audio
        self.status = status
        self.effects_enabled = effects_enabled
        self.debug_directory = debug_directory

    def run_turn(self) -> TurnResult | None:
        temporary_directory = None
        try:
            if self.debug_directory is None:
                temporary_directory = tempfile.TemporaryDirectory(prefix="servo-skull-turn-")
                turn_directory = Path(temporary_directory.name)
            else:
                self.debug_directory.mkdir(parents=True, exist_ok=True)
                turn_directory = Path(
                    tempfile.mkdtemp(prefix="turn-", dir=self.debug_directory)
                )

            recording_path = turn_directory / "recording.wav"
            clean_path = turn_directory / "response-clean.wav"
            processed_path = turn_directory / "response-processed.wav"

            self.status("Waiting for speech...")
            recorded = self.recorder.capture(recording_path)
            if recorded is None:
                return None

            self.status("Transcribing...")
            transcript = self.whisper.transcribe(recorded).text.strip()
            if not transcript:
                raise VoiceLoopError("Whisper returned no speech")

            self.status("Thinking...")
            response = self.ollama.chat(transcript).text.strip()
            if not response:
                raise VoiceLoopError("Ollama returned no response")

            self.status("Synthesizing...")
            clean_audio = self.piper.synthesize(response, clean_path)
            final_audio = clean_audio
            if self.effects_enabled:
                self.status("Applying audio effects...")
                final_audio = self.effects.apply(clean_audio, processed_path)

            self.status("Playing...")
            self.audio.play(final_audio)
            return TurnResult(transcript, response, final_audio if self.debug_directory else None)
        finally:
            if temporary_directory is not None:
                temporary_directory.cleanup()
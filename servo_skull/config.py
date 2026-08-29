"""Configuration for local, CPU-only runtime components."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WhisperConfig:
    executable: Path = Path.home() / "whisper.cpp/build/bin/whisper-cli"
    model: Path = Path.home() / "whisper.cpp/models/ggml-base.en.bin"
    threads: int = 4
    timeout_seconds: float = 120.0
    language: str = "en"

    @classmethod
    def from_environment(cls) -> "WhisperConfig":
        return cls(
            executable=Path(os.getenv("SERVO_SKULL_WHISPER_EXECUTABLE", cls.executable)),
            model=Path(os.getenv("SERVO_SKULL_WHISPER_MODEL", cls.model)),
            threads=int(os.getenv("SERVO_SKULL_WHISPER_THREADS", cls.threads)),
            timeout_seconds=float(
                os.getenv("SERVO_SKULL_WHISPER_TIMEOUT", cls.timeout_seconds)
            ),
            language=os.getenv("SERVO_SKULL_WHISPER_LANGUAGE", cls.language),
        )


@dataclass(frozen=True)
class AudioConfig:
    device: str = "default"
    sample_rate: int = 16000
    channels: int = 1
    max_recording_seconds: float = 30.0

    @classmethod
    def from_environment(cls) -> "AudioConfig":
        return cls(
            device=os.getenv("SERVO_SKULL_AUDIO_DEVICE", cls.device),
            sample_rate=int(os.getenv("SERVO_SKULL_AUDIO_SAMPLE_RATE", cls.sample_rate)),
            channels=int(os.getenv("SERVO_SKULL_AUDIO_CHANNELS", cls.channels)),
            max_recording_seconds=float(
                os.getenv("SERVO_SKULL_MAX_RECORDING_SECONDS", cls.max_recording_seconds)
            ),
        )


@dataclass(frozen=True)
class OllamaConfig:
    endpoint: str = "http://127.0.0.1:11434/api/chat"
    model: str = "llama3.2:3b-instruct"
    timeout_seconds: float = 90.0
    max_history_turns: int = 2
    max_response_tokens: int = 48

    @classmethod
    def from_environment(cls, fast_mode: bool = False) -> "OllamaConfig":
        overrides = {
            "timeout_seconds": cls.timeout_seconds,
            "max_history_turns": cls.max_history_turns,
            "max_response_tokens": cls.max_response_tokens,
        }
        if fast_mode:
            overrides = {
                "timeout_seconds": 60.0,
                "max_history_turns": 2,
                "max_response_tokens": 32,
            }
        return cls(
            endpoint=os.getenv("SERVO_SKULL_OLLAMA_ENDPOINT", cls.endpoint),
            model=os.getenv("SERVO_SKULL_OLLAMA_MODEL", cls.model),
            timeout_seconds=float(
                os.getenv("SERVO_SKULL_OLLAMA_TIMEOUT", overrides["timeout_seconds"])
            ),
            max_history_turns=int(
                os.getenv(
                    "SERVO_SKULL_OLLAMA_MAX_HISTORY_TURNS",
                    overrides["max_history_turns"],
                )
            ),
            max_response_tokens=int(
                os.getenv(
                    "SERVO_SKULL_OLLAMA_MAX_RESPONSE_TOKENS",
                    overrides["max_response_tokens"],
                )
            ),
        )


@dataclass(frozen=True)
class TtsConfig:
    executable: Path = Path.home() / "servo-skull-venv/bin/piper"
    voice: Path = Path.home() / "en_GB-alan-medium.onnx"
    timeout_seconds: float = 60.0

    @classmethod
    def from_environment(cls) -> "TtsConfig":
        return cls(
            executable=Path(os.getenv("SERVO_SKULL_PIPER_EXECUTABLE", cls.executable)),
            voice=Path(os.getenv("SERVO_SKULL_PIPER_VOICE", cls.voice)),
            timeout_seconds=float(
                os.getenv("SERVO_SKULL_PIPER_TIMEOUT", cls.timeout_seconds)
            ),
        )


@dataclass(frozen=True)
class EffectsConfig:
    executable: str = "sox"
    timeout_seconds: float = 30.0
    effects: tuple[str, ...] = ("overdrive", "6", "chorus", "0.5", "0.7", "20", "0.4", "0.25", "2", "-t")

    @classmethod
    def from_environment(cls) -> "EffectsConfig":
        effects = os.getenv("SERVO_SKULL_SOX_EFFECTS")
        return cls(
            executable=os.getenv("SERVO_SKULL_SOX_EXECUTABLE", cls.executable),
            timeout_seconds=float(
                os.getenv("SERVO_SKULL_SOX_TIMEOUT", cls.timeout_seconds)
            ),
            effects=tuple(effects.split()) if effects else cls.effects,
        )


@dataclass(frozen=True)
class AppConfig:
    whisper: WhisperConfig = WhisperConfig()
    audio: AudioConfig = AudioConfig()
    ollama: OllamaConfig = OllamaConfig()
    tts: TtsConfig = TtsConfig()
    effects: EffectsConfig = EffectsConfig()

    @classmethod
    def from_environment(cls, fast_mode: bool = False) -> "AppConfig":
        return cls(
            whisper=WhisperConfig.from_environment(),
            audio=AudioConfig.from_environment(),
            ollama=OllamaConfig.from_environment(fast_mode=fast_mode),
            tts=TtsConfig.from_environment(),
            effects=EffectsConfig.from_environment(),
        )

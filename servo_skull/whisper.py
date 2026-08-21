"""Subprocess adapter for the local whisper.cpp command-line client."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import WhisperConfig


class WhisperError(RuntimeError):
    """Base error for recoverable Whisper failures."""


class WhisperExecutionError(WhisperError):
    """The Whisper process returned a non-zero exit status."""


class WhisperTimeoutError(WhisperError):
    """The Whisper process exceeded its configured timeout."""


@dataclass(frozen=True)
class Transcription:
    text: str


class WhisperAdapter:
    def __init__(self, config: WhisperConfig):
        self.config = config

    def build_command(self, audio_path: Path) -> list[str]:
        return [
            str(self.config.executable),
            "-m",
            str(self.config.model),
            "-f",
            str(audio_path),
            "-l",
            self.config.language,
            "-t",
            str(self.config.threads),
            "-ng",
            "-nt",
            "-np",
        ]

    def transcribe(self, audio_path: Path) -> Transcription:
        command = self.build_command(audio_path)
        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds,
            )
        except subprocess.TimeoutExpired as error:
            raise WhisperTimeoutError(
                f"Whisper timed out after {self.config.timeout_seconds:.1f} seconds"
            ) from error
        except OSError as error:
            raise WhisperExecutionError(
                f"Unable to start Whisper executable {self.config.executable}: {error}"
            ) from error

        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
            raise WhisperExecutionError(
                f"Whisper exited with status {result.returncode}: {detail}"
            )

        text = self._normalize_output(result.stdout)
        return Transcription(text=text)

    @staticmethod
    def _normalize_output(output: str) -> str:
        lines = [line.strip() for line in output.splitlines()]
        return " ".join(line for line in lines if line)

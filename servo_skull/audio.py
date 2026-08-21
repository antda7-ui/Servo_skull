"""ALSA recording and playback adapter."""

from __future__ import annotations

import math
import subprocess
from pathlib import Path

from .config import AudioConfig


class AudioError(RuntimeError):
    """Base error for recoverable audio failures."""


class AudioExecutionError(AudioError):
    """An audio subprocess could not start or failed."""


class AudioTimeoutError(AudioError):
    """An audio subprocess exceeded its timeout."""


class AudioAdapter:
    def __init__(self, config: AudioConfig):
        self.config = config

    def build_record_command(self, output_path: Path, duration_seconds: float) -> list[str]:
        return [
            "arecord",
            "-D",
            self.config.device,
            "-f",
            "S16_LE",
            "-r",
            str(self.config.sample_rate),
            "-c",
            str(self.config.channels),
            "-d",
            str(math.ceil(duration_seconds)),
            str(output_path),
        ]

    def build_live_record_command(self, output_path: Path) -> list[str]:
        return [
            "arecord",
            "-D",
            self.config.device,
            "-f",
            "S16_LE",
            "-r",
            str(self.config.sample_rate),
            "-c",
            str(self.config.channels),
            str(output_path),
        ]

    def build_playback_command(self, audio_path: Path) -> list[str]:
        return ["aplay", "-D", self.config.device, str(audio_path)]

    def record(self, output_path: Path, duration_seconds: float) -> Path:
        if duration_seconds <= 0 or duration_seconds > self.config.max_recording_seconds:
            raise AudioError(
                f"Recording duration must be between 0 and "
                f"{self.config.max_recording_seconds:.1f} seconds"
            )
        self._run(
            self.build_record_command(output_path, duration_seconds),
            timeout=duration_seconds + 5.0,
        )
        return output_path

    def play(self, audio_path: Path) -> None:
        self._run(self.build_playback_command(audio_path), timeout=30.0)

    @staticmethod
    def _run(command: list[str], timeout: float) -> None:
        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as error:
            raise AudioTimeoutError(
                f"Audio command timed out after {timeout:.1f} seconds"
            ) from error
        except OSError as error:
            raise AudioExecutionError(
                f"Unable to start audio command {command[0]}: {error}"
            ) from error

        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
            raise AudioExecutionError(
                f"Audio command exited with status {result.returncode}: {detail}"
            )

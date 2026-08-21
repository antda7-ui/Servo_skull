"""Piper speech synthesis and SoX effects adapters."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .config import EffectsConfig, TtsConfig


class TtsError(RuntimeError):
    """Base error for recoverable speech synthesis failures."""


class TtsExecutionError(TtsError):
    """Piper or SoX could not start or returned a failure."""


class TtsTimeoutError(TtsError):
    """Piper or SoX exceeded its configured timeout."""


class PiperAdapter:
    def __init__(self, config: TtsConfig):
        self.config = config

    def build_command(self, output_path: Path) -> list[str]:
        return [
            str(self.config.executable),
            "--model",
            str(self.config.voice),
            "--output_file",
            str(output_path),
        ]

    def synthesize(self, text: str, output_path: Path) -> Path:
        if not text.strip():
            raise TtsError("Cannot synthesize empty text")
        try:
            result = subprocess.run(
                self.build_command(output_path),
                input=text,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds,
            )
        except subprocess.TimeoutExpired as error:
            raise TtsTimeoutError(
                f"Piper timed out after {self.config.timeout_seconds:.1f} seconds"
            ) from error
        except OSError as error:
            raise TtsExecutionError(
                f"Unable to start Piper executable {self.config.executable}: {error}"
            ) from error
        self._check_result("Piper", result)
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise TtsExecutionError("Piper produced no audio file")
        return output_path

    @staticmethod
    def _check_result(name: str, result: subprocess.CompletedProcess[str]) -> None:
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
            raise TtsExecutionError(
                f"{name} exited with status {result.returncode}: {detail}"
            )


class SoxEffectsAdapter:
    def __init__(self, config: EffectsConfig):
        self.config = config

    def build_command(self, input_path: Path, output_path: Path) -> list[str]:
        return [
            self.config.executable,
            str(input_path),
            str(output_path),
            *self.config.effects,
        ]

    def apply(self, input_path: Path, output_path: Path) -> Path:
        try:
            result = subprocess.run(
                self.build_command(input_path, output_path),
                check=False,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds,
            )
        except subprocess.TimeoutExpired as error:
            raise TtsTimeoutError(
                f"SoX timed out after {self.config.timeout_seconds:.1f} seconds"
            ) from error
        except OSError as error:
            raise TtsExecutionError(
                f"Unable to start SoX executable {self.config.executable}: {error}"
            ) from error
        PiperAdapter._check_result("SoX", result)
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise TtsExecutionError("SoX produced no audio file")
        return output_path
from pathlib import Path
import subprocess
from subprocess import CompletedProcess

import pytest

from servo_skull.config import WhisperConfig
from servo_skull.whisper import (
    WhisperAdapter,
    WhisperExecutionError,
    WhisperTimeoutError,
)


@pytest.fixture
def adapter():
    return WhisperAdapter(
        WhisperConfig(
            executable=Path("/opt/whisper-cli"),
            model=Path("/models/base.en.bin"),
            threads=4,
            timeout_seconds=12.0,
        )
    )


def test_build_command_uses_cpu_only_verified_options(adapter):
    assert adapter.build_command(Path("turn.wav")) == [
        "/opt/whisper-cli",
        "-m",
        "/models/base.en.bin",
        "-f",
        "turn.wav",
        "-l",
        "en",
        "-t",
        "4",
        "-ng",
        "-nt",
        "-np",
    ]


def test_transcribe_normalizes_successful_output(monkeypatch, adapter):
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return CompletedProcess(command, 0, "  First line.\n\nSecond line.  \n", "")

    monkeypatch.setattr("servo_skull.whisper.subprocess.run", fake_run)

    result = adapter.transcribe(Path("turn.wav"))

    assert result.text == "First line. Second line."
    assert calls[0][1]["timeout"] == 12.0
    assert calls[0][1]["capture_output"] is True


def test_transcribe_reports_process_failure(monkeypatch, adapter):
    monkeypatch.setattr(
        "servo_skull.whisper.subprocess.run",
        lambda command, **kwargs: CompletedProcess(command, 1, "", "model missing"),
    )

    with pytest.raises(WhisperExecutionError, match="model missing"):
        adapter.transcribe(Path("turn.wav"))


def test_transcribe_converts_subprocess_timeout(monkeypatch, adapter):
    def fake_run(command, **kwargs):
        raise subprocess.TimeoutExpired(command, 12.0)

    monkeypatch.setattr("servo_skull.whisper.subprocess.run", fake_run)

    with pytest.raises(WhisperTimeoutError, match="12.0 seconds"):
        adapter.transcribe(Path("turn.wav"))

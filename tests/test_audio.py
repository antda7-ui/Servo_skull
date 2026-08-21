from pathlib import Path
from subprocess import CompletedProcess

import pytest

from servo_skull.audio import AudioAdapter, AudioError, AudioExecutionError
from servo_skull.config import AudioConfig


@pytest.fixture
def adapter():
    return AudioAdapter(AudioConfig(device="default", max_recording_seconds=10.0))


def test_record_command_uses_whisper_compatible_wav_format(adapter):
    assert adapter.build_record_command(Path("turn.wav"), 3) == [
        "arecord", "-D", "default", "-f", "S16_LE", "-r", "16000", "-c", "1",
        "-d", "3", "turn.wav",
    ]


def test_playback_command_uses_configured_device(adapter):
    assert adapter.build_playback_command(Path("turn.wav")) == [
        "aplay", "-D", "default", "turn.wav",
    ]


def test_record_rejects_duration_over_limit(adapter):
    with pytest.raises(AudioError, match="between 0 and 10.0 seconds"):
        adapter.record(Path("turn.wav"), 11)


def test_record_reports_alsa_failure(monkeypatch, adapter):
    monkeypatch.setattr(
        "servo_skull.audio.subprocess.run",
        lambda command, **kwargs: CompletedProcess(command, 1, "", "no microphone"),
    )

    with pytest.raises(AudioExecutionError, match="no microphone"):
        adapter.record(Path("turn.wav"), 3)

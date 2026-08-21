from pathlib import Path
from subprocess import CompletedProcess

import pytest

from servo_skull.config import EffectsConfig, TtsConfig
from servo_skull.tts import PiperAdapter, SoxEffectsAdapter, TtsError, TtsExecutionError


def test_piper_command_uses_configured_voice_and_output():
    adapter = PiperAdapter(
        TtsConfig(executable=Path("/opt/piper"), voice=Path("/voices/alan.onnx"))
    )

    assert adapter.build_command(Path("clean.wav")) == [
        "/opt/piper", "--model", "/voices/alan.onnx", "--output_file", "clean.wav"
    ]


def test_piper_sends_text_to_stdin_and_returns_audio(monkeypatch, tmp_path):
    output_path = tmp_path / "clean.wav"

    def fake_run(command, **kwargs):
        assert kwargs["input"] == "Acknowledged."
        output_path.write_bytes(b"RIFF audio")
        return CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("servo_skull.tts.subprocess.run", fake_run)

    result = PiperAdapter(TtsConfig()).synthesize("Acknowledged.", output_path)

    assert result == output_path


def test_piper_rejects_empty_text(tmp_path):
    with pytest.raises(TtsError, match="empty text"):
        PiperAdapter(TtsConfig()).synthesize(" \n", tmp_path / "clean.wav")


def test_sox_command_is_structured_configuration():
    adapter = SoxEffectsAdapter(EffectsConfig(executable="sox", effects=("overdrive", "4")))

    assert adapter.build_command(Path("clean.wav"), Path("gritty.wav")) == [
        "sox", "clean.wav", "gritty.wav", "overdrive", "4"
    ]


def test_sox_applies_effects_and_returns_audio(monkeypatch, tmp_path):
    output_path = tmp_path / "gritty.wav"

    def fake_run(command, **kwargs):
        output_path.write_bytes(b"RIFF processed")
        return CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("servo_skull.tts.subprocess.run", fake_run)

    result = SoxEffectsAdapter(EffectsConfig()).apply(tmp_path / "clean.wav", output_path)

    assert result == output_path


def test_tts_reports_subprocess_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "servo_skull.tts.subprocess.run",
        lambda command, **kwargs: CompletedProcess(command, 1, "", "voice missing"),
    )

    with pytest.raises(TtsExecutionError, match="voice missing"):
        PiperAdapter(TtsConfig()).synthesize("Speak.", tmp_path / "clean.wav")
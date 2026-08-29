from pathlib import Path

from servo_skull.config import AppConfig, OllamaConfig, WhisperConfig


def test_ollama_config_defaults_are_faster_for_cpu_usage():
    config = OllamaConfig()

    assert config.max_history_turns == 2
    assert config.max_response_tokens == 48


def test_app_config_uses_fast_voice_profile_when_requested():
    config = AppConfig.from_environment(fast_mode=True)

    assert config.ollama.max_history_turns == 2
    assert config.ollama.max_response_tokens == 32
    assert config.ollama.timeout_seconds == 60.0


def test_whisper_config_defaults_to_verified_local_installation():
    config = WhisperConfig()

    assert config.executable == Path.home() / "whisper.cpp/build/bin/whisper-cli"
    assert config.model == Path.home() / "whisper.cpp/models/ggml-base.en.bin"
    assert config.threads == 4


def test_whisper_config_reads_environment(monkeypatch):
    monkeypatch.setenv("SERVO_SKULL_WHISPER_EXECUTABLE", "/opt/whisper-cli")
    monkeypatch.setenv("SERVO_SKULL_WHISPER_MODEL", "/models/custom.bin")
    monkeypatch.setenv("SERVO_SKULL_WHISPER_THREADS", "2")
    monkeypatch.setenv("SERVO_SKULL_WHISPER_TIMEOUT", "45.5")
    monkeypatch.setenv("SERVO_SKULL_AUDIO_DEVICE", "hw:USB,0")
    monkeypatch.setenv("SERVO_SKULL_AUDIO_SAMPLE_RATE", "8000")
    monkeypatch.setenv("SERVO_SKULL_AUDIO_CHANNELS", "2")
    monkeypatch.setenv("SERVO_SKULL_MAX_RECORDING_SECONDS", "15.0")

    config = AppConfig.from_environment()

    assert config.whisper.executable == Path("/opt/whisper-cli")
    assert config.whisper.model == Path("/models/custom.bin")
    assert config.whisper.threads == 2
    assert config.whisper.timeout_seconds == 45.5
    assert config.audio.device == "hw:USB,0"
    assert config.audio.sample_rate == 8000
    assert config.audio.channels == 2
    assert config.audio.max_recording_seconds == 15.0

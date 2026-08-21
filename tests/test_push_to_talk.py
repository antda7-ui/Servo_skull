from pathlib import Path
import threading
import wave

import pytest

from servo_skull.audio import AudioAdapter
from servo_skull.config import AudioConfig
from servo_skull.push_to_talk import (
    EmptyRecordingError,
    PushToTalkError,
    PushToTalkRecorder,
)


def write_wav(path: Path, frames: int) -> None:
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(b"\0\0" * frames)


class FakeProcess:
    def __init__(self, command, **kwargs):
        self.command = command
        self.returncode = 0
        self.stderr = None
        self.terminated = False

    def poll(self):
        return None if not self.terminated else self.returncode

    def terminate(self):
        self.terminated = True

    def send_signal(self, signal):
        self.terminated = True

    def wait(self, timeout=None):
        self.terminated = True
        return self.returncode

    def kill(self):
        self.terminated = True

    def communicate(self, timeout=None):
        self.terminated = True
        return "", self.stderr or ""


def make_recorder(input_fn, process_factory):
    return PushToTalkRecorder(
        AudioAdapter(AudioConfig(max_recording_seconds=30.0)),
        input_fn=input_fn,
        process_factory=process_factory,
    )


def test_capture_starts_and_stops_arecord_on_enter(tmp_path):
    processes = []

    def process_factory(command, **kwargs):
        process = FakeProcess(command, **kwargs)
        processes.append(process)
        write_wav(tmp_path / "turn.wav", 160)
        return process

    recorder = make_recorder(lambda _: "", process_factory)

    result = recorder.capture(tmp_path / "turn.wav")

    assert result == tmp_path / "turn.wav"
    assert processes[0].command[-1] == str(tmp_path / "turn.wav")
    assert processes[0].terminated is True


def test_ctrl_c_before_start_cancels_cleanly(tmp_path):
    def cancel(_):
        raise KeyboardInterrupt

    recorder = make_recorder(cancel, lambda *args, **kwargs: pytest.fail("not started"))

    assert recorder.capture(tmp_path / "turn.wav") is None


def test_empty_recording_is_rejected(tmp_path):
    def process_factory(command, **kwargs):
        write_wav(tmp_path / "turn.wav", 0)
        return FakeProcess(command, **kwargs)

    recorder = make_recorder(lambda _: "", process_factory)

    with pytest.raises(EmptyRecordingError, match="no audio"):
        recorder.capture(tmp_path / "turn.wav")


def test_ctrl_c_while_recording_stops_process(tmp_path):
    process = None

    def process_factory(command, **kwargs):
        nonlocal process
        process = FakeProcess(command, **kwargs)
        write_wav(tmp_path / "turn.wav", 160)
        return process

    calls = 0

    def stop_on_second_prompt(_):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise KeyboardInterrupt
        return ""

    recorder = make_recorder(stop_on_second_prompt, process_factory)

    assert recorder.capture(tmp_path / "turn.wav") is None
    assert process is not None and process.terminated is True


def test_recording_timeout_stops_and_reports_limit(tmp_path):
    process = None

    def process_factory(command, **kwargs):
        nonlocal process
        process = FakeProcess(command, **kwargs)
        return process

    recorder = PushToTalkRecorder(
        AudioAdapter(AudioConfig(max_recording_seconds=0.01)),
        input_fn=lambda _: threading.Event().wait(1),
        process_factory=process_factory,
    )

    with pytest.raises(PushToTalkError, match="exceeded 0.0 seconds"):
        recorder.capture(tmp_path / "turn.wav")
    assert process is not None and process.terminated is True


def test_existing_output_is_removed_before_recording(tmp_path):
    output_path = tmp_path / "turn.wav"
    write_wav(output_path, 160)

    recorder = make_recorder(
        lambda _: "",
        lambda command, **kwargs: FakeProcess(command, **kwargs),
    )

    with pytest.raises(EmptyRecordingError, match="no audio"):
        recorder.capture(output_path)


def test_arecord_interrupt_status_is_success_when_audio_exists(tmp_path):
    def process_factory(command, **kwargs):
        process = FakeProcess(command, **kwargs)
        process.returncode = 1
        process.stderr = "Recording WAVE ...\nAborted by signal Interrupt..."
        write_wav(tmp_path / "turn.wav", 160)
        return process

    recorder = make_recorder(lambda _: "", process_factory)

    assert recorder.capture(tmp_path / "turn.wav") == tmp_path / "turn.wav"

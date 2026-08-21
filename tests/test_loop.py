from pathlib import Path

from servo_skull.loop import VoiceLoop


class FakeRecorder:
    def capture(self, path):
        path.write_bytes(b"recording")
        return path


class FakeWhisper:
    class Result:
        text = "What is the status?"

    def transcribe(self, path):
        return self.Result()


class FakeOllama:
    class Result:
        text = "All local systems are ready."

    def chat(self, text):
        return self.Result()


class FakePiper:
    def synthesize(self, text, path):
        path.write_bytes(b"clean")
        return path


class FakeEffects:
    def apply(self, input_path, output_path):
        output_path.write_bytes(b"processed")
        return output_path


class FakeAudio:
    def __init__(self):
        self.played = None

    def play(self, path):
        self.played = path


def make_loop(status, audio, debug_directory=None, effects_enabled=True):
    return VoiceLoop(
        FakeRecorder(),
        FakeWhisper(),
        FakeOllama(),
        FakePiper(),
        FakeEffects(),
        audio,
        status=status.append,
        debug_directory=debug_directory,
        effects_enabled=effects_enabled,
    )


def test_run_turn_executes_all_stages_and_cleans_temporary_files(tmp_path):
    status = []
    audio = FakeAudio()

    result = make_loop(status, audio).run_turn()

    assert result.transcript == "What is the status?"
    assert result.response == "All local systems are ready."
    assert result.audio_path is None
    assert audio.played is not None
    assert status == [
        "Waiting for speech...",
        "Transcribing...",
        "Thinking...",
        "Synthesizing...",
        "Applying audio effects...",
        "Playing...",
    ]


def test_debug_mode_preserves_final_audio(tmp_path):
    status = []
    audio = FakeAudio()

    result = make_loop(status, audio, debug_directory=tmp_path).run_turn()

    assert result.audio_path is not None
    assert result.audio_path.exists()
    assert result.audio_path.read_bytes() == b"processed"


def test_clean_voice_skips_effects(tmp_path):
    status = []
    audio = FakeAudio()

    result = make_loop(status, audio, debug_directory=tmp_path, effects_enabled=False).run_turn()

    assert result.audio_path is not None
    assert result.audio_path.name == "response-clean.wav"
    assert "Applying audio effects..." not in status
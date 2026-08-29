from pathlib import Path

from servo_skull.run import main


def test_voice_loop_cli_exits_cleanly_on_keyboard_interrupt(monkeypatch, capsys):
    class InterruptingLoop:
        def __init__(self, *args, **kwargs):
            pass

        def run_turn(self):
            raise KeyboardInterrupt

    monkeypatch.setattr("servo_skull.run.VoiceLoop", InterruptingLoop)
    monkeypatch.setattr("servo_skull.run.PushToTalkRecorder", lambda *args, **kwargs: None)
    monkeypatch.setattr("servo_skull.run.WhisperAdapter", lambda *args: None)
    monkeypatch.setattr("servo_skull.run.OllamaAdapter", lambda *args: None)
    monkeypatch.setattr("servo_skull.run.PiperAdapter", lambda *args: None)
    monkeypatch.setattr("servo_skull.run.SoxEffectsAdapter", lambda *args: None)

    monkeypatch.setattr("sys.argv", ["servo-skull"])

    assert main() == 0
    assert "Shutting down." in capsys.readouterr().out
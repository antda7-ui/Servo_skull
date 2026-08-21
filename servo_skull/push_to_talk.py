"""Enter-key push-to-talk recording boundary."""

from __future__ import annotations

import subprocess
import signal
import threading
import wave
from pathlib import Path
from typing import Callable

from .audio import AudioAdapter, AudioError, AudioExecutionError


class PushToTalkError(AudioError):
    """Base error for push-to-talk failures."""


class EmptyRecordingError(PushToTalkError):
    """The recording contains no audio beyond its WAV header."""


class PushToTalkRecorder:
    def __init__(
        self,
        audio: AudioAdapter,
        input_fn: Callable[[str], str] = input,
        process_factory: Callable[..., subprocess.Popen] = subprocess.Popen,
    ):
        self.audio = audio
        self.input_fn = input_fn
        self.process_factory = process_factory

    def capture(self, output_path: Path) -> Path | None:
        process = None
        timer = None
        cancelled = False
        timed_out = False
        try:
            self.input_fn("Press Enter to start recording (Ctrl-C to cancel): ")
            output_path.unlink(missing_ok=True)
            process = self.process_factory(
                self.audio.build_live_record_command(output_path),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            stop_requested = threading.Event()
            input_error: list[BaseException] = []

            def wait_for_stop() -> None:
                try:
                    self.input_fn("Recording. Press Enter to stop: ")
                except BaseException as error:
                    input_error.append(error)
                finally:
                    stop_requested.set()

            input_thread = threading.Thread(target=wait_for_stop, daemon=True)
            input_thread.start()
            if not stop_requested.wait(self.audio.config.max_recording_seconds):
                timed_out = True
            if input_error and isinstance(input_error[0], KeyboardInterrupt):
                cancelled = True
        except KeyboardInterrupt:
            cancelled = True
        finally:
            stderr = ""
            if process is not None:
                stderr = self._stop_process(process)

        if cancelled or process is None:
            return None
        has_audio = self._has_audio_frames(output_path)
        interrupted_normally = (
            process.returncode == 1 and "Aborted by signal Interrupt" in stderr
        )
        if process.returncode not in (0, -signal.SIGINT) and not interrupted_normally:
            raise AudioExecutionError(
                f"Recording failed with status {process.returncode}: "
                f"{stderr or 'unknown error'}"
            )
        if timed_out:
            raise PushToTalkError(
                f"Recording exceeded {self.audio.config.max_recording_seconds:.1f} seconds"
            )
        if not has_audio:
            raise EmptyRecordingError("Recording contains no audio")
        return output_path

    @staticmethod
    def _has_audio_frames(audio_path: Path) -> bool:
        try:
            with wave.open(str(audio_path), "rb") as wav_file:
                return wav_file.getnframes() > 0
        except (OSError, wave.Error):
            return False

    @staticmethod
    def _stop_process(process: subprocess.Popen) -> str:
        if process.poll() is None:
            PushToTalkRecorder._request_stop(process)
        try:
            _, stderr = process.communicate(timeout=5.0)
        except subprocess.TimeoutExpired:
            process.kill()
            _, stderr = process.communicate()
        return (stderr or "").strip()

    @staticmethod
    def _request_stop(process: subprocess.Popen) -> None:
        if process.poll() is None:
            process.send_signal(signal.SIGINT)

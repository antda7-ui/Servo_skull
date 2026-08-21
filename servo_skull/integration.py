"""Opt-in local integration checks for the Phase 1 voice pipeline."""

from __future__ import annotations

import argparse
import tempfile
import time
from pathlib import Path

from .audio import AudioAdapter
from .config import AppConfig
from .ollama import OllamaAdapter
from .push_to_talk import PushToTalkRecorder
from .tts import PiperAdapter, SoxEffectsAdapter
from .whisper import WhisperAdapter


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local voice-pipeline integration checks")
    parser.add_argument(
        "--sample",
        type=Path,
        default=Path.home() / "whisper.cpp/samples/jfk.wav",
        help="WAV to use instead of recording from the microphone",
    )
    parser.add_argument(
        "--record",
        action="store_true",
        help="capture a push-to-talk recording instead of using --sample",
    )
    parser.add_argument("--no-playback", action="store_true", help="skip speaker playback")
    parser.add_argument("--debug", action="store_true", help="preserve generated WAV files")
    args = parser.parse_args()

    config = AppConfig.from_environment()
    audio = AudioAdapter(config.audio)
    temporary_directory = None
    try:
        timings: dict[str, float] = {}
        started = time.perf_counter()
        if args.debug:
            artifact_directory = Path.cwd() / "integration-artifacts"
            artifact_directory.mkdir(parents=True, exist_ok=True)
            turn_directory = Path(tempfile.mkdtemp(prefix="check-", dir=artifact_directory))
        else:
            temporary_directory = tempfile.TemporaryDirectory(prefix="servo-skull-integration-")
            turn_directory = Path(temporary_directory.name)

        if args.record:
            print("[1/5] Recording from the default ALSA device...")
            stage_started = time.perf_counter()
            input_path = PushToTalkRecorder(audio).capture(turn_directory / "recording.wav")
            timings["recording"] = time.perf_counter() - stage_started
            if input_path is None:
                print("Integration check cancelled.")
                return 0
        else:
            input_path = args.sample
            if not input_path.exists():
                print(f"Integration check failed: sample does not exist: {input_path}")
                return 1
            print(f"[1/5] Using sample: {input_path}")

        print("[2/5] Transcribing with Whisper...")
        stage_started = time.perf_counter()
        transcript = WhisperAdapter(config.whisper).transcribe(input_path).text.strip()
        timings["whisper"] = time.perf_counter() - stage_started
        if not transcript:
            print("Integration check failed: Whisper returned no speech")
            return 1
        print(f"Transcript: {transcript}")

        print("[3/5] Generating response with Ollama...")
        stage_started = time.perf_counter()
        response = OllamaAdapter(config.ollama).chat(transcript).text.strip()
        timings["ollama"] = time.perf_counter() - stage_started
        print(f"Response: {response}")

        print("[4/5] Synthesizing and applying SoX effects...")
        stage_started = time.perf_counter()
        clean_path = PiperAdapter(config.tts).synthesize(response, turn_directory / "clean.wav")
        output_path = SoxEffectsAdapter(config.effects).apply(
            clean_path, turn_directory / "processed.wav"
        )
        timings["tts_and_effects"] = time.perf_counter() - stage_started

        if args.no_playback:
            print("[5/5] Playback skipped.")
        else:
            print("[5/5] Playing processed response...")
            stage_started = time.perf_counter()
            audio.play(output_path)
            timings["playback"] = time.perf_counter() - stage_started
        timings["total"] = time.perf_counter() - started
        print("Timing: " + ", ".join(f"{name}={duration:.2f}s" for name, duration in timings.items()))
        print(f"Integration check passed: {output_path}")
        return 0
    except Exception as error:
        print(f"Integration check failed: {error}")
        return 1
    finally:
        if temporary_directory is not None:
            temporary_directory.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
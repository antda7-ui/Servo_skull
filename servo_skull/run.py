"""Command-line entry point for the Phase 1 voice loop."""

from __future__ import annotations

import argparse
from pathlib import Path

from .audio import AudioAdapter
from .config import AppConfig
from .loop import VoiceLoop
from .ollama import OllamaAdapter
from .push_to_talk import PushToTalkRecorder
from .tts import PiperAdapter, SoxEffectsAdapter
from .whisper import WhisperAdapter


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local servo skull voice loop")
    parser.add_argument("--debug", action="store_true", help="preserve per-turn audio artifacts")
    parser.add_argument(
        "--clean-voice", action="store_true", help="skip the configured SoX effects"
    )
    parser.add_argument(
        "--fast-mode",
        action="store_true",
        help="reduce reply length and context for lower-latency CPU-only responses",
    )
    parser.add_argument(
        "--debug-directory", type=Path, default=Path("debug-artifacts")
    )
    args = parser.parse_args()

    config = AppConfig.from_environment(fast_mode=args.fast_mode)
    audio = AudioAdapter(config.audio)
    loop = VoiceLoop(
        recorder=PushToTalkRecorder(audio, propagate_interrupt=True),
        whisper=WhisperAdapter(config.whisper),
        ollama=OllamaAdapter(config.ollama),
        piper=PiperAdapter(config.tts),
        effects=SoxEffectsAdapter(config.effects),
        audio=audio,
        effects_enabled=not args.clean_voice,
        debug_directory=args.debug_directory if args.debug else None,
    )
    print("Servo skull voice loop ready. Press Ctrl-C to exit.")
    try:
        while True:
            try:
                loop.run_turn()
            except Exception as error:  # keep one failed turn from ending the loop
                print(f"Turn failed: {error}")
    except KeyboardInterrupt:
        print("Shutting down.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
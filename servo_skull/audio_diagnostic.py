"""Command-line ALSA recording and playback diagnostic."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from .audio import AudioAdapter, AudioError
from .config import AppConfig


def main() -> int:
    parser = argparse.ArgumentParser(description="Test the default ALSA microphone and playback")
    parser.add_argument("--duration", type=float, default=3.0)
    parser.add_argument("--keep", action="store_true", help="keep the recorded WAV file")
    args = parser.parse_args()

    config = AppConfig.from_environment()
    adapter = AudioAdapter(config.audio)
    temporary_directory = None
    try:
        if args.keep:
            output_path = Path.cwd() / "audio-diagnostic.wav"
        else:
            temporary_directory = tempfile.TemporaryDirectory(prefix="servo-skull-audio-")
            output_path = Path(temporary_directory.name) / "recording.wav"
        print(f"Recording {args.duration:.1f} seconds from ALSA device '{config.audio.device}'...")
        adapter.record(output_path, args.duration)
        print(f"Recorded {output_path.stat().st_size} bytes.")
        print("Playing recording...")
        adapter.play(output_path)
        print("Audio diagnostic passed.")
        return 0
    except AudioError as error:
        print(f"Audio diagnostic failed: {error}")
        return 1
    finally:
        if temporary_directory is not None:
            temporary_directory.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())

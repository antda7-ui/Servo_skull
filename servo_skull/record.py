"""Command-line push-to-talk recording check."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from .audio import AudioAdapter, AudioError
from .config import AppConfig
from .push_to_talk import PushToTalkRecorder


def main() -> int:
    parser = argparse.ArgumentParser(description="Record one push-to-talk WAV")
    parser.add_argument("--keep", action="store_true", help="keep the recorded WAV file")
    args = parser.parse_args()
    config = AppConfig.from_environment()
    temporary_directory = None
    try:
        if args.keep:
            output_path = Path.cwd() / "recording.wav"
        else:
            temporary_directory = tempfile.TemporaryDirectory(prefix="servo-skull-record-")
            output_path = Path(temporary_directory.name) / "recording.wav"
        result = PushToTalkRecorder(AudioAdapter(config.audio)).capture(output_path)
        if result is None:
            print("Recording cancelled.")
            return 0
        print(f"Recording saved to {result}")
        return 0
    except AudioError as error:
        print(f"Recording failed: {error}")
        return 1
    finally:
        if temporary_directory is not None:
            temporary_directory.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())

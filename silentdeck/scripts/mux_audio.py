#!/usr/bin/env python3
"""Mux a generated narration audio track into a source MP4."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from silentdeck_core.env import get_setting, load_env
from silentdeck_core.media import mux_audio, require_binary


def main() -> int:
    parser = argparse.ArgumentParser(description="Mux narration audio into a source MP4.")
    parser.add_argument("video", type=Path)
    parser.add_argument("audio", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--env", type=Path, default=Path(".env"), help="Path to .env.")
    args = parser.parse_args()

    if not args.video.exists():
        raise SystemExit(f"Video not found: {args.video}")
    if not args.audio.exists():
        raise SystemExit(f"Audio not found: {args.audio}")

    env = load_env(args.env)
    ffmpeg = require_binary("ffmpeg", get_setting(env, "SILENTDECK_FFMPEG_PATH"), "SILENTDECK_FFMPEG_PATH")
    mux_audio(ffmpeg, args.video, args.audio, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Run the SilentDeck provider-backed pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from silentdeck_core.pipeline import run_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the SilentDeck provider-backed pipeline.")
    parser.add_argument("input", type=Path, help="Silent presentation MP4.")
    parser.add_argument("--out", type=Path, required=True, help="Output directory.")
    parser.add_argument("--env", type=Path, default=Path(".env"), help="Path to .env.")
    parser.add_argument("--lang", default=None, help="Narration language.")
    parser.add_argument("--segment-sec", type=float, default=None, help="Maximum segment length in seconds.")
    parser.add_argument("--scene-threshold", type=float, default=None, help="FFmpeg scene-detection threshold.")
    parser.add_argument("--no-vlm", action="store_true", help="Skip VLM keyframe analysis and write a manual-review script skeleton.")
    parser.add_argument("--manual-script", type=Path, help="Use an existing script.md or segments.json and skip VLM/text generation.")
    parser.add_argument("--tts-only", action="store_true", help="Build audio/video from --manual-script or OUT/script.md.")
    parser.add_argument("--tts-chain", help="Comma-separated TTS chain. Default: siliconflow,edge,sapi.")
    parser.add_argument("--vision-model", help="Override the VLM model ID.")
    parser.add_argument("--text-model", help="Override the narration model ID.")
    parser.add_argument("--tts-model", help="Override the TTS model ID.")
    parser.add_argument("--tts-voice", help="Override the TTS voice ID.")
    parser.add_argument("--edge-voice", help="Override edge-tts voice.")
    parser.add_argument("--sapi-voice", help="Override Windows SAPI voice.")
    parser.add_argument("--subtitle", action="store_true", help="Generate subtitles.srt.")
    parser.add_argument("--max-segments", type=int, help="Limit the number of segments.")
    args = parser.parse_args()
    run_pipeline(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())

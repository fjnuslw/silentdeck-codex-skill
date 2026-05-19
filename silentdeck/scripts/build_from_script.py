#!/usr/bin/env python3
"""Build narrated and subtitled MP4 outputs from an existing script."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from silentdeck_core.builder import build_from_script


def main() -> int:
    parser = argparse.ArgumentParser(description="Build SilentDeck outputs from script.md or segments.json.")
    parser.add_argument("input", type=Path, help="Source MP4.")
    parser.add_argument("script", type=Path, help="script.md or segments.json.")
    parser.add_argument("--out", type=Path, required=True, help="Output directory.")
    parser.add_argument("--env", type=Path, default=Path(".env"), help="Path to .env.")
    parser.add_argument("--lang", default=None, help="Narration language.")
    parser.add_argument("--tts-chain", help="Comma-separated TTS chain. Default: siliconflow,edge,sapi.")
    parser.add_argument("--tts-model", help="Override the provider TTS model ID.")
    parser.add_argument("--tts-voice", help="Override the provider TTS voice ID.")
    parser.add_argument("--edge-voice", help="Override edge-tts voice.")
    parser.add_argument("--sapi-voice", help="Override Windows SAPI voice.")
    parser.add_argument("--no-subtitle", action="store_true", help="Skip SRT and subtitled MP4 outputs.")
    args = parser.parse_args()

    summary = build_from_script(
        input_video=args.input,
        script_path=args.script,
        output_dir=args.out,
        env_path=args.env,
        lang=args.lang,
        subtitle=not args.no_subtitle,
        tts_chain=args.tts_chain,
        tts_model=args.tts_model,
        tts_voice=args.tts_voice,
        edge_voice=args.edge_voice,
        sapi_voice=args.sapi_voice,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Create a compact review pack for Codex-assisted SilentDeck analysis."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from silentdeck_core.env import get_setting, load_env
from silentdeck_core.media import require_binary
from silentdeck_core.review import prepare_review_pack


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a Codex review pack from SilentDeck outputs.")
    parser.add_argument("output", type=Path, help="SilentDeck output directory.")
    parser.add_argument("--cols", type=int, default=3)
    parser.add_argument("--rows", type=int, default=3)
    parser.add_argument("--thumb-width", type=int, default=426)
    parser.add_argument("--max-sheets", type=int, default=4)
    parser.add_argument("--env", type=Path, default=Path(".env"), help="Path to .env.")
    args = parser.parse_args()

    if not args.output.exists():
        raise SystemExit(f"Output directory not found: {args.output}")

    env = load_env(args.env)
    ffmpeg = require_binary("ffmpeg", get_setting(env, "SILENTDECK_FFMPEG_PATH"), "SILENTDECK_FFMPEG_PATH")
    summary = prepare_review_pack(args.output, args.cols, args.rows, args.thumb_width, args.max_sheets, ffmpeg)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

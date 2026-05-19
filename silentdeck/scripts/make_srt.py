#!/usr/bin/env python3
"""Create SRT subtitles from SilentDeck JSON or markdown script data."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from silentdeck_core.documents import parse_json_segments, parse_markdown, write_srt


def main() -> int:
    parser = argparse.ArgumentParser(description="Create SRT subtitles from SilentDeck script data.")
    parser.add_argument("input", type=Path, help="script.md or JSON segment file.")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Input not found: {args.input}")

    segments = parse_json_segments(args.input) if args.input.suffix.lower() == ".json" else parse_markdown(args.input)
    if not segments:
        raise SystemExit("No segments found.")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_srt(segments, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

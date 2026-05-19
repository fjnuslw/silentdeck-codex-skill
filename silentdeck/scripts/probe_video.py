#!/usr/bin/env python3
"""Probe MP4 metadata and basic audio volume."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from silentdeck_core.env import get_setting, load_env
from silentdeck_core.media import probe_video


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe MP4 metadata.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--env", type=Path, default=Path(".env"), help="Path to .env.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Input not found: {args.input}")

    env = load_env(args.env)
    ffprobe = get_setting(env, "SILENTDECK_FFPROBE_PATH")
    report = probe_video(args.input, ffprobe)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        for key, value in report.items():
            print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

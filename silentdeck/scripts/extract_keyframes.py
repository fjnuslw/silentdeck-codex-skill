#!/usr/bin/env python3
"""Extract representative keyframes for SilentDeck segments."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from silentdeck_core.env import get_setting, load_env
from silentdeck_core.media import extract_keyframe, probe_video, require_binary
from silentdeck_core.scene import build_segments


def load_segments(timeline: Path) -> list[dict[str, Any]]:
    data = json.loads(timeline.read_text(encoding="utf-8"))
    segments = data.get("segments", data if isinstance(data, list) else [])
    if not isinstance(segments, list):
        raise SystemExit("Timeline must contain a segments list.")
    return segments


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract representative keyframes.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--env", type=Path, default=Path(".env"), help="Path to .env.")
    parser.add_argument("--timeline", type=Path, help="timeline.json with segment start/end values.")
    parser.add_argument("--out", type=Path, required=True, help="Output keyframe directory.")
    parser.add_argument("--duration", type=float, help="Video duration for fixed sampling mode.")
    parser.add_argument("--every-sec", type=float, default=30.0, help="Fixed sample interval when no timeline is given.")
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Input not found: {args.input}")

    env = load_env(args.env)
    ffmpeg = require_binary("ffmpeg", get_setting(env, "SILENTDECK_FFMPEG_PATH"), "SILENTDECK_FFMPEG_PATH")

    if args.timeline:
        segments = load_segments(args.timeline)
    else:
        if args.duration is None:
            ffprobe = require_binary("ffprobe", get_setting(env, "SILENTDECK_FFPROBE_PATH"), "SILENTDECK_FFPROBE_PATH")
            video = probe_video(args.input, ffprobe)
            args.duration = float(video["duration_sec"])
        segments = build_segments(float(args.duration), [], args.every_sec)

    results = []
    for index, segment in enumerate(segments, start=1):
        segment_id = str(segment.get("id") or f"seg_{index:04d}")
        start = float(segment["start"])
        end = float(segment["end"])
        timestamp = start + max((end - start) / 2.0, 0.0)
        output = args.out / f"{segment_id}.jpg"
        extract_keyframe(ffmpeg, args.input, timestamp, output)
        results.append({"id": segment_id, "timestamp": timestamp, "keyframe": str(output)})

    print(json.dumps({"keyframes": results}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

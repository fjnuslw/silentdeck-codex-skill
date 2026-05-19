"""Scene and segment helpers for SilentDeck scripts."""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

from .media import require_binary, run_command


SCENE_TIME_RE = re.compile(r"pts_time:(?P<time>\d+(?:\.\d+)?)")


def detect_scene_changes(video_path: Path, threshold: float = 0.28, ffmpeg: str | None = None) -> list[float]:
    ffmpeg = ffmpeg or require_binary("ffmpeg", env_var="SILENTDECK_FFMPEG_PATH")
    result = run_command(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "info",
            "-i",
            str(video_path),
            "-vf",
            f"select='gt(scene,{threshold})',showinfo",
            "-f",
            "null",
            "-",
        ]
    )
    text = f"{result.stdout}\n{result.stderr}"
    times: list[float] = []
    for line in text.splitlines():
        match = SCENE_TIME_RE.search(line)
        if match:
            times.append(round(float(match.group("time")), 3))
    return sorted(set(times))


def build_segments(duration: float, scene_times: list[float], max_segment_sec: float) -> list[dict[str, Any]]:
    boundaries = [0.0]
    for time in sorted(set(scene_times)):
        if 0.05 < time < duration - 0.05:
            boundaries.append(time)
    boundaries.append(duration)
    boundaries = sorted(set(round(value, 3) for value in boundaries))

    chunks: list[tuple[float, float]] = []
    for start, end in zip(boundaries, boundaries[1:]):
        if end - start <= 0.05:
            continue
        span = end - start
        if span <= max_segment_sec:
            chunks.append((start, end))
            continue
        parts = max(1, math.ceil(span / max_segment_sec))
        for index in range(parts):
            part_start = start + (span * index / parts)
            part_end = start + (span * (index + 1) / parts)
            chunks.append((round(part_start, 3), round(part_end, 3)))

    return [
        {
            "id": f"seg_{index:04d}",
            "start": round(start, 3),
            "end": round(end, 3),
        }
        for index, (start, end) in enumerate(chunks, start=1)
    ]

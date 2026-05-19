"""Agent review pack helpers for SilentDeck."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .documents import format_display_time
from .media import require_binary, run_command


def load_timeline(output_dir: Path) -> list[dict[str, Any]]:
    timeline_path = output_dir / "assets" / "timeline.json"
    if not timeline_path.exists():
        return []
    data = json.loads(timeline_path.read_text(encoding="utf-8"))
    segments = data.get("segments", [])
    return segments if isinstance(segments, list) else []


def find_keyframes(output_dir: Path) -> list[Path]:
    keyframe_dir = output_dir / "assets" / "keyframes"
    if not keyframe_dir.exists():
        return []
    return sorted(keyframe_dir.glob("*.jpg"))


def cell_name(index: int, cols: int, rows: int) -> tuple[int, str]:
    per_sheet = cols * rows
    sheet = index // per_sheet + 1
    cell = index % per_sheet
    row = cell // cols + 1
    col = cell % cols + 1
    return sheet, f"r{row}c{col}"


def make_contact_sheets(
    keyframes: list[Path],
    review_dir: Path,
    cols: int,
    rows: int,
    thumb_width: int,
    max_sheets: int,
    ffmpeg: str | None = None,
) -> list[Path]:
    ffmpeg = ffmpeg or require_binary("ffmpeg", env_var="SILENTDECK_FFMPEG_PATH")
    if not keyframes:
        return []

    staged = review_dir / "frames"
    staged.mkdir(parents=True, exist_ok=True)
    max_frames = cols * rows * max_sheets
    selected = keyframes[:max_frames]
    for index, frame in enumerate(selected, start=1):
        shutil.copy2(frame, staged / f"frame_{index:04d}.jpg")

    result = run_command(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-framerate",
            "1",
            "-start_number",
            "1",
            "-i",
            str(staged / "frame_%04d.jpg"),
            "-vf",
            f"scale={thumb_width}:-1,tile={cols}x{rows}:padding=8:margin=8",
            "-frames:v",
            str(max_sheets),
            str(review_dir / "contact_sheet_%03d.jpg"),
        ]
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "Failed to build contact sheets")
    return sorted(review_dir.glob("contact_sheet_*.jpg"))


def write_review_markdown(
    review_dir: Path,
    segments: list[dict[str, Any]],
    keyframes: list[Path],
    sheets: list[Path],
    cols: int,
    rows: int,
) -> Path:
    review_path = review_dir / "agent_review.md"
    lines = [
        "# SilentDeck Agent Review Pack",
        "",
        "Use this pack for Codex-assisted analysis. Inspect contact sheets first, then open individual keyframes only when needed.",
        "",
        "## Contact Sheets",
        "",
    ]

    if sheets:
        for sheet in sheets:
            lines.append(f"- {sheet.resolve()}")
    else:
        lines.append("- No contact sheets were generated.")

    lines.extend(
        [
            "",
            "Frame order in each sheet is left-to-right, top-to-bottom.",
            "",
            "## Segment Map",
            "",
            "| Sheet | Cell | Segment | Time | Keyframe |",
            "| --- | --- | --- | --- | --- |",
        ]
    )

    by_id = {str(segment.get("id")): segment for segment in segments}
    for index, frame in enumerate(keyframes, start=0):
        segment_id = frame.stem
        segment = by_id.get(segment_id, {})
        start = segment.get("start")
        end = segment.get("end")
        if isinstance(start, (int, float)) and isinstance(end, (int, float)):
            time_range = f"{format_display_time(float(start))} -> {format_display_time(float(end))}"
        else:
            time_range = ""
        sheet, cell = cell_name(index, cols, rows)
        lines.append(f"| {sheet} | {cell} | {segment_id} | {time_range} | {frame.resolve()} |")

    lines.extend(
        [
            "",
            "## Agent Task",
            "",
            "1. Identify visible text and important visual content.",
            "2. Write concise visual notes for each segment.",
            "3. Write short Chinese narration aligned to each segment duration.",
            "4. Avoid facts that are not visible or strongly implied.",
            "5. Keep subtitles short enough to avoid covering important UI areas.",
        ]
    )
    review_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return review_path


def prepare_review_pack(
    output_dir: Path,
    cols: int = 3,
    rows: int = 3,
    thumb_width: int = 426,
    max_sheets: int = 4,
    ffmpeg: str | None = None,
) -> dict[str, Any]:
    review_dir = output_dir / "assets" / "agent_review"
    review_dir.mkdir(parents=True, exist_ok=True)
    segments = load_timeline(output_dir)
    keyframes = find_keyframes(output_dir)
    if not keyframes:
        raise SystemExit(f"No keyframes found under {output_dir / 'assets' / 'keyframes'}")
    selected_keyframes = keyframes[: cols * rows * max_sheets]
    sheets = make_contact_sheets(selected_keyframes, review_dir, cols, rows, thumb_width, max_sheets, ffmpeg)
    review_path = write_review_markdown(review_dir, segments, selected_keyframes, sheets, cols, rows)
    return {
        "review": str(review_path),
        "contact_sheets": [str(sheet) for sheet in sheets],
        "keyframes": len(selected_keyframes),
        "total_keyframes": len(keyframes),
    }

"""Document writers and parsers for SilentDeck scripts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def format_display_time(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours, remainder = divmod(millis, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, ms = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"


def format_srt_time(seconds: float) -> str:
    return format_display_time(seconds).replace(".", ",")


def write_timeline(video: dict[str, Any], segments: list[dict[str, Any]], output: Path, extra: dict[str, Any] | None = None) -> None:
    payload: dict[str, Any] = {"video": video, "segments": segments}
    if extra:
        payload.update(extra)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_manifest(output: Path, payload: dict[str, Any]) -> None:
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_transcript(segments: list[dict[str, Any]], output: Path) -> None:
    lines = ["# Visual Transcript", "", "This is a visual transcript, not recovered original speech.", ""]
    for segment in segments:
        lines.append(
            f"## Segment {segment['id']} - {format_display_time(segment['start'])} -> {format_display_time(segment['end'])}"
        )
        lines.append("")
        lines.append("### Visible text")
        visible_text = segment.get("ocr_text") or []
        if visible_text:
            lines.extend(f"- {item}" for item in visible_text)
        else:
            lines.append("- No reliable visible text extracted.")
        lines.append("")
        lines.append("### Visual content")
        lines.append(str(segment.get("visual_notes") or "No visual notes."))
        lines.append("")
        lines.append("### Inferred presentation intent")
        lines.append(str(segment.get("intent") or "No intent inferred."))
        lines.append("")
    output.write_text("\n".join(lines), encoding="utf-8")


def write_script(segments: list[dict[str, Any]], output: Path, lang: str) -> None:
    lines = ["# Narration Script", ""]
    for segment in segments:
        target = segment["end"] - segment["start"]
        lines.append(
            f"## Segment {segment['id']} - {format_display_time(segment['start'])} -> {format_display_time(segment['end'])}"
        )
        lines.append("")
        lines.append(f"**Goal:** {segment.get('intent') or 'Explain the visible slide content.'}")
        lines.append(f"**Target duration:** {target:.1f} seconds")
        lines.append(f"**Language:** {lang}")
        lines.append("")
        lines.append(str(segment.get("narration") or ""))
        lines.append("")
    output.write_text("\n".join(lines), encoding="utf-8")


HEADING_RE = re.compile(
    r"^##\s+Segment\s+(?P<id>\S+)\s+[-:\u2013\u2014]\s*(?P<start>[0-9:.]+)\s*(?:->|-->|to|\u2192)\s*(?P<end>[0-9:.]+)",
    re.IGNORECASE,
)


def parse_time(value: str | int | float) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", ".")
    if ":" not in text:
        return float(text)
    parts = [float(part) for part in text.split(":")]
    if len(parts) == 3:
        hours, minutes, seconds = parts
    elif len(parts) == 2:
        hours = 0.0
        minutes, seconds = parts
    else:
        raise ValueError(f"Invalid timestamp: {value}")
    return hours * 3600 + minutes * 60 + seconds


def clean_markdown_text(lines: list[str]) -> str:
    cleaned: list[str] = []
    for line in lines:
        text = line.strip()
        if not text:
            continue
        if text.startswith("#"):
            continue
        if re.match(r"^\*\*(Goal|Target duration|Voice|Delivery|Notes|Language):", text, re.IGNORECASE):
            continue
        text = re.sub(r"^\*\*Narration:\*\*\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"[*_`]", "", text)
        cleaned.append(text)
    return " ".join(cleaned).strip()


def parse_markdown(path: Path) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    body: list[str] = []

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        match = HEADING_RE.match(raw_line.strip())
        if match:
            if current:
                current["text"] = clean_markdown_text(body)
                segments.append(current)
            current = {
                "id": match.group("id"),
                "start": parse_time(match.group("start")),
                "end": parse_time(match.group("end")),
            }
            body = []
        elif current:
            body.append(raw_line)

    if current:
        current["text"] = clean_markdown_text(body)
        segments.append(current)

    return segments


def parse_json_segments(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    raw_segments = data.get("segments", data if isinstance(data, list) else [])
    segments: list[dict[str, Any]] = []
    for index, segment in enumerate(raw_segments, start=1):
        text = segment.get("narration") or segment.get("text") or segment.get("script") or ""
        segments.append(
            {
                "id": segment.get("id") or f"seg_{index:04d}",
                "start": parse_time(segment["start"]),
                "end": parse_time(segment["end"]),
                "text": str(text).strip(),
            }
        )
    return segments


def write_srt(segments: list[dict[str, Any]], output: Path) -> None:
    blocks: list[str] = []
    for index, segment in enumerate(segments, start=1):
        text = str(segment.get("text") or segment.get("narration") or "").strip()
        if not text:
            continue
        blocks.append(
            "\n".join(
                [
                    str(index),
                    f"{format_srt_time(segment['start'])} --> {format_srt_time(segment['end'])}",
                    text,
                ]
            )
        )
    output.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")

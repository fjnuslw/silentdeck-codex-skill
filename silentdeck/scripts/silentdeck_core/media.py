"""Media helpers for SilentDeck scripts."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any


def require_binary(name: str, configured_path: str | Path | None = None, env_var: str | None = None) -> str:
    if configured_path:
        candidate = Path(configured_path).expanduser()
        if candidate.exists():
            return str(candidate)
        label = f"{env_var}={candidate}" if env_var else str(candidate)
        raise SystemExit(
            f"{name} was configured as {label}, but that file does not exist.\n"
            f"Next step: update {env_var or 'the configured path'} in .env, or add {name} to PATH."
        )

    path = shutil.which(name)
    if not path:
        if env_var:
            example = f"SILENTDECK_{name.upper()}_PATH"
            if name.lower() == "ffmpeg":
                example = "SILENTDECK_FFMPEG_PATH=C:\\path\\to\\ffmpeg.exe"
            elif name.lower() == "ffprobe":
                example = "SILENTDECK_FFPROBE_PATH=C:\\path\\to\\ffprobe.exe"
            hint = f"Next step: set {example} in .env, or add {name} to PATH."
        else:
            hint = f"Next step: install {name} and add it to PATH."
        raise SystemExit(f"Missing required binary: {name}\n{hint}")
    return path


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )


def parse_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def probe_video(video_path: Path, ffprobe: str | None = None) -> dict[str, Any]:
    ffprobe = ffprobe or require_binary("ffprobe", env_var="SILENTDECK_FFPROBE_PATH")
    result = run_command(
        [
            ffprobe,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(video_path),
        ]
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "ffprobe failed")

    import json

    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
    duration = parse_float(data.get("format", {}).get("duration")) or parse_float(video_stream.get("duration"))
    if not duration:
        raise SystemExit("Could not determine video duration.")

    fps = None
    rate = video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate")
    if isinstance(rate, str) and "/" in rate:
        num, den = rate.split("/", 1)
        den_float = parse_float(den)
        if den_float:
            fps = (parse_float(num) or 0.0) / den_float

    return {
        "path": str(video_path),
        "duration_sec": duration,
        "fps": fps,
        "width": video_stream.get("width"),
        "height": video_stream.get("height"),
        "has_audio": bool(audio_streams),
        "audio_stream_count": len(audio_streams),
    }


def extract_keyframe(ffmpeg: str, video_path: Path, timestamp: float, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    result = run_command(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{timestamp:.3f}",
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(output),
        ]
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or f"ffmpeg failed extracting {output}")


def fit_audio_to_duration(ffmpeg: str, input_audio: Path, duration: float, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    result = run_command(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(input_audio),
            "-filter:a",
            f"apad,atrim=0:{duration:.3f}",
            "-t",
            f"{duration:.3f}",
            "-ac",
            "2",
            "-ar",
            "44100",
            "-c:a",
            "pcm_s16le",
            str(output),
        ]
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or f"Failed to fit audio segment {input_audio}")


def concat_audio(ffmpeg: str, files: list[Path], output: Path) -> None:
    if not files:
        raise SystemExit("No audio files were produced.")
    output.parent.mkdir(parents=True, exist_ok=True)
    list_path = output.with_suffix(".concat.txt")
    list_path.write_text(
        "\n".join(f"file '{path.resolve().as_posix()}'" for path in files),
        encoding="utf-8",
    )
    try:
        result = run_command(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_path),
                "-ac",
                "2",
                "-ar",
                "44100",
                "-c:a",
                "pcm_s16le",
                str(output),
            ]
        )
    finally:
        try:
            list_path.unlink()
        except OSError:
            pass
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "Failed to concatenate audio segments")


def mux_audio(ffmpeg: str, video: Path, audio: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    result = run_command(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(video),
            "-i",
            str(audio),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            str(output),
        ]
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "Failed to mux audio")


def subtitle_filter_path(path: Path) -> str:
    try:
        value = path.resolve().relative_to(Path.cwd()).as_posix()
    except ValueError:
        value = path.resolve().as_posix().replace(":", "\\:")
    return value.replace("'", "\\'")


def burn_subtitles(ffmpeg: str, video: Path, subtitles: Path, output: Path, font_size: int = 12) -> bool:
    output.parent.mkdir(parents=True, exist_ok=True)
    style = f"FontName=Microsoft YaHei,FontSize={font_size},Outline=1,Shadow=0,MarginV=42"
    result = run_command(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(video),
            "-vf",
            f"subtitles='{subtitle_filter_path(subtitles)}':force_style='{style}'",
            "-c:a",
            "copy",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )
    return result.returncode == 0


def mux_subtitles(ffmpeg: str, video: Path, subtitles: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    result = run_command(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(video),
            "-i",
            str(subtitles),
            "-map",
            "0",
            "-map",
            "1:0",
            "-c:v",
            "copy",
            "-c:a",
            "copy",
            "-c:s",
            "mov_text",
            "-metadata:s:s:0",
            "language=chi",
            str(output),
        ]
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "Failed to mux subtitles")

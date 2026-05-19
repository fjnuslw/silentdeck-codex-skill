"""Build narrated videos from an existing SilentDeck script."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .documents import parse_json_segments, parse_markdown, write_manifest, write_srt
from .env import get_setting, load_env
from .media import burn_subtitles, concat_audio, fit_audio_to_duration, mux_audio, mux_subtitles, probe_video, require_binary
from .providers.siliconflow import SiliconFlowClient
from .tts import parse_tts_chain, synthesize_tts_chain


def load_script_segments(path: Path) -> list[dict[str, Any]]:
    segments = parse_json_segments(path) if path.suffix.lower() == ".json" else parse_markdown(path)
    normalized: list[dict[str, Any]] = []
    for index, segment in enumerate(segments, start=1):
        text = str(segment.get("text") or segment.get("narration") or "").strip()
        normalized.append(
            {
                "id": str(segment.get("id") or f"seg_{index:04d}"),
                "start": float(segment["start"]),
                "end": float(segment["end"]),
                "text": text,
            }
        )
    return normalized


def build_from_script(
    *,
    input_video: Path,
    script_path: Path,
    output_dir: Path,
    env_path: Path | None,
    lang: str | None = None,
    subtitle: bool = True,
    tts_chain: str | None = None,
    tts_model: str | None = None,
    tts_voice: str | None = None,
    edge_voice: str | None = None,
    sapi_voice: str | None = None,
) -> dict[str, Any]:
    if not input_video.exists():
        raise SystemExit(f"Input video not found: {input_video}")
    if not script_path.exists():
        raise SystemExit(
            f"Script file not found: {script_path}\n"
            "Next step: pass --manual-script path\\to\\script.md, or create script.md with segment headings first."
        )

    env = load_env(env_path)
    ffmpeg = require_binary("ffmpeg", get_setting(env, "SILENTDECK_FFMPEG_PATH"), "SILENTDECK_FFMPEG_PATH")
    ffprobe = require_binary("ffprobe", get_setting(env, "SILENTDECK_FFPROBE_PATH"), "SILENTDECK_FFPROBE_PATH")
    output_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = output_dir / "assets"
    audio_dir = assets_dir / "audio_segments"
    audio_dir.mkdir(parents=True, exist_ok=True)

    video = probe_video(input_video, ffprobe)
    segments = load_script_segments(script_path)
    if not segments:
        raise SystemExit(
            "No script segments found.\n"
            "Next step: use headings like `## Segment seg_0001 - 00:00:00.000 -> 00:00:05.000` in script.md."
        )

    api_key = get_setting(env, "SILICONFLOW_API_KEY")
    base_url = get_setting(env, "SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
    client = SiliconFlowClient(api_key, base_url) if api_key else None
    lang = lang or get_setting(env, "SILENTDECK_LANG", "zh-CN")
    chain = parse_tts_chain(tts_chain or get_setting(env, "SILENTDECK_TTS_CHAIN", "siliconflow,edge,sapi"))
    tts_model = tts_model or get_setting(env, "SILENTDECK_TTS_MODEL", "FunAudioLLM/CosyVoice2-0.5B")
    tts_voice = tts_voice or get_setting(env, "SILENTDECK_TTS_VOICE", "FunAudioLLM/CosyVoice2-0.5B:alex")
    edge_voice = edge_voice or get_setting(env, "SILENTDECK_EDGE_TTS_VOICE", "zh-CN-XiaoxiaoNeural")
    sapi_voice = sapi_voice or get_setting(env, "SILENTDECK_SAPI_VOICE", "")

    srt_path = output_dir / "subtitles.srt"
    final_audio = assets_dir / "final.wav"
    narrated_video = output_dir / "narrated.mp4"
    subtitled_video = output_dir / "subtitled.mp4"
    manifest_path = assets_dir / "manifest.json"
    script_copy = output_dir / "script.md"
    warnings: list[str] = []
    tts_attempts: dict[str, Any] = {}
    fitted_audio: list[Path] = []
    audio_done = False
    video_done = False
    subtitled_done = False

    if script_path.suffix.lower() != ".json" and script_path.resolve() != script_copy.resolve():
        script_copy.write_text(script_path.read_text(encoding="utf-8"), encoding="utf-8")

    if subtitle:
        write_srt(segments, srt_path)

    for segment in segments:
        result = synthesize_tts_chain(
            text=str(segment.get("text") or ""),
            segment_id=str(segment["id"]),
            output_dir=audio_dir,
            chain=chain,
            client=client,
            tts_model=tts_model,
            tts_voice=tts_voice,
            edge_voice=edge_voice,
            sapi_voice=sapi_voice,
        )
        tts_attempts[str(segment["id"])] = result["attempts"]
        if not result["ok"]:
            warnings.append(
                f"TTS failed for {segment['id']}. Next step: check SILICONFLOW_API_KEY/TTS model, install edge-tts, "
                "or keep editing script.md and rerun build_from_script.py."
            )
            continue

        fitted = audio_dir / f"{segment['id']}_fit.wav"
        try:
            fit_audio_to_duration(ffmpeg, Path(result["file"]), float(segment["end"]) - float(segment["start"]), fitted)
        except SystemExit as exc:
            warnings.append(f"Audio fitting failed for {segment['id']}: {exc.code}")
            continue
        fitted_audio.append(fitted)

    audio_complete = len(fitted_audio) == len(segments)
    if audio_complete:
        concat_audio(ffmpeg, fitted_audio, final_audio)
        audio_done = True
        mux_audio(ffmpeg, input_video, final_audio, narrated_video)
        video_done = True
        if subtitle:
            if not burn_subtitles(ffmpeg, narrated_video, srt_path, subtitled_video):
                warnings.append("Hard subtitle burn failed; muxed subtitles as an MP4 subtitle track instead.")
                mux_subtitles(ffmpeg, narrated_video, srt_path, subtitled_video)
            subtitled_done = True
    else:
        warnings.append(
            "Audio/video rendering skipped because not every segment has TTS audio. "
            "Script and subtitles are still available for manual retry."
        )

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": "build_from_script",
        "input": str(input_video),
        "script": str(script_path),
        "output_dir": str(output_dir),
        "language": lang,
        "tts_chain": chain,
        "tts_attempts": tts_attempts,
        "warnings": warnings,
        "video": video,
        "segments": len(segments),
    }
    write_manifest(manifest_path, manifest)

    return {
        "mode": "build_from_script",
        "segments": len(segments),
        "script": str(script_copy if script_copy.exists() else script_path),
        "subtitles": str(srt_path) if subtitle else None,
        "audio": str(final_audio) if audio_done else None,
        "video": str(narrated_video) if video_done else None,
        "subtitled_video": str(subtitled_video) if subtitle and subtitled_done else None,
        "manifest": str(manifest_path),
        "warnings": warnings,
    }

"""End-to-end SilentDeck pipeline."""

from __future__ import annotations

import json
import subprocess
from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .builder import build_from_script
from .documents import write_manifest, write_script, write_srt, write_timeline, write_transcript
from .env import get_setting, load_env
from .media import burn_subtitles, concat_audio, extract_keyframe, fit_audio_to_duration, mux_audio, mux_subtitles, probe_video, require_binary
from .providers.siliconflow import SiliconFlowClient, analyze_keyframe, generate_narration
from .scene import build_segments, detect_scene_changes
from .tts import parse_tts_chain, synthesize_tts_chain


def _ffmpeg_version(ffmpeg: str) -> str:
    result = subprocess.run([ffmpeg, "-version"], text=True, capture_output=True, check=False)
    first_line = (result.stdout or result.stderr or "").splitlines()[0] if (result.stdout or result.stderr) else ""
    return first_line.strip()


def _manual_analysis(segment: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "visible_text": [],
        "visual_notes": reason,
        "intent": "Manual review required before narration.",
        "confidence": 0.0,
        "risk_flags": ["manual_review"],
    }


def run_pipeline(args: Namespace) -> dict[str, Any]:
    if not args.input.exists():
        raise SystemExit(f"Input not found: {args.input}")

    env = load_env(args.env)
    if getattr(args, "manual_script", None) or getattr(args, "tts_only", False):
        script_path = getattr(args, "manual_script", None) or (args.out / "script.md")
        summary = build_from_script(
            input_video=args.input,
            script_path=script_path,
            output_dir=args.out,
            env_path=args.env,
            lang=args.lang,
            subtitle=args.subtitle,
            tts_chain=getattr(args, "tts_chain", None),
            tts_model=args.tts_model,
            tts_voice=args.tts_voice,
            edge_voice=getattr(args, "edge_voice", None),
            sapi_voice=getattr(args, "sapi_voice", None),
        )
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return summary

    skip_vlm = getattr(args, "no_vlm", False)
    api_key = get_setting(env, "SILICONFLOW_API_KEY")
    if not api_key and not skip_vlm:
        raise SystemExit(
            "SILICONFLOW_API_KEY is missing. Fill .env before running the VLM/text pipeline.\n"
            "Next step: add SILICONFLOW_API_KEY, use --no-vlm to create a manual script skeleton, "
            "or use --manual-script/--tts-only if you already have script.md."
        )

    ffmpeg = require_binary("ffmpeg", get_setting(env, "SILENTDECK_FFMPEG_PATH"), "SILENTDECK_FFMPEG_PATH")
    ffprobe = require_binary("ffprobe", get_setting(env, "SILENTDECK_FFPROBE_PATH"), "SILENTDECK_FFPROBE_PATH")
    lang = args.lang or get_setting(env, "SILENTDECK_LANG", "zh-CN")
    segment_sec = args.segment_sec if args.segment_sec is not None else float(get_setting(env, "SILENTDECK_SEGMENT_SEC", "30"))
    scene_threshold = (
        args.scene_threshold if args.scene_threshold is not None else float(get_setting(env, "SILENTDECK_SCENE_THRESHOLD", "0.28"))
    )
    output_dir: Path = args.out
    output_dir.mkdir(parents=True, exist_ok=True)

    video = probe_video(args.input, ffprobe)
    scene_times = detect_scene_changes(args.input, scene_threshold, ffmpeg)
    segments = build_segments(float(video["duration_sec"]), scene_times, segment_sec)
    if args.max_segments is not None:
        segments = segments[: args.max_segments]
    if not segments:
        segments = [{"id": "seg_0001", "start": 0.0, "end": float(video["duration_sec"])}]

    keyframe_dir = output_dir / "assets" / "keyframes"
    audio_dir = output_dir / "assets" / "audio_segments"
    keyframe_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)

    vision_model = args.vision_model or get_setting(env, "SILENTDECK_VISION_MODEL", "Qwen/Qwen3-VL-8B-Instruct")
    text_model = args.text_model or get_setting(env, "SILENTDECK_TEXT_MODEL", "deepseek-ai/DeepSeek-V3")
    tts_model = args.tts_model or get_setting(env, "SILENTDECK_TTS_MODEL", "FunAudioLLM/CosyVoice2-0.5B")
    tts_voice = args.tts_voice or get_setting(env, "SILENTDECK_TTS_VOICE", "FunAudioLLM/CosyVoice2-0.5B:alex")
    edge_voice = getattr(args, "edge_voice", None) or get_setting(env, "SILENTDECK_EDGE_TTS_VOICE", "zh-CN-XiaoxiaoNeural")
    sapi_voice = getattr(args, "sapi_voice", None) or get_setting(env, "SILENTDECK_SAPI_VOICE", "")
    tts_chain = parse_tts_chain(getattr(args, "tts_chain", None) or get_setting(env, "SILENTDECK_TTS_CHAIN", "siliconflow,edge,sapi"))
    base_url = get_setting(env, "SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")

    client = SiliconFlowClient(api_key, base_url) if api_key else None
    processed: list[dict[str, Any]] = []
    audio_files: list[Path] = []
    warnings: list[str] = []
    tts_attempts: dict[str, Any] = {}

    for segment in segments:
        midpoint = float(segment["start"]) + (float(segment["end"]) - float(segment["start"])) / 2.0
        keyframe = keyframe_dir / f"{segment['id']}.jpg"
        extract_keyframe(ffmpeg, args.input, midpoint, keyframe)

        if skip_vlm:
            analysis = _manual_analysis(segment, "VLM skipped by --no-vlm. Use the keyframe and script.md for manual narration.")
            narration = ""
            warnings.append(
                f"VLM skipped for {segment['id']}. Next step: edit script.md, then rerun with --tts-only --manual-script."
            )
        else:
            try:
                analysis = analyze_keyframe(client, vision_model, segment, keyframe, lang)
            except SystemExit as exc:
                analysis = _manual_analysis(segment, f"VLM failed: {exc.code}")
                narration = ""
                warnings.append(
                    f"VLM failed for {segment['id']}: {exc.code}. "
                    "Next step: rerun with --no-vlm, or edit script.md and use --tts-only."
                )
            else:
                try:
                    narration = generate_narration(client, text_model, segment, analysis, lang)
                except SystemExit as exc:
                    narration = ""
                    warnings.append(
                        f"Text generation failed for {segment['id']}: {exc.code}. "
                        "Next step: write this segment in script.md and rerun --tts-only."
                    )

        if narration:
            tts_result = synthesize_tts_chain(
                text=narration,
                segment_id=str(segment["id"]),
                output_dir=audio_dir,
                chain=tts_chain,
                client=client,
                tts_model=tts_model,
                tts_voice=tts_voice,
                edge_voice=edge_voice,
                sapi_voice=sapi_voice,
            )
            tts_attempts[str(segment["id"])] = tts_result["attempts"]
            if tts_result["ok"]:
                fitted_file = audio_dir / f"{segment['id']}_fit.wav"
                try:
                    fit_audio_to_duration(ffmpeg, Path(tts_result["file"]), float(segment["end"]) - float(segment["start"]), fitted_file)
                except SystemExit as exc:
                    warnings.append(f"Audio fitting failed for {segment['id']}: {exc.code}")
                else:
                    audio_files.append(fitted_file)
            else:
                warnings.append(
                    f"TTS failed for {segment['id']}. Next step: check TTS settings, install edge-tts, or keep script/srt only."
                )
        else:
            tts_attempts[str(segment["id"])] = [
                {
                    "provider": "script-only",
                    "ok": True,
                    "message": "No narration text was generated; audio skipped for this segment.",
                    "file": None,
                }
            ]

        processed.append(
            {
                **segment,
                "keyframes": [str(keyframe.relative_to(output_dir))],
                "ocr_text": analysis.get("visible_text") or [],
                "visual_notes": analysis.get("visual_notes") or "",
                "intent": analysis.get("intent") or "",
                "confidence": analysis.get("confidence") or 0.0,
                "risk_flags": analysis.get("risk_flags") or [],
                "narration": narration,
            }
        )

    timeline_path = output_dir / "assets" / "timeline.json"
    transcript_path = output_dir / "transcript.md"
    script_path = output_dir / "script.md"
    srt_path = output_dir / "subtitles.srt"
    final_audio = output_dir / "assets" / "final.wav"
    narrated_video = output_dir / "output_narrated.mp4"
    subtitled_video = output_dir / "output_narrated_subtitled.mp4"
    manifest_path = output_dir / "assets" / "manifest.json"
    audio_done = False
    video_done = False
    subtitled_done = False

    write_timeline(video, processed, timeline_path)
    write_transcript(processed, transcript_path)
    write_script(processed, script_path, lang)
    if args.subtitle:
        write_srt(processed, srt_path)
    if audio_files and len(audio_files) == len(processed):
        concat_audio(ffmpeg, audio_files, final_audio)
        audio_done = True
        mux_audio(ffmpeg, args.input, final_audio, narrated_video)
        video_done = True
        if args.subtitle:
            if not burn_subtitles(ffmpeg, narrated_video, srt_path, subtitled_video):
                warnings.append("Hard subtitle burn failed; muxed subtitles as an MP4 subtitle track instead.")
                mux_subtitles(ffmpeg, narrated_video, srt_path, subtitled_video)
            subtitled_done = True
    else:
        warnings.append(
            "Audio/video rendering skipped because narration or TTS audio is missing for at least one segment. "
            "Next step: edit script.md and rerun with --tts-only --manual-script."
        )

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input": str(args.input),
        "output_dir": str(output_dir),
        "language": lang,
        "segment_sec": segment_sec,
        "scene_threshold": scene_threshold,
        "models": {
            "vision": vision_model,
            "text": text_model,
            "tts": tts_model,
            "voice": tts_voice,
        },
        "tts_chain": tts_chain,
        "tts_attempts": tts_attempts,
        "warnings": warnings,
        "video": video,
        "segments": len(processed),
        "ffmpeg_version": _ffmpeg_version(ffmpeg),
    }
    write_manifest(manifest_path, manifest)

    summary = {
        "segments": len(processed),
        "timeline": str(timeline_path),
        "transcript": str(transcript_path),
        "script": str(script_path),
        "subtitles": str(srt_path) if args.subtitle else None,
        "audio": str(final_audio) if audio_done else None,
        "video": str(narrated_video) if video_done else None,
        "subtitled_video": str(subtitled_video) if args.subtitle and subtitled_done else None,
        "manifest": str(manifest_path),
        "warnings": warnings,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary

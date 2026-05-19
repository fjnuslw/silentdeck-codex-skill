# SilentDeck Architecture

Use this reference when designing or modifying a SilentDeck Python project.

## Package Layout

```text
silentdeck/
  cli.py
  probe.py
  segment.py
  keyframes.py
  ocr.py
  vision.py
  transcript.py
  scriptgen.py
  tts.py
  align.py
  subtitles.py
  mux.py
  schemas.py
```

## CLI Commands

```text
python scripts/init_env.py --out .env
python scripts/run_pipeline.py input.mp4 --out ./output --env .env --subtitle
python scripts/run_pipeline.py input.mp4 --out ./output --env .env --no-vlm --subtitle
python scripts/prepare_agent_review.py ./output --env .env
python scripts/build_from_script.py input.mp4 ./output/script.md --out ./output --env .env
silentdeck run input.mp4 --out ./output --lang zh-CN --voice alloy --subtitle
silentdeck extract input.mp4 --out ./output/assets
silentdeck script ./output/assets/timeline.json --out ./output/script.md
silentdeck speak ./output/script.md --out ./output/assets/audio_segments
silentdeck mux input.mp4 ./output/assets/final.wav --out ./output/output_narrated.mp4
```

The bundled `scripts/run_pipeline.py` is the provider-backed executable path. A separate Python package can later wrap the same behavior as a polished `silentdeck` CLI.

`scripts/prepare_agent_review.py` is the agent-first helper path. It creates contact sheets and a review markdown file so Codex can inspect fewer images while still contributing high-quality visual reasoning and narration.

`scripts/build_from_script.py` is the script-first production path. It accepts an existing `script.md` or `segments.json`, generates SRT, tries the configured TTS chain, and builds `narrated.mp4` plus `subtitled.mp4` when audio is complete.

## Pipeline

1. Probe video metadata and audio streams.
2. Validate that there is no usable speech audio, or document existing audio.
3. Detect slide or scene boundaries.
4. Extract one or more representative keyframes per segment.
5. Run OCR over keyframes.
6. Run VLM analysis when visual semantics matter.
7. Generate `timeline.json`.
8. Generate visual `transcript.md`.
9. Generate timing-aware `script.md`.
10. Generate TTS audio per segment.
11. Rewrite overlong narration before stretching audio.
12. Pad short audio with controlled silence.
13. Normalize and compose the final audio timeline.
14. Mux final audio into the original MP4.
15. Optionally generate or burn subtitles.

## Design Principles

- Keep provider adapters swappable.
- Keep FFmpeg command construction testable.
- Store deterministic intermediate artifacts.
- Keep AI-generated claims tied to visual evidence.
- Use per-segment audio generation for synchronization.
- Keep `.env` configuration outside source control and load provider settings at runtime.
- Support `SILENTDECK_FFMPEG_PATH` and `SILENTDECK_FFPROBE_PATH` for Windows machines where FFmpeg is installed outside PATH.
- Preserve script/SRT outputs and manifest warnings when VLM or TTS providers fail.

## Suggested Python Stack

- Python 3.11+
- Typer for CLI
- Pydantic for schemas
- FFmpeg and ffprobe through subprocess
- PySceneDetect or OpenCV frame-diff logic for segmentation
- PaddleOCR, Tesseract, or a cloud OCR adapter for OCR
- OpenAI-compatible, local, or provider-specific adapters for VLM/text
- Provider TTS, edge-tts, Windows SAPI, or local adapters for TTS
- pytest for tests

## Skill-Level Tool Outputs

`scripts/run_pipeline.py` writes:

```text
output/
  transcript.md
  script.md
  subtitles.srt
  output_narrated.mp4
  assets/
    manifest.json
    timeline.json
    final.wav
    keyframes/
    audio_segments/
    agent_review/
```

`scripts/build_from_script.py` writes:

```text
output/
  script.md
  subtitles.srt
  narrated.mp4
  subtitled.mp4
  assets/
    manifest.json
    final.wav
    audio_segments/
```

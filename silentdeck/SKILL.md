---
name: silentdeck
description: Build, modify, or operate SilentDeck-style pipelines that turn silent presentation MP4 videos into visual transcripts, timing-aware narration scripts, generated speech audio, narrated MP4 outputs, and optional subtitles. Use when Codex needs to analyze silent slide recordings, screen-recorded presentations, lab talks, course videos, research talks, or group reports with no usable speech audio; run local helper scripts; configure .env files; use SiliconFlow or compatible OCR/VLM/TTS APIs; generate transcript.md, script.md, timeline.json, subtitles.srt, or narrated video outputs; or scaffold provider adapters for OCR, vision-language models, text generation, and text-to-speech.
---

# SilentDeck

## Overview

Use this skill to build, modify, or operate workflows that turn silent presentation-style MP4 files into narrated and subtitled videos. The active worker is the Codex agent; the skill supplies the workflow, references, and scripts. Prefer an agent-first hybrid workflow when quality matters: scripts prepare frames and media, Codex/GPT-5.5 analyzes compact review packs and writes narration, then scripts synthesize/mux outputs. Prefer the provider-backed path when the user wants unattended automation, but switch to script-first build mode when VLM or TTS providers are unstable.

Treat the output as reconstructed narration from visual evidence, not recovered original speech. Never imply that SilentDeck extracted a verbatim transcript from a silent video.

## Default Workflow

1. Probe the input video with FFmpeg or `scripts/probe_video.py`.
2. Confirm the video has no usable speech audio, or explicitly document any audio that exists.
3. Segment the video by slide or scene changes.
4. Extract representative keyframes per segment.
5. Run OCR on keyframes when visible text matters.
6. Use VLM analysis only when charts, diagrams, code screenshots, dense academic slides, or visual intent require it.
7. Build `timeline.json` with segment boundaries, keyframes, OCR text, visual notes, and confidence.
8. Generate `transcript.md` as a timestamped visual transcript.
9. Generate `script.md` as a segment-aligned narration script.
10. Generate TTS audio per segment.
11. Fit each audio segment to its target duration by rewriting long text first and padding short audio with controlled silence.
12. Normalize and compose the final audio timeline.
13. Mux audio into the original video with FFmpeg.
14. Optionally generate `subtitles.srt` and burn subtitles into the output video.

## Resource Navigation

- Read `references/architecture.md` when designing or modifying the Python project structure.
- Read `references/data-contracts.md` when creating or validating `timeline.json`, `transcript.md`, `script.md`, or `subtitles.srt`.
- Read `references/provider-design.md` when adding OCR, VLM, text generation, or TTS adapters.
- Read `references/siliconflow.md` when configuring SiliconFlow models, `.env`, or API calls.
- Read `references/codex-assisted.md` when the user asks whether Codex/GPT-5.5 can replace external VLM or text models.
- Read `references/prompting.md` when writing prompts for visual transcript generation, timing-aware script generation, or narration rewriting.

Use bundled scripts instead of rewriting fragile FFmpeg or SRT code:

- `scripts/init_env.py`: create a local `.env` template for SiliconFlow settings.
- `scripts/run_pipeline.py`: run a provider-backed SilentDeck pipeline from MP4 to timeline, transcript, script, SRT, audio, and narrated MP4.
- `scripts/build_from_script.py`: build audio, `narrated.mp4`, `subtitled.mp4`, and SRT from an existing `script.md` or `segments.json`.
- `scripts/prepare_agent_review.py`: create contact sheets and an agent review pack from keyframes for efficient Codex/GPT-5.5 analysis.
- `scripts/probe_video.py`: inspect MP4 streams and audio silence.
- `scripts/extract_keyframes.py`: extract representative frames for segments.
- `scripts/make_srt.py`: convert segment narration text into SRT.
- `scripts/mux_audio.py`: mux a generated WAV or audio track into the source video.

## Model and API Guidance

Prefer provider interfaces so API-backed and interactive modes can coexist. For a user-ready path, use `.env` variables and SiliconFlow's OpenAI-compatible API.

- OCR: use PaddleOCR for Chinese-heavy slides or Tesseract for lightweight local OCR when an OCR adapter is added.
- Vision and script generation: use SiliconFlow or another OpenAI-compatible multimodal/text model. Use smaller models for cost-sensitive work and stronger models for dense academic or chart-heavy slides.
- TTS: use a clear priority chain: SiliconFlow/provider TTS, then edge-tts, then Windows SAPI, then script/SRT-only output with explicit warnings.
- Video and audio processing: use FFmpeg. On Windows, prefer `.env` paths such as `SILENTDECK_FFMPEG_PATH=C:\path\to\ffmpeg.exe` when FFmpeg is not on PATH.

Qwen, DeepSeek, and FunAudioLLM model IDs in `.env` are examples, not hard requirements. Keep model IDs configurable and let users replace them with any provider model that supports the needed modality.

Codex/GPT-5.5 can be used interactively to analyze extracted frames and write narration, but local scripts cannot directly call the current Codex conversation model. Use a provider API for unattended one-command execution.

## One-Command Tool Path

When the user wants to run SilentDeck directly from the skill:

1. Create a local env file:

   ```powershell
   python scripts/init_env.py --out .env
   ```

2. Ask the user to fill `SILICONFLOW_API_KEY` in `.env`.
3. If FFmpeg is not on PATH, ask the user to fill `SILENTDECK_FFMPEG_PATH` and `SILENTDECK_FFPROBE_PATH`.
4. Run:

   ```powershell
   python scripts/run_pipeline.py input.mp4 --out output --env .env --subtitle
   ```

If VLM analysis is slow or timing out, create a manual-review skeleton instead:

```powershell
python scripts/run_pipeline.py input.mp4 --out output --env .env --no-vlm --subtitle
```

After `script.md` is edited, build the final video from that script:

```powershell
python scripts/build_from_script.py input.mp4 output\script.md --out output --env .env
```

The equivalent `run_pipeline.py` shortcut is:

```powershell
python scripts/run_pipeline.py input.mp4 --out output --env .env --tts-only --manual-script output\script.md --subtitle
```

## Agent-First Hybrid Path

When the user wants Codex/GPT-5.5 to participate directly and efficiently:

1. Extract structure and keyframes. Use `--no-vlm` when provider VLM calls are unstable:

   ```powershell
   python scripts/run_pipeline.py input.mp4 --out output --env .env --no-vlm --subtitle
   ```

2. Build a compact review pack:

   ```powershell
   python scripts/prepare_agent_review.py output --env .env
   ```

3. Inspect `output/assets/agent_review/agent_review.md` and the generated contact sheets. Use the current Codex model to revise `timeline.json`, `transcript.md`, `script.md`, and `subtitles.srt`.
4. Build from the edited script:

   ```powershell
   python scripts/build_from_script.py input.mp4 output\script.md --out output --env .env
   ```

5. If TTS fails, preserve `script.md`, `subtitles.srt`, and `assets/manifest.json` warnings; fix the provider settings and rerun `build_from_script.py`.

## MVP Order

1. Schemas and timestamp utilities.
2. FFmpeg probing and silence validation.
3. Scene segmentation and keyframe extraction.
4. OCR and VLM adapters.
5. `timeline.json` generation.
6. `transcript.md` generation.
7. `script.md` generation.
8. SRT generation.
9. TTS audio segment generation.
10. Audio composition and muxing.
11. Real provider adapters.

## Testing Priorities

Add tests for timestamp conversion, SRT formatting, timeline schema validation, segment ordering and non-overlap validation, FFmpeg command construction, manifest generation, and script generation constraints such as target duration and segment IDs.

## Safety and Quality

- Preserve intermediate artifacts under `output/assets/`.
- Keep segment IDs stable, such as `seg_0001`.
- Prefer deterministic file names for frames and audio segments.
- Mark low-confidence visual interpretations.
- Require manual review warnings for scientific, medical, legal, financial, or policy content.
- Avoid inventing facts not visible in the source video.

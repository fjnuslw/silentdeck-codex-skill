# SilentDeck

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

SilentDeck is a Codex skill for adding narration and subtitles to silent presentation-style videos.

It extracts a visual timeline from an MP4, prepares keyframes for agent review, writes or accepts a time-aligned narration script, synthesizes speech per segment, and uses FFmpeg to build a narrated video.

## Status

This repository is a Codex skill with local helper scripts. It is usable from the command line, but it is not yet a packaged Python CLI.

The current focus is silent slide decks, screen recordings, course clips, research talks, and business presentation videos. The same pipeline can later be adapted to denser frame sampling for short-form generated videos and other visual-first content.

## Features

- Video probing with FFmpeg and ffprobe
- Scene or slide-based segmentation
- Keyframe extraction for visual review
- Provider-backed visual analysis and narration generation
- Agent-first review flow for higher quality scripts
- Script-first rendering from `script.md` or `segments.json`
- Per-segment TTS and audio fitting
- SRT generation and MP4 muxing
- Windows-friendly `.env` configuration for FFmpeg paths

## Outputs

SilentDeck can produce:

| File | Purpose |
| --- | --- |
| `assets/timeline.json` | Segment timing, keyframes, visual notes, and metadata |
| `transcript.md` | Visual transcript inferred from frames |
| `script.md` | Time-aligned narration script |
| `subtitles.srt` | Subtitle file generated from the script |
| `assets/final.wav` | Composed narration audio |
| `output_narrated.mp4` | Source video with narration audio |
| `output_narrated_subtitled.mp4` | Narrated video with subtitles |

`assets/manifest.json` records model choices, warnings, TTS attempts, and generated artifacts.

## Requirements

- Python 3.11+
- FFmpeg and ffprobe
- Codex with local skill support
- Optional: SiliconFlow API key for VLM, text generation, and provider TTS
- Optional: edge-tts or Windows SAPI for local TTS paths

## Installation

Clone the repository:

```powershell
git clone https://github.com/fjnuslw/silentdeck-codex-skill.git
cd silentdeck-codex-skill
```

Install the skill by copying the `silentdeck/` folder into your Codex skills directory:

```text
<CODEX_HOME>/skills/silentdeck/
```

The skill entry point is:

```text
silentdeck/SKILL.md
```

## Configuration

Create a local `.env` file:

```powershell
python silentdeck/scripts/init_env.py --out silentdeck/.env
```

Set your provider key:

```text
SILICONFLOW_API_KEY=
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
```

If FFmpeg is not on `PATH`, set explicit paths:

```text
SILENTDECK_FFMPEG_PATH=C:\path\to\ffmpeg.exe
SILENTDECK_FFPROBE_PATH=C:\path\to\ffprobe.exe
```

Model IDs are configurable:

```text
SILENTDECK_VISION_MODEL=Qwen/Qwen3-VL-8B-Instruct
SILENTDECK_TEXT_MODEL=deepseek-ai/DeepSeek-V3
SILENTDECK_TTS_MODEL=FunAudioLLM/CosyVoice2-0.5B
SILENTDECK_TTS_VOICE=FunAudioLLM/CosyVoice2-0.5B:alex
SILENTDECK_TTS_CHAIN=siliconflow,edge,sapi
```

Do not commit real `.env` files or API keys.

## Quick Start

Run the provider-backed pipeline:

```powershell
python silentdeck/scripts/run_pipeline.py input.mp4 --out output --env silentdeck/.env --subtitle
```

If the visual model is slow or unstable, use the agent-first path:

```powershell
python silentdeck/scripts/run_pipeline.py input.mp4 --out output --env silentdeck/.env --no-vlm --subtitle
python silentdeck/scripts/prepare_agent_review.py output --env silentdeck/.env
python silentdeck/scripts/build_from_script.py input.mp4 output\script.md --out output --env silentdeck/.env
```

If you already have a script:

```powershell
python silentdeck/scripts/build_from_script.py input.mp4 script.md --out output --env silentdeck/.env
```

## Workflows

### Provider-backed

Use this when your VLM, text, and TTS provider is stable enough for unattended processing.

```powershell
python silentdeck/scripts/run_pipeline.py input.mp4 --out output --env silentdeck/.env --subtitle
```

### Agent-first

Use this when script quality matters or when provider VLM calls time out. SilentDeck extracts the structure and keyframes; Codex reviews the generated contact sheets and edits the script; the local script then builds the final media.

```powershell
python silentdeck/scripts/run_pipeline.py input.mp4 --out output --env silentdeck/.env --no-vlm --subtitle
python silentdeck/scripts/prepare_agent_review.py output --env silentdeck/.env
python silentdeck/scripts/build_from_script.py input.mp4 output\script.md --out output --env silentdeck/.env
```

### Script-first

Use this when the narration has already been written by a person, by Codex, or by another script generator.

```powershell
python silentdeck/scripts/build_from_script.py input.mp4 script.md --out output --env silentdeck/.env
```

### TTS-only

Use this when timeline and script files already exist and only audio/video rendering is needed.

```powershell
python silentdeck/scripts/run_pipeline.py input.mp4 --out output --env silentdeck/.env --tts-only --manual-script output\script.md --subtitle
```

## Use Cases

- Silent slide recordings
- Research group-meeting rehearsals
- Course and tutorial clips
- Product demos and UI walkthroughs
- PPT-based business reports
- Short-form generated videos that need explanatory narration

## Repository Layout

```text
silentdeck/
  SKILL.md
  agents/
  assets/
  references/
  scripts/
```

The `references/` folder contains design notes for data contracts, provider adapters, SiliconFlow setup, and Codex-assisted workflows.

## Design Notes

- Generated narration should stay grounded in visible evidence.
- `transcript.md` is a visual transcript, not recovered original speech.
- Audio is generated per segment to keep narration aligned with the video.
- Intermediate artifacts are kept so humans and agents can inspect, revise, and rerun specific steps.
- TTS failures preserve `script.md`, `subtitles.srt`, and `assets/manifest.json` for retry.

## Roadmap

- Package the helper scripts as a proper Python CLI
- Add schema validation for timeline and script files
- Add tests for timestamp parsing, SRT generation, and FFmpeg command construction
- Add more provider adapters for OCR, VLM, text generation, and TTS
- Improve dense-frame workflows for short-form visual videos
- Add sample videos or screenshots once licensing-safe examples are available

## License

MIT

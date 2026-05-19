# SilentDeck

SilentDeck is a Codex skill for turning silent presentation-style MP4 videos into visual transcripts, timing-aware narration scripts, generated speech audio, narrated videos, and subtitles.

It is designed for slide recordings, course videos, lab talks, research presentations, group reports, and screen-recorded presentations where there is no usable speech audio.

## What It Can Do

- Probe video metadata with FFmpeg and ffprobe.
- Segment silent presentation videos by scene or slide changes.
- Extract representative keyframes for review.
- Generate `timeline.json`, `transcript.md`, `script.md`, and `subtitles.srt`.
- Use SiliconFlow-compatible VLM, text, and TTS APIs for automated runs.
- Support an agent-first workflow where Codex/GPT-5.5 reviews keyframes and writes narration.
- Build narrated and subtitled MP4 files from an existing `script.md` or `segments.json`.
- Try a TTS chain: SiliconFlow provider TTS, edge-tts, Windows SAPI, then script/SRT-only output with warnings.

## What It Is Not

SilentDeck reconstructs narration from visible evidence. It does not recover the original speaker's exact words from a silent video.

This repository is currently a Codex skill plus helper scripts. It is not yet a packaged Python CLI on PyPI.

## Requirements

- Python 3.11+
- FFmpeg and ffprobe
- A Codex environment that can load local skills
- Optional: SiliconFlow API key for provider-backed VLM/text/TTS
- Optional: edge-tts or Windows SAPI for local TTS paths

## Install As A Codex Skill

Copy or clone this repository, then place the `silentdeck/` folder under your Codex skills directory:

```text
<CODEX_HOME>/skills/silentdeck/
```

The skill entry point is:

```text
silentdeck/SKILL.md
```

## Configure

Create a local `.env` file:

```powershell
python silentdeck/scripts/init_env.py --out silentdeck/.env
```

Fill in your provider key:

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

Never commit real `.env` files or API keys.

## Usage

Provider-backed one-command path:

```powershell
python silentdeck/scripts/run_pipeline.py input.mp4 --out output --env silentdeck/.env --subtitle
```

Agent-first path for higher reliability:

```powershell
python silentdeck/scripts/run_pipeline.py input.mp4 --out output --env silentdeck/.env --no-vlm --subtitle
python silentdeck/scripts/prepare_agent_review.py output --env silentdeck/.env
python silentdeck/scripts/build_from_script.py input.mp4 output\script.md --out output --env silentdeck/.env
```

Build directly from an existing script:

```powershell
python silentdeck/scripts/build_from_script.py input.mp4 script.md --out output --env silentdeck/.env
```

Use `--manual-script` or `--tts-only` when you already have a script and only need audio/video generation:

```powershell
python silentdeck/scripts/run_pipeline.py input.mp4 --out output --env silentdeck/.env --tts-only --manual-script output\script.md --subtitle
```

## Output Layout

Typical output:

```text
output/
  transcript.md
  script.md
  subtitles.srt
  output_narrated.mp4
  output_narrated_subtitled.mp4
  assets/
    manifest.json
    timeline.json
    final.wav
    keyframes/
    audio_segments/
    agent_review/
```

`assets/manifest.json` records warnings, model choices, TTS attempts, and generated artifacts.

## Repository Layout

```text
silentdeck/
  SKILL.md
  agents/
  assets/
  references/
  scripts/
```

The `references/` folder contains longer design notes for data contracts, provider adapters, SiliconFlow setup, and Codex-assisted workflows.

## Safety Notes

- Do not treat the generated transcript as verbatim speech.
- Review outputs manually for scientific, medical, legal, financial, or policy content.
- Keep generated media and local `.env` files out of version control.

## License

MIT

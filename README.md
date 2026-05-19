# SilentDeck

**SilentDeck turns silent visual videos into narrated, subtitled stories.**

It started as a Codex skill for silent presentation recordings, but the broader idea is simple: if a video has enough visual signal, SilentDeck can extract the timeline, help an agent understand what is happening, write a time-aware narration script, synthesize speech, and mux everything back into a finished video.

The first target is silent slide and screen-recorded presentation videos. The longer-term direction is broader: AI-generated short videos, research group-meeting rehearsals, PPT business reports, course clips, product demos, and any visual-first video that needs automatic explanation.

## Why This Exists

Many useful videos are visually rich but silent, under-explained, or hard to present live:

- a screen recording of slides with no speaker audio
- a lab meeting deck that needs a simulated walkthrough
- a business PPT that needs a polished narration track
- an AI-generated short video that needs contextual commentary
- a course or tutorial clip that needs subtitles and voiceover
- a product demo that should explain UI changes as they appear

SilentDeck treats narration as a **reconstruction from visual evidence**, not as recovered original speech. It is built around time-aligned segments, visible keyframes, grounded narration, per-segment TTS, and reproducible FFmpeg outputs.

## What It Can Do Today

- Probe video metadata with FFmpeg and ffprobe.
- Segment silent presentation videos by scene or slide changes.
- Extract representative keyframes for review.
- Generate `timeline.json`, `transcript.md`, `script.md`, and `subtitles.srt`.
- Use SiliconFlow-compatible VLM, text, and TTS APIs for automated runs.
- Support an agent-first workflow where Codex/GPT-5.5 reviews keyframes and writes narration.
- Build narrated and subtitled MP4 files from an existing `script.md` or `segments.json`.
- Try a practical TTS chain: SiliconFlow provider TTS, edge-tts, Windows SAPI, then script/SRT-only output with warnings.

## What This Could Become

SilentDeck is currently a Codex skill plus helper scripts, but the architecture is intentionally broader than one presentation workflow.

Possible directions:

- **AI short-video auto narration**: sample frames more densely, let a small vision model track scene changes, then generate short-form commentary for Douyin/TikTok-style clips.
- **Group-meeting simulation**: turn a silent research deck into a spoken rehearsal script with timestamps, subtitles, and review notes.
- **Business presentation voiceover**: create polished narration for sales decks, investor updates, product reports, and internal briefings.
- **Course and tutorial narration**: explain visual steps from screen recordings or slide-based lessons.
- **Agentic video post-production**: let an agent inspect contact sheets, revise the script, retry TTS, and produce a final narrated MP4.

The core bet is that video narration can be decomposed into reliable pieces: frame extraction, timeline construction, visual reasoning, script writing, speech synthesis, and FFmpeg assembly.

## What It Is Not

SilentDeck does not recover the original speaker's exact words from a silent video.

It is not yet a packaged Python CLI on PyPI. The current repository is a Codex skill with local helper scripts that can run directly.

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

## Workflows

### Provider-backed one-command path

Use this when your VLM/text/TTS provider is stable and you want automation:

```powershell
python silentdeck/scripts/run_pipeline.py input.mp4 --out output --env silentdeck/.env --subtitle
```

### Agent-first path

Use this when quality matters, when VLM calls time out, or when you want Codex/GPT-5.5 to write better narration:

```powershell
python silentdeck/scripts/run_pipeline.py input.mp4 --out output --env silentdeck/.env --no-vlm --subtitle
python silentdeck/scripts/prepare_agent_review.py output --env silentdeck/.env
python silentdeck/scripts/build_from_script.py input.mp4 output\script.md --out output --env silentdeck/.env
```

### Build directly from an existing script

Use this when you already have `script.md` or `segments.json`:

```powershell
python silentdeck/scripts/build_from_script.py input.mp4 script.md --out output --env silentdeck/.env
```

### TTS-only shortcut

Use this when the visual analysis and script are already done:

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

## Design Principles

- Keep facts grounded in visible evidence.
- Generate narration per segment, not as one long disconnected audio file.
- Preserve intermediate artifacts so agents and humans can review and retry.
- Let provider-backed automation and agent-assisted workflows coexist.
- Prefer clear failure messages with the next actionable step.

## Safety Notes

- Do not treat the generated transcript as verbatim speech.
- Review outputs manually for scientific, medical, legal, financial, or policy content.
- Keep generated media and local `.env` files out of version control.

## License

MIT

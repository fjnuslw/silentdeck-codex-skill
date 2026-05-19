# Codex-Assisted Workflow

Use this reference when the user asks whether Codex itself, GPT-5.5, or the current Codex conversation can do the visual analysis and narration work.

The skill is not a separate autonomous agent. The active agent is Codex. The skill gives Codex a specialized playbook, references, and local tools. This means Codex can participate in the work interactively, while scripts handle repetitive media operations.

## Key Distinction

Codex in an interactive chat can use its current model to inspect extracted keyframes, reason about the visible content, write Chinese narration, adjust subtitles, and patch the local pipeline. This is useful for one-off jobs or for debugging a difficult video.

The local Python script cannot directly call "the current Codex conversation model" as an API. For unattended command-line execution, the script needs an external provider such as SiliconFlow or OpenAI API credentials.

## GPT-5.5 Fit

GPT-5.5 is suitable for:

- analyzing extracted keyframes
- writing grounded visual notes
- creating concise Chinese narration
- editing `timeline.json`, `transcript.md`, `script.md`, and `subtitles.srt`
- reviewing subtitle placement and quality from verification frames

GPT-5.5 is not a complete replacement for:

- FFmpeg video processing
- TTS speech synthesis
- direct video-frame batch processing from a local script without an API

Extract representative frames first, create a compact review pack, then ask Codex to analyze the frames. Use a TTS provider for the final audio.

## Efficient Agent-First Flow

1. Extract structure and keyframes. Use `--no-vlm` if external VLM calls are slow or unstable:

   ```powershell
   python scripts/run_pipeline.py input.mp4 --out output --env .env --no-vlm --subtitle
   ```

2. Create an agent review pack:

   ```powershell
   python scripts/prepare_agent_review.py output --env .env
   ```

3. Ask Codex to inspect `output/assets/agent_review/agent_review.md` and the contact sheets before opening individual keyframes.
4. Let Codex write or revise `timeline.json`, `transcript.md`, `script.md`, and `subtitles.srt`.
5. Build the final media from the edited script:

   ```powershell
   python scripts/build_from_script.py input.mp4 output\script.md --out output --env .env
   ```

6. If TTS fails, inspect `output/assets/manifest.json`, fix `.env`, and rerun `build_from_script.py`.
7. Extract a verification frame from the final video and ask Codex to inspect subtitle placement.

This is usually more efficient than asking Codex to inspect every keyframe individually.

## When To Prefer Provider Automation

Use `scripts/run_pipeline.py` when the user wants one command to process the video without manual frame-by-frame Codex review.

Use Codex-assisted mode when quality matters more than unattended automation, the video is short, or the provider model produces poor narration.

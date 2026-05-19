# Provider Design

Use this reference when adding OCR, VLM, text generation, or TTS adapters.

## Provider Rule

Every provider must fail with a clear, actionable error when credentials, binaries, or model files are missing.

For SiliconFlow, load settings from `.env`:

- `SILICONFLOW_API_KEY`
- `SILICONFLOW_BASE_URL`
- `SILENTDECK_VISION_MODEL`
- `SILENTDECK_TEXT_MODEL`
- `SILENTDECK_TTS_MODEL`
- `SILENTDECK_TTS_VOICE`
- `SILENTDECK_TTS_CHAIN`
- `SILENTDECK_FFMPEG_PATH`
- `SILENTDECK_FFPROBE_PATH`

See `references/siliconflow.md` for endpoint and payload details.

## OCR Providers

Required interface:

- input: image path or bytes
- output: list of recognized text blocks with confidence

Recommended providers:

- `tesseract`: lightweight local OCR
- `paddleocr`: better for Chinese-heavy slides
- `cloud`: optional cloud OCR adapter

## VLM Providers

Required interface:

- input: segment metadata and one or more keyframes
- output: visual notes, inferred intent, confidence, and risk flags

Recommended providers:

- `siliconflow`: multimodal model through `/chat/completions`
- `openai`: multimodal model through the Responses API or compatible client
- `codex-assisted`: interactive Codex/GPT-5.5 analysis of extracted keyframes, not callable from the local script
- `local`: local vision-language model adapter

Use VLM analysis when slides include charts, diagrams, formulas, code screenshots, dense academic content, UI screens, or low-OCR visual meaning.

## Text Generation Providers

Responsibilities:

- create transcript sections from OCR and visual notes
- create narration scripts constrained by segment duration
- rewrite narration if synthesized audio is too long
- keep facts grounded in visible content

## TTS Providers

Required interface:

- input: text, language, voice, and target duration
- output: audio file path plus measured duration

Recommended providers:

- `siliconflow`: `/audio/speech` with configurable model and voice
- `edge-tts`: local/free-ish baseline
- `openai`: production speech generation
- `azure`: enterprise TTS option
- `local`: local TTS model adapter

Codex/GPT-5.5 can write narration text but does not itself synthesize final speech audio inside this local pipeline. Pair Codex-assisted analysis with a TTS provider or local speech engine.

Default TTS priority:

1. `siliconflow`: provider TTS through `/audio/speech`
2. `edge`: edge-tts CLI when installed
3. `sapi`: Windows SAPI through PowerShell
4. script/SRT-only output with manifest warnings

TTS failures should not delete or block `script.md`, `subtitles.srt`, keyframes, or `assets/manifest.json`. If not every segment has audio, skip final audio/video rendering and tell the user to fix TTS settings or rerun `scripts/build_from_script.py`.

Generate audio per segment. Avoid producing one long narration file and hoping it matches the video timeline.

## Timing Strategy

For each segment:

1. Estimate target duration as `end - start`.
2. Generate or rewrite narration text to fit the target.
3. Synthesize TTS for the segment.
4. If audio is too long, rewrite text shorter first.
5. If audio is slightly short, insert controlled silence padding.
6. Normalize loudness across segments.
7. Compose all segments on the original timeline.

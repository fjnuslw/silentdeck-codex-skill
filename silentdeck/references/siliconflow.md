# SiliconFlow Provider

Use this reference when configuring `.env` files or calling SiliconFlow models from SilentDeck tools.

## Official API Shape

SiliconFlow provides OpenAI-compatible endpoints:

- Base URL: `https://api.siliconflow.cn/v1`
- Chat completions: `POST /chat/completions`
- Model list: `GET /models`
- Speech generation: `POST /audio/speech`

Use `Authorization: Bearer <SILICONFLOW_API_KEY>`.

## Multimodal Inputs

Multimodal models use `/chat/completions`. Message `content` can be a list containing text and media parts:

```json
[
  {
    "type": "image_url",
    "image_url": {
      "url": "data:image/jpeg;base64,...",
      "detail": "high"
    }
  },
  {
    "type": "text",
    "text": "Analyze this silent presentation keyframe."
  }
]
```

Use image keyframes for SilentDeck by default. Avoid sending whole videos unless the user explicitly wants video-model processing and understands the cost and latency.

## TTS Inputs

The speech endpoint accepts fields such as:

```json
{
  "model": "FunAudioLLM/CosyVoice2-0.5B",
  "voice": "FunAudioLLM/CosyVoice2-0.5B:alex",
  "input": "Narration text",
  "response_format": "mp3"
}
```

SiliconFlow notes that TTS model availability may change, so expose model and voice IDs through `.env`.

## Required .env Variables

```text
SILICONFLOW_API_KEY=
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
SILENTDECK_FFMPEG_PATH=
SILENTDECK_FFPROBE_PATH=
SILENTDECK_VISION_MODEL=Qwen/Qwen3-VL-8B-Instruct
SILENTDECK_TEXT_MODEL=deepseek-ai/DeepSeek-V3
SILENTDECK_TTS_MODEL=FunAudioLLM/CosyVoice2-0.5B
SILENTDECK_TTS_VOICE=FunAudioLLM/CosyVoice2-0.5B:alex
SILENTDECK_TTS_CHAIN=siliconflow,edge,sapi
SILENTDECK_EDGE_TTS_VOICE=zh-CN-XiaoxiaoNeural
SILENTDECK_SAPI_VOICE=
SILENTDECK_LANG=zh-CN
SILENTDECK_SEGMENT_SEC=30
SILENTDECK_SCENE_THRESHOLD=0.28
```

The Qwen, DeepSeek, and FunAudioLLM values above are examples, not required dependencies. Any SiliconFlow model that supports the needed modality can be used:

- vision model: image input plus text output
- text model: text input/output for narration rewriting
- TTS model: speech generation through `/audio/speech`

## Runtime Rules

- Never commit real `.env` files or API keys.
- Keep model names configurable because SiliconFlow model availability changes.
- If the chosen model returns `model not found`, call `/models` or ask the user to copy an exact model ID from the Model Plaza.
- Override models from the command line when testing alternatives:
- If FFmpeg is not on PATH, set `SILENTDECK_FFMPEG_PATH` and `SILENTDECK_FFPROBE_PATH`.
- If VLM calls time out, use `--no-vlm`, let Codex edit `script.md`, then run `scripts/build_from_script.py`.
- If provider TTS fails, the TTS chain tries edge-tts and Windows SAPI before leaving script/SRT-only outputs.

```powershell
python scripts/run_pipeline.py input.mp4 --out output --env .env --vision-model "Qwen/Qwen3-VL-8B-Instruct" --text-model "deepseek-ai/DeepSeek-V3"
```

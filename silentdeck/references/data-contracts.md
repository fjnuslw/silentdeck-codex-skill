# Data Contracts

Use this reference when creating or validating `timeline.json`, `transcript.md`, `script.md`, and `subtitles.srt`.

## timeline.json

Required top-level fields:

- `video.path`
- `video.duration_sec`
- `video.fps`
- `video.width`
- `video.height`
- `video.has_audio`
- `segments`

Recommended video fields:

- `audio_mean_volume_db`
- `audio_max_volume_db`
- `language`
- `source_sha256`

Required segment fields:

- `id`
- `start`
- `end`
- `keyframes`
- `ocr_text`
- `visual_notes`
- `confidence`

Recommended segment fields:

- `intent`
- `risk_flags`
- `speaker_notes`
- `review_required`

Rules:

- `start < end`
- segments must be sorted by `start`
- segments should not overlap
- segment IDs should be stable and zero-padded, such as `seg_0001`
- keyframe and audio paths should be relative to the output directory when possible

## Example timeline.json

```json
{
  "video": {
    "path": "input.mp4",
    "duration_sec": 612.4,
    "fps": 30,
    "width": 1920,
    "height": 1080,
    "has_audio": false
  },
  "segments": [
    {
      "id": "seg_0001",
      "start": 0.0,
      "end": 18.2,
      "keyframes": ["assets/keyframes/seg_0001.jpg"],
      "ocr_text": ["Project Overview", "Motivation", "Method"],
      "visual_notes": "Title slide introducing the project structure.",
      "confidence": 0.86
    }
  ]
}
```

## transcript.md

Use visual transcript wording. Include:

- segment ID
- timestamp range
- visible text
- visual content
- inferred presentation intent
- confidence or review note when needed

Never label this as a verbatim ASR transcript unless real speech audio was transcribed.

## script.md

Each segment should include:

- segment ID
- timestamp range
- goal
- target duration
- narration text
- optional delivery notes

Keep narration constrained by the segment duration. If audio synthesis produces overlong audio, rewrite the segment shorter before using audio speed changes.

## subtitles.srt

Use standard SRT timestamps:

```text
HH:MM:SS,mmm --> HH:MM:SS,mmm
```

Subtitles should follow final narration timing, not merely original slide timing, when those differ.

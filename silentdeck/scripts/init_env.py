#!/usr/bin/env python3
"""Create a SilentDeck .env template for SiliconFlow settings."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


TEMPLATE = """# SilentDeck SiliconFlow configuration
# Fill SILICONFLOW_API_KEY, then run scripts/run_pipeline.py.

SILICONFLOW_API_KEY=
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1

# Optional Windows paths when ffmpeg/ffprobe are not on PATH.
SILENTDECK_FFMPEG_PATH=
SILENTDECK_FFPROBE_PATH=

# Example model IDs. Replace them with the exact IDs you want to use.
SILENTDECK_VISION_MODEL=Qwen/Qwen3-VL-8B-Instruct
SILENTDECK_TEXT_MODEL=deepseek-ai/DeepSeek-V3
SILENTDECK_TTS_MODEL=FunAudioLLM/CosyVoice2-0.5B
SILENTDECK_TTS_VOICE=FunAudioLLM/CosyVoice2-0.5B:alex

# TTS priority chain: provider TTS -> edge-tts -> Windows SAPI -> script/srt only.
SILENTDECK_TTS_CHAIN=siliconflow,edge,sapi
SILENTDECK_EDGE_TTS_VOICE=zh-CN-XiaoxiaoNeural
SILENTDECK_SAPI_VOICE=

SILENTDECK_LANG=zh-CN
SILENTDECK_SEGMENT_SEC=30
SILENTDECK_SCENE_THRESHOLD=0.28
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a SilentDeck .env template.")
    parser.add_argument("--out", type=Path, default=Path(".env"))
    parser.add_argument("--force", action="store_true", help="Overwrite an existing env file.")
    args = parser.parse_args()

    if args.out.exists() and not args.force:
        raise SystemExit(f"{args.out} already exists. Use --force to overwrite it.")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(TEMPLATE, encoding="utf-8")
    print(f"Created {args.out}")
    print("Fill SILICONFLOW_API_KEY before running the pipeline.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

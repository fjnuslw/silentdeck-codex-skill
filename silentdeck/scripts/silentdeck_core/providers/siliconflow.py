"""SiliconFlow provider adapter for SilentDeck."""

from __future__ import annotations

import base64
import json
import mimetypes
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def extract_json_object(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if "\n" in stripped:
            stripped = stripped.split("\n", 1)[1]
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        parsed = json.loads(stripped[start : end + 1])
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


class SiliconFlowClient:
    def __init__(self, api_key: str, base_url: str) -> None:
        if not api_key:
            raise SystemExit("SILICONFLOW_API_KEY is missing. Fill .env or set the environment variable.")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def request_json(self, path: str, payload: dict[str, Any], timeout: int = 180) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise SystemExit(
                f"SiliconFlow HTTP {exc.code}: {detail}\n"
                "Next step: verify the API key and model ID in .env. For urgent output, rerun with --manual-script or --no-vlm."
            ) from exc
        except urllib.error.URLError as exc:
            raise SystemExit(
                f"SiliconFlow request failed: {exc}\n"
                "Next step: retry, switch to --no-vlm, or use build_from_script.py with an existing script.md."
            ) from exc

    def chat(self, model: str, messages: list[dict[str, Any]], max_tokens: int = 2048) -> str:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": max_tokens,
        }
        data = self.request_json("/chat/completions", payload)
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise SystemExit(f"Unexpected chat response: {data}") from exc

    def speech(self, model: str, voice: str, text: str, output: Path, response_format: str = "mp3") -> None:
        payload = {
            "model": model,
            "voice": voice,
            "input": text,
            "response_format": response_format,
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/audio/speech",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=240) as response:
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(response.read())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise SystemExit(
                f"SiliconFlow TTS HTTP {exc.code}: {detail}\n"
                "Next step: check SILENTDECK_TTS_MODEL/SILENTDECK_TTS_VOICE, or let the TTS chain try edge-tts/Windows SAPI."
            ) from exc
        except urllib.error.URLError as exc:
            raise SystemExit(
                f"SiliconFlow TTS request failed: {exc}\n"
                "Next step: retry later, or let the TTS chain try edge-tts/Windows SAPI."
            ) from exc


def analyze_keyframe(client: SiliconFlowClient, model: str, segment: dict[str, Any], keyframe: Path, lang: str) -> dict[str, Any]:
    prompt = (
        "Analyze this keyframe from a silent presentation video. "
        "Return strict JSON with keys: visible_text (array of strings), visual_notes (string), "
        "intent (string), confidence (number from 0 to 1), risk_flags (array of strings). "
        "Describe only visible or strongly implied content. Do not invent facts. "
        f"Use {lang} for prose fields when appropriate."
    )
    content = [
        {"type": "image_url", "image_url": {"url": data_url(keyframe), "detail": "high"}},
        {"type": "text", "text": prompt},
    ]
    text = client.chat(model, [{"role": "user", "content": content}], max_tokens=1200)
    parsed = extract_json_object(text)
    if parsed:
        return {
            "visible_text": parsed.get("visible_text") or [],
            "visual_notes": str(parsed.get("visual_notes") or ""),
            "intent": str(parsed.get("intent") or ""),
            "confidence": float(parsed.get("confidence") or 0.5),
            "risk_flags": parsed.get("risk_flags") or [],
        }
    raise SystemExit(f"Could not parse model output as JSON for {segment['id']}: {text[:500]}")


def generate_narration(
    client: SiliconFlowClient,
    model: str,
    segment: dict[str, Any],
    analysis: dict[str, Any],
    lang: str,
) -> str:
    target_duration = float(segment["end"]) - float(segment["start"])
    max_chars = max(8, int(target_duration * 5))
    prompt = {
        "task": "Write spoken narration for one silent presentation video segment.",
        "language": lang,
        "target_duration_seconds": round(target_duration, 1),
        "max_chinese_characters": max_chars,
        "segment": {"id": segment["id"], "start": segment["start"], "end": segment["end"]},
        "visual_analysis": analysis,
        "rules": [
            "Return narration text only.",
            "Do not add facts not supported by the visual analysis.",
            "Keep it concise enough for the target duration.",
            "For Chinese narration, keep the text at or below max_chinese_characters.",
            "Use a natural presentation tone.",
        ],
    }
    messages = [
        {"role": "system", "content": "You write grounded narration for silent presentation videos."},
        {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
    ]
    return client.chat(model, messages, max_tokens=900).strip().strip('"')

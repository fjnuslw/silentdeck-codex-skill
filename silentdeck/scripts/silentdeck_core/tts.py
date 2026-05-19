"""TTS provider chain helpers for SilentDeck scripts."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .media import run_command
from .providers.siliconflow import SiliconFlowClient


def parse_tts_chain(value: str | None) -> list[str]:
    raw = value or "siliconflow,edge,sapi"
    aliases = {
        "provider": "siliconflow",
        "sf": "siliconflow",
        "edge-tts": "edge",
        "windows": "sapi",
        "windows-sapi": "sapi",
    }
    chain: list[str] = []
    for item in raw.split(","):
        name = aliases.get(item.strip().lower(), item.strip().lower())
        if name and name not in chain:
            chain.append(name)
    return chain or ["siliconflow", "edge", "sapi"]


def _ok_audio(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


def _message(exc: BaseException) -> str:
    if isinstance(exc, SystemExit):
        return str(exc.code)
    return str(exc)


def _siliconflow_tts(
    client: SiliconFlowClient | None,
    model: str,
    voice: str,
    text: str,
    output: Path,
) -> tuple[bool, str]:
    if client is None:
        return False, "SILICONFLOW_API_KEY is missing; provider TTS skipped."
    try:
        client.speech(model, voice, text, output)
    except SystemExit as exc:
        return False, _message(exc)
    if not _ok_audio(output):
        return False, "SiliconFlow TTS returned no audio bytes."
    return True, "SiliconFlow TTS produced audio."


def _edge_tts(text: str, voice: str, output: Path) -> tuple[bool, str]:
    edge = shutil.which("edge-tts") or shutil.which("edge-tts.exe")
    if not edge:
        return False, "edge-tts was not found. Next step: run `python -m pip install edge-tts` or remove edge from SILENTDECK_TTS_CHAIN."
    result = run_command([edge, "--voice", voice, "--text", text, "--write-media", str(output)])
    if result.returncode != 0:
        return False, (result.stderr or result.stdout or "edge-tts failed").strip()
    if not _ok_audio(output):
        return False, "edge-tts finished but did not create audio."
    return True, "edge-tts produced audio."


def _sapi_tts(text: str, voice: str, output: Path) -> tuple[bool, str]:
    powershell = shutil.which("powershell") or shutil.which("powershell.exe") or shutil.which("pwsh")
    if not powershell:
        return False, "PowerShell was not found; Windows SAPI TTS cannot run."

    output.parent.mkdir(parents=True, exist_ok=True)
    text_path = output.with_suffix(".sapi.txt")
    script_path = output.with_suffix(".sapi.ps1")
    text_path.write_text(text, encoding="utf-8")
    script_path.write_text(
        "\n".join(
            [
                "param([string]$TextPath, [string]$OutputPath, [string]$Voice)",
                "Add-Type -AssemblyName System.Speech",
                "$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer",
                "if ($Voice) { try { $synth.SelectVoice($Voice) } catch { Write-Error $_; exit 2 } }",
                "$content = Get-Content -LiteralPath $TextPath -Raw",
                "$synth.SetOutputToWaveFile($OutputPath)",
                "$synth.Speak($content)",
                "$synth.Dispose()",
            ]
        ),
        encoding="utf-8",
    )
    try:
        result = run_command(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script_path),
                "-TextPath",
                str(text_path),
                "-OutputPath",
                str(output),
                "-Voice",
                voice,
            ]
        )
    finally:
        for path in (text_path, script_path):
            try:
                path.unlink()
            except OSError:
                pass

    if result.returncode != 0:
        return False, (result.stderr or result.stdout or "Windows SAPI failed").strip()
    if not _ok_audio(output):
        return False, "Windows SAPI finished but did not create audio."
    return True, "Windows SAPI produced audio."


def synthesize_tts_chain(
    *,
    text: str,
    segment_id: str,
    output_dir: Path,
    chain: list[str],
    client: SiliconFlowClient | None,
    tts_model: str,
    tts_voice: str,
    edge_voice: str,
    sapi_voice: str,
) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    if not text.strip():
        return {
            "ok": False,
            "file": None,
            "provider": None,
            "attempts": [{"provider": "script-only", "ok": False, "message": "Narration text is empty."}],
        }

    output_dir.mkdir(parents=True, exist_ok=True)
    for provider in chain:
        if provider == "siliconflow":
            output = output_dir / f"{segment_id}_siliconflow.mp3"
            ok, message = _siliconflow_tts(client, tts_model, tts_voice, text, output)
        elif provider == "edge":
            output = output_dir / f"{segment_id}_edge.mp3"
            ok, message = _edge_tts(text, edge_voice, output)
        elif provider == "sapi":
            output = output_dir / f"{segment_id}_sapi.wav"
            ok, message = _sapi_tts(text, sapi_voice, output)
        else:
            output = output_dir / f"{segment_id}_{provider}.audio"
            ok, message = False, f"Unknown TTS provider '{provider}'."

        attempts.append({"provider": provider, "ok": ok, "message": message, "file": str(output)})
        if ok:
            return {"ok": True, "file": output, "provider": provider, "attempts": attempts}

    attempts.append(
        {
            "provider": "script-only",
            "ok": True,
            "message": "No TTS provider produced audio. Script and subtitles were kept for manual retry.",
            "file": None,
        }
    )
    return {"ok": False, "file": None, "provider": None, "attempts": attempts}

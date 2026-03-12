"""MiniMax TTS provider (海螺语音) - High quality text-to-speech."""

from __future__ import annotations
import httpx
from . import BaseTTSProvider, AudioResult


class MiniMaxTTSProvider(BaseTTSProvider):
    def __init__(self, api_key: str, api_host: str = "https://api.minimax.chat"):
        self.api_key = api_key
        self.api_host = api_host

    @property
    def name(self) -> str:
        return "minimax"

    @property
    def description(self) -> str:
        return "MiniMax TTS (speech-2.6-hd) - High quality, multi-language, emotional voice synthesis"

    async def speak(
        self,
        text: str,
        voice_id: str | None = None,
        speed: float = 1.0,
    ) -> AudioResult:
        body = {
            "model": "speech-2.6-hd",
            "text": text,
            "voice_setting": {
                "voice_id": voice_id or "female-shaonv",
                "speed": speed,
                "vol": 1.0,
                "pitch": 0,
            },
            "audio_setting": {
                "sample_rate": 32000,
                "bitrate": 128000,
                "format": "mp3",
                "channel": 1,
            },
            "language_boost": "auto",
            "output_format": "url",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.api_host}/v1/t2a_v2",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=60.0,
            )
            try:
                data = resp.json()
            except Exception:
                return AudioResult(status="failed", error=f"HTTP {resp.status_code}")

            base_resp = data.get("base_resp", {})
            if base_resp.get("status_code", 0) != 0:
                msg = base_resp.get("status_msg", "Unknown error")
                return AudioResult(status="failed", error=f"MiniMax TTS error: {msg}")

            audio = data.get("data", {}).get("audio", "")
            if audio.startswith("http"):
                return AudioResult(status="success", audio_url=audio)
            elif audio:
                return AudioResult(status="success", audio_data=bytes.fromhex(audio))
            else:
                return AudioResult(status="failed", error="No audio returned")

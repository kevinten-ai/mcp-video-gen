"""Google Cloud Text-to-Speech provider — Chirp 3 HD voices."""

from __future__ import annotations

import base64
import os

import httpx
from . import BaseTTSProvider, AudioResult

API_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"

# Chirp 3 HD voices (subset of most useful)
VOICES = {
    # English
    "charon": "en-US-Chirp3-HD-Charon",       # male
    "achernar": "en-US-Chirp3-HD-Achernar",   # female
    "puck": "en-US-Chirp3-HD-Puck",           # male
    "kore": "en-US-Chirp3-HD-Kore",           # female
    "fenrir": "en-US-Chirp3-HD-Fenrir",       # male
    "aoede": "en-US-Chirp3-HD-Aoede",         # female
    # Chinese
    "charon-zh": "cmn-CN-Chirp3-HD-Charon",   # male
    "achernar-zh": "cmn-CN-Chirp3-HD-Achernar", # female
    "kore-zh": "cmn-CN-Chirp3-HD-Kore",       # female
    # Japanese
    "charon-ja": "ja-JP-Chirp3-HD-Charon",    # male
    "achernar-ja": "ja-JP-Chirp3-HD-Achernar", # female
}


def _get_api_key() -> str:
    return os.getenv("GEMINI_API_KEY", "") or os.getenv("GCP_API_KEY", "")


def _get_auth(url: str) -> tuple[str, dict[str, str]]:
    api_key = _get_api_key()
    if api_key:
        return f"{url}?key={api_key}", {"Content-Type": "application/json"}
    import google.auth
    import google.auth.transport.requests
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    credentials.refresh(google.auth.transport.requests.Request())
    return url, {"Authorization": f"Bearer {credentials.token}", "Content-Type": "application/json"}


class GoogleTTSProvider(BaseTTSProvider):
    """Google Cloud TTS — Chirp 3 HD premium voices, 52 languages.

    Pricing: ~$30/1M chars (Chirp 3 HD), ~$16/1M chars (WaveNet).
    """

    @property
    def name(self) -> str:
        return "google-tts"

    @property
    def description(self) -> str:
        voices = ", ".join(VOICES.keys())
        return f"Google Cloud TTS (Chirp 3 HD) — Premium multi-language voices. IDs: {voices}"

    def _resolve_voice(self, voice_id: str | None) -> tuple[str, str]:
        """Resolve voice_id to (voice_name, language_code)."""
        if not voice_id:
            return "en-US-Chirp3-HD-Charon", "en-US"

        # Check shorthand first (e.g., "charon", "achernar-zh")
        if voice_id.lower() in VOICES:
            full_name = VOICES[voice_id.lower()]
        else:
            full_name = voice_id  # Allow full voice name directly

        # Extract language code from voice name pattern: "{lang}-Chirp3-HD-{name}"
        parts = full_name.split("-Chirp3-HD-")
        lang_code = parts[0] if len(parts) == 2 else "en-US"
        return full_name, lang_code

    async def speak(self, text: str, voice_id: str | None = None, speed: float = 1.0) -> AudioResult:
        voice_name, lang_code = self._resolve_voice(voice_id)

        body = {
            "input": {"text": text},
            "voice": {
                "languageCode": lang_code,
                "name": voice_name,
            },
            "audioConfig": {
                "audioEncoding": "MP3",
                "speakingRate": max(0.25, min(speed, 4.0)),
            },
        }

        try:
            authed_url, headers = _get_auth(API_URL)
        except Exception as e:
            return AudioResult(
                status="failed",
                error=f"Auth failed: {e}. Set GEMINI_API_KEY or run: gcloud auth application-default login",
            )

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                authed_url,
                headers=headers,
                json=body,
                timeout=30.0,
            )
            try:
                data = resp.json()
            except Exception:
                return AudioResult(status="failed", error=f"HTTP {resp.status_code}")

            if resp.status_code != 200:
                msg = data.get("error", {}).get("message", "Unknown error")
                return AudioResult(status="failed", error=f"Google TTS error ({resp.status_code}): {msg}")

            audio_b64 = data.get("audioContent", "")
            if not audio_b64:
                return AudioResult(status="failed", error="Empty audioContent")

            audio_bytes = base64.b64decode(audio_b64)
            return AudioResult(status="success", audio_data=audio_bytes)

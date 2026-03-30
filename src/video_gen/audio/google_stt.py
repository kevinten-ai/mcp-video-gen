"""Google Cloud Speech-to-Text provider — Chirp 2 model.

Uses Cloud STT v1 synchronous recognize API. Accepts local audio files
and returns timestamped transcript. Can be used with ffmpeg add_subtitles
for full subtitle pipeline.

Pricing: ~$0.016/minute. 60 minutes/month free.
"""

from __future__ import annotations

import base64
import os
from pathlib import Path

import httpx


def _get_api_key() -> str:
    return os.getenv("GEMINI_API_KEY", "") or os.getenv("GCP_API_KEY", "")


def _get_auth(url: str) -> tuple[str, dict[str, str]]:
    """Cloud STT v1 supports API key via query param."""
    api_key = _get_api_key()
    if api_key:
        return f"{url}?key={api_key}", {"Content-Type": "application/json"}
    # ADC fallback
    import google.auth
    import google.auth.transport.requests
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    credentials.refresh(google.auth.transport.requests.Request())
    return url, {"Authorization": f"Bearer {credentials.token}", "Content-Type": "application/json"}


async def transcribe(
    audio_path: str,
    language_code: str = "en-US",
) -> dict:
    """Transcribe audio file to text with word-level timestamps.

    Returns:
        {"transcript": str, "words": [{"word": str, "start": float, "end": float}], "error": str | None}
    """
    url = "https://speech.googleapis.com/v1/speech:recognize"

    # Load audio file
    path = Path(audio_path)
    if not path.exists():
        return {"transcript": "", "words": [], "error": f"File not found: {audio_path}"}

    audio_bytes = path.read_bytes()
    audio_b64 = base64.b64encode(audio_bytes).decode()

    # Detect encoding from extension
    ext = path.suffix.lower()
    encoding_map = {
        ".wav": "LINEAR16",
        ".flac": "FLAC",
        ".mp3": "MP3",
        ".ogg": "OGG_OPUS",
        ".webm": "WEBM_OPUS",
    }
    encoding = encoding_map.get(ext, "MP3")

    body = {
        "config": {
            "encoding": encoding,
            "languageCode": language_code,
            "model": "chirp_2",
            "enableWordTimeOffsets": True,
            "enableAutomaticPunctuation": True,
        },
        "audio": {
            "content": audio_b64,
        },
    }

    try:
        authed_url, headers = _get_auth(url)
    except Exception as e:
        return {"transcript": "", "words": [], "error": f"Auth failed: {e}"}

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            authed_url,
            headers=headers,
            json=body,
            timeout=120.0,
        )
        try:
            data = resp.json()
        except Exception:
            return {"transcript": "", "words": [], "error": f"HTTP {resp.status_code}"}

        if resp.status_code != 200:
            msg = data.get("error", {}).get("message", "Unknown error")
            return {"transcript": "", "words": [], "error": f"STT error ({resp.status_code}): {msg}"}

        # Parse results
        results = data.get("results", [])
        if not results:
            return {"transcript": "", "words": [], "error": "No speech detected"}

        transcript_parts = []
        words = []
        for result in results:
            alt = result.get("alternatives", [{}])[0]
            transcript_parts.append(alt.get("transcript", ""))
            for w in alt.get("words", []):
                start = float(w.get("startTime", "0s").rstrip("s"))
                end = float(w.get("endTime", "0s").rstrip("s"))
                words.append({"word": w.get("word", ""), "start": start, "end": end})

        return {
            "transcript": " ".join(transcript_parts),
            "words": words,
            "error": None,
        }

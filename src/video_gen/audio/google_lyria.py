"""Google Lyria 2 music generation provider — Vertex AI (synchronous predict)."""

from __future__ import annotations

import base64
import os

import httpx
from . import BaseMusicProvider, AudioResult


def _get_api_key() -> str:
    return os.getenv("GEMINI_API_KEY", "") or os.getenv("GCP_API_KEY", "")


def _get_auth(url: str) -> tuple[str, dict[str, str]]:
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


class GoogleLyriaProvider(BaseMusicProvider):
    """Lyria 2 — instrumental music generation via Vertex AI.

    Synchronous API (`:predict`), returns ~33s WAV audio per call.
    Pricing: ~$0.06/30s.
    """

    def __init__(self, project_id: str, region: str = "us-central1"):
        self.project_id = project_id
        self.region = region

    @property
    def name(self) -> str:
        return "google-lyria"

    @property
    def description(self) -> str:
        return "Google Lyria 2 (Vertex AI) — Instrumental music generation, ~33s WAV, ~$0.06/clip"

    async def generate(self, prompt: str, lyrics: str | None = None) -> AudioResult:
        url = (
            f"https://{self.region}-aiplatform.googleapis.com/v1/"
            f"projects/{self.project_id}/locations/{self.region}/"
            f"publishers/google/models/lyria-002:predict"
        )

        body = {
            "instances": [{"prompt": prompt}],
            "parameters": {"sample_count": 1},
        }

        try:
            authed_url, headers = _get_auth(url)
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
                timeout=120.0,
            )
            try:
                data = resp.json()
            except Exception:
                return AudioResult(status="failed", error=f"HTTP {resp.status_code}")

            if resp.status_code != 200:
                msg = data.get("error", {}).get("message", "Unknown error")
                return AudioResult(status="failed", error=f"Lyria API error ({resp.status_code}): {msg}")

            predictions = data.get("predictions", [])
            if not predictions:
                return AudioResult(status="failed", error="No audio in response")

            # Vertex AI predict API uses "bytesBase64Encoded" (same as Imagen)
            audio_b64 = predictions[0].get("bytesBase64Encoded", "") or predictions[0].get("audioContent", "")
            if not audio_b64:
                return AudioResult(status="failed", error="Empty audio response")

            audio_bytes = base64.b64decode(audio_b64)
            return AudioResult(status="success", audio_data=audio_bytes)

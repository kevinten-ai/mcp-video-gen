"""Google Veo provider — Vertex AI video generation (Veo 2/3)."""

from __future__ import annotations

import base64
import ipaddress
from pathlib import Path
from datetime import datetime
import os
from urllib.parse import urlsplit

import httpx
from . import BaseProvider, VideoResult

# Supported models
MODELS = {
    "veo-2.0-generate-001": {"name": "Veo 2", "resolution": "720p", "pricing": "~$0.50/s"},
    "veo-3.0-generate-001": {"name": "Veo 3", "resolution": "1080p", "pricing": "~$0.75/s"},
    "veo-3.0-fast-generate-001": {"name": "Veo 3 Fast", "resolution": "1080p", "pricing": "~$0.15/s"},
    "veo-3.1-generate-001": {"name": "Veo 3.1", "resolution": "4K", "pricing": "~$0.75/s"},
    "veo-3.1-fast-generate-001": {"name": "Veo 3.1 Fast", "resolution": "1080p", "pricing": "~$0.10/s"},
}

DEFAULT_MODEL = os.getenv("VEO_MODEL", "veo-3.1-fast-generate-001")
GCS_BUCKET = os.getenv("VEO_GCS_BUCKET", "")
MAX_REFERENCE_IMAGE_BYTES = 20 * 1024 * 1024


def _is_safe_remote_image_url(url: str) -> bool:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False

    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith((".localhost", ".local")):
        return False

    try:
        return ipaddress.ip_address(hostname).is_global
    except ValueError:
        return True


def _get_api_key() -> str:
    """Read API key at call time (not import time) so env changes are picked up."""
    return os.getenv("GEMINI_API_KEY", "") or os.getenv("GCP_API_KEY", "")


def _get_access_token() -> str:
    """Get OAuth2 access token via Application Default Credentials."""
    import google.auth
    import google.auth.transport.requests

    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    credentials.refresh(google.auth.transport.requests.Request())
    return credentials.token


def _get_auth(url: str) -> tuple[str, dict[str, str]]:
    """Get authenticated URL and headers. Prefers API key, falls back to ADC."""
    api_key = _get_api_key()
    if api_key:
        return f"{url}?key={api_key}", {"Content-Type": "application/json"}
    token = _get_access_token()
    return url, {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


class VeoProvider(BaseProvider):
    def __init__(self, project_id: str, region: str = "us-central1"):
        self.project_id = project_id
        self.region = region

    @property
    def name(self) -> str:
        return "veo"

    @property
    def description(self) -> str:
        models = ", ".join(MODELS.keys())
        return f"Google Veo (Vertex AI) — High quality video generation. Models: {models}. Default: {DEFAULT_MODEL}"

    @property
    def free_tier_info(self) -> str:
        return "Uses GCP credits/billing. No free tier."

    @property
    def models(self) -> dict:
        return MODELS

    @property
    def default_model(self) -> str:
        return DEFAULT_MODEL

    async def _load_image(self, image_url: str) -> dict | None:
        """Load image from local path or URL, return Vertex AI image dict."""
        try:
            if image_url.startswith(("http://", "https://")):
                if not _is_safe_remote_image_url(image_url):
                    return None
                async with httpx.AsyncClient() as client:
                    async with client.stream("GET", image_url, timeout=30.0) as resp:
                        if resp.status_code != 200:
                            return None
                        content_length = resp.headers.get("content-length")
                        if content_length:
                            try:
                                if not 0 <= int(content_length) <= MAX_REFERENCE_IMAGE_BYTES:
                                    return None
                            except ValueError:
                                return None
                        mime = resp.headers.get("content-type", "image/png").split(";", 1)[0].strip()
                        if not mime.startswith("image/"):
                            return None
                        chunks = []
                        size = 0
                        async for chunk in resp.aiter_bytes():
                            size += len(chunk)
                            if size > MAX_REFERENCE_IMAGE_BYTES:
                                return None
                            chunks.append(chunk)
                        if size == 0:
                            return None
                        img_b64 = base64.b64encode(b"".join(chunks)).decode()
                        return {"bytesBase64Encoded": img_b64, "mimeType": mime}
            elif image_url.startswith("gs://"):
                return {"gcsUri": image_url, "mimeType": "image/png"}
            else:
                # Local file path
                path = Path(image_url)
                if path.is_file() and path.stat().st_size <= MAX_REFERENCE_IMAGE_BYTES:
                    img_b64 = base64.b64encode(path.read_bytes()).decode()
                    mime = "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
                    return {"bytesBase64Encoded": img_b64, "mimeType": mime}
        except Exception:
            pass
        return None

    def _base_url(self, model: str) -> str:
        return (
            f"https://{self.region}-aiplatform.googleapis.com/v1/"
            f"projects/{self.project_id}/locations/{self.region}/"
            f"publishers/google/models/{model}"
        )

    async def generate(
        self,
        prompt: str,
        duration: int = 8,
        aspect_ratio: str = "16:9",
        image_url: str | None = None,
        model: str | None = None,
    ) -> VideoResult:
        model = model or DEFAULT_MODEL
        url = f"{self._base_url(model)}:predictLongRunning"

        parameters: dict = {
            "sampleCount": 1,
            "durationSeconds": min(max(duration, 5), 8),
            "aspectRatio": aspect_ratio,
            "enhancePrompt": True,
            "personGeneration": "allow_adult",
        }
        if GCS_BUCKET:
            parameters["storageUri"] = f"gs://{GCS_BUCKET}/"

        instance: dict = {"prompt": prompt}

        # img2vid: add reference image
        if image_url:
            image_data = await self._load_image(image_url)
            if image_data:
                instance["image"] = image_data

        body = {
            "instances": [instance],
            "parameters": parameters,
        }

        try:
            authed_url, headers = _get_auth(url)
        except Exception as e:
            return VideoResult(
                task_id="", status="failed",
                error=f"Auth failed: {e}. Set GEMINI_API_KEY or run: gcloud auth application-default login",
            )

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                authed_url,
                headers=headers,
                json=body,
                timeout=60.0,
            )
            try:
                data = resp.json()
            except Exception:
                return VideoResult(task_id="", status="failed", error=f"HTTP {resp.status_code}")

            if resp.status_code != 200:
                msg = data.get("error", {}).get("message", "Unknown error")
                return VideoResult(task_id="", status="failed", error=f"Veo API error ({resp.status_code}): {msg}")

            # Response: {"name": "projects/.../operations/OPERATION_ID"}
            operation_name = data.get("name", "")
            if not operation_name:
                return VideoResult(task_id="", status="failed", error="No operation name returned")

            return VideoResult(task_id=operation_name, status="processing")

    async def query(self, task_id: str) -> VideoResult:
        # task_id is the full operation name:
        # "projects/{PROJECT}/locations/{REGION}/publishers/google/models/{MODEL}/operations/{OP_ID}"
        # Extract model from it to build the fetchPredictOperation URL
        try:
            parts = task_id.split("/")
            model_idx = parts.index("models") + 1
            model = parts[model_idx]
        except (ValueError, IndexError):
            model = DEFAULT_MODEL

        url = f"{self._base_url(model)}:fetchPredictOperation"

        try:
            authed_url, headers = _get_auth(url)
        except Exception as e:
            return VideoResult(
                task_id=task_id, status="failed",
                error=f"Auth failed: {e}",
            )

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                authed_url,
                headers=headers,
                json={"operationName": task_id},
                timeout=60.0,
            )
            try:
                data = resp.json()
            except Exception:
                return VideoResult(task_id=task_id, status="failed", error=f"HTTP {resp.status_code}")

            if resp.status_code != 200:
                msg = data.get("error", {}).get("message", "Unknown error")
                return VideoResult(task_id=task_id, status="failed", error=f"Veo query error: {msg}")

            done = data.get("done", False)
            if not done:
                return VideoResult(task_id=task_id, status="processing")

            # Done — extract video
            response = data.get("response", {})
            videos = response.get("videos", [])

            if not videos:
                filtered = response.get("raiMediaFilteredCount", 0)
                if filtered:
                    return VideoResult(task_id=task_id, status="failed", error=f"Video blocked by safety filter ({filtered} filtered)")
                return VideoResult(task_id=task_id, status="failed", error="No video in response")

            video = videos[0]

            # GCS mode: return gcsUri as video_url
            if "gcsUri" in video:
                return VideoResult(task_id=task_id, status="success", video_url=video["gcsUri"])

            # Base64 mode: decode and save locally
            if "bytesBase64Encoded" in video:
                video_bytes = base64.b64decode(video["bytesBase64Encoded"])
                output_dir = os.getenv("VIDEO_OUTPUT_DIR", os.path.join(os.getcwd(), "output"))
                out = Path(output_dir)
                out.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath = out / f"veo_{timestamp}.mp4"
                filepath.write_bytes(video_bytes)
                return VideoResult(task_id=task_id, status="success", video_url=str(filepath))

            return VideoResult(task_id=task_id, status="failed", error="Unknown video format in response")

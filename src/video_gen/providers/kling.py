"""Kling AI provider (可灵) - 66 free credits/day."""

from __future__ import annotations
import os
import time
import jwt
import httpx
from . import BaseProvider, VideoResult

API_BASE = "https://api.klingai.com"


class KlingProvider(BaseProvider):
    MODELS = {
        "kling-v3": {"name": "Kling 3.0", "resolution": "1080p", "pricing": "Credit-based"},
        "kling-v2-master": {"name": "Kling 2.0 Master", "resolution": "720p", "pricing": "Credit-based"},
    }

    def __init__(self, access_key: str, secret_key: str):
        self.access_key = access_key
        self.secret_key = secret_key
        self._default_model = os.getenv("KLING_MODEL", "kling-v3")

    @property
    def name(self) -> str:
        return "kling"

    @property
    def description(self) -> str:
        return "Kling AI - High quality video generation (720p, 5-10s)"

    @property
    def free_tier_info(self) -> str:
        return "66 free credits/day (1 standard 5s video = 2 credits)"

    @property
    def models(self) -> dict:
        return self.MODELS

    @property
    def default_model(self) -> str:
        return self._default_model

    def _make_token(self) -> str:
        now = int(time.time())
        payload = {
            "iss": self.access_key,
            "exp": now + 1800,
            "nbf": now - 5,
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256")

    async def generate(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        image_url: str | None = None,
        model: str | None = None,
    ) -> VideoResult:
        model = model or self._default_model

        body = {
            "model_name": model,
            "prompt": prompt,
            "mode": "std",
            "aspect_ratio": aspect_ratio,
            "duration": str(duration),
        }

        token = self._make_token()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{API_BASE}/v1/videos/text2video",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=30.0,
            )
            try:
                data = resp.json()
            except Exception:
                return VideoResult(task_id="", status="failed", error=f"HTTP {resp.status_code}")

            if data.get("code") != 0:
                msg = data.get("message", "Unknown error")
                return VideoResult(task_id="", status="failed", error=f"Kling API error: {msg}")

            task_id = data.get("data", {}).get("task_id", "")
            return VideoResult(task_id=task_id, status="processing")

    async def query(self, task_id: str) -> VideoResult:
        token = self._make_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{API_BASE}/v1/videos/text2video/{task_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30.0,
            )
            try:
                data = resp.json()
            except Exception:
                return VideoResult(task_id=task_id, status="failed", error=f"HTTP {resp.status_code}")

            if data.get("code") != 0:
                msg = data.get("message", "Unknown error")
                return VideoResult(task_id=task_id, status="failed", error=f"Kling API error: {msg}")

            task_data = data.get("data", {})
            status = task_data.get("task_status", "")

            if status == "succeed":
                videos = task_data.get("task_result", {}).get("videos", [])
                url = videos[0]["url"] if videos else None
                return VideoResult(task_id=task_id, status="success", video_url=url)
            elif status == "failed":
                msg = task_data.get("task_status_msg", "Video generation failed")
                return VideoResult(task_id=task_id, status="failed", error=msg)
            else:
                return VideoResult(task_id=task_id, status="processing")

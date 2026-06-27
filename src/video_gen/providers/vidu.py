"""Vidu provider (生数科技) - Promotional free credits."""

from __future__ import annotations
import os
import httpx
from . import BaseProvider, VideoResult

API_BASE = "https://api.vidu.com"


class ViduProvider(BaseProvider):
    MODELS = {
        "q2-turbo": {"name": "Vidu Q2 Turbo", "resolution": "1080p", "pricing": "~$0.40/video"},
        "q2-pro": {"name": "Vidu Q2 Pro", "resolution": "720p", "pricing": "~$0.20/video"},
        "vidu-2.0": {"name": "Vidu 2.0", "resolution": "720p", "pricing": "Credit-based"},
    }

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._default_model = os.getenv("VIDU_MODEL", "q2-turbo")

    @property
    def name(self) -> str:
        return "vidu"

    @property
    def description(self) -> str:
        return "Vidu Q2 (生数科技) - High quality video generation (up to 1080P, 4-10s)"

    @property
    def free_tier_info(self) -> str:
        return "Apply for 200 free API credits at platform.vidu.com"

    @property
    def models(self) -> dict:
        return self.MODELS

    @property
    def default_model(self) -> str:
        return self._default_model

    async def generate(
        self,
        prompt: str,
        duration: int = 4,
        aspect_ratio: str = "16:9",
        image_url: str | None = None,
        model: str | None = None,
    ) -> VideoResult:
        model = model or self._default_model

        body = {
            "model": model,
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "resolution": "1080p",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{API_BASE}/ent/v2/text2video",
                headers={
                    "Authorization": f"Token {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=30.0,
            )
            try:
                data = resp.json()
            except Exception:
                return VideoResult(task_id="", status="failed", error=f"HTTP {resp.status_code}")

            if resp.status_code not in (200, 201):
                msg = data.get("message", "") or data.get("error", "Unknown error")
                return VideoResult(task_id="", status="failed", error=f"Vidu API error: {msg}")

            task_id = data.get("task_id", "") or data.get("id", "")
            if not task_id:
                return VideoResult(task_id="", status="failed", error="No task_id returned")
            return VideoResult(task_id=task_id, status="processing")

    async def query(self, task_id: str) -> VideoResult:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{API_BASE}/ent/v2/tasks/{task_id}",
                headers={"Authorization": f"Token {self.api_key}"},
                timeout=30.0,
            )
            try:
                data = resp.json()
            except Exception:
                return VideoResult(task_id=task_id, status="failed", error=f"HTTP {resp.status_code}")

            state = data.get("state", "")

            if state == "success":
                creations = data.get("creations", [])
                url = creations[0].get("url", "") if creations else ""
                return VideoResult(task_id=task_id, status="success", video_url=url)
            elif state in ("fail", "failed"):
                msg = data.get("err_msg", "Video generation failed")
                return VideoResult(task_id=task_id, status="failed", error=msg)
            else:
                return VideoResult(task_id=task_id, status="processing")

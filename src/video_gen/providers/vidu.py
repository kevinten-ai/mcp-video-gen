"""Vidu provider (生数科技) - Promotional free credits."""

from __future__ import annotations
import httpx
from . import BaseProvider, VideoResult

API_BASE = "https://api.vidu.com"


class ViduProvider(BaseProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    @property
    def name(self) -> str:
        return "vidu"

    @property
    def description(self) -> str:
        return "Vidu (生数科技) - High quality video generation with Vidu Q1 model"

    @property
    def free_tier_info(self) -> str:
        return "Apply for 200 free API credits at platform.vidu.com"

    async def generate(
        self,
        prompt: str,
        duration: int = 4,
        aspect_ratio: str = "16:9",
        image_url: str | None = None,
    ) -> VideoResult:
        body = {
            "model": "vidu-2.0",
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "resolution": "720p",
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

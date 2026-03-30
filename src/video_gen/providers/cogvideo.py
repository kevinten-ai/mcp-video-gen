"""CogVideoX-Flash provider (智谱清影) - Free unlimited video generation."""

from __future__ import annotations
import httpx
from . import BaseProvider, VideoResult

API_BASE = "https://open.bigmodel.cn/api/paas/v4"


class CogVideoProvider(BaseProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    @property
    def name(self) -> str:
        return "cogvideo"

    @property
    def description(self) -> str:
        return "CogVideoX-Flash by Zhipu AI - Free unlimited video generation (1440x960, 6s)"

    @property
    def free_tier_info(self) -> str:
        return "Completely free, no daily limit"

    async def generate(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        image_url: str | None = None,
    ) -> VideoResult:
        size_map = {
            "16:9": "1920x1080",
            "9:16": "1080x1920",
            "1:1": "1024x1024",
        }
        size = size_map.get(aspect_ratio, "1920x1080")

        body = {
            "model": "cogvideox-flash",
            "prompt": prompt,
            "size": size,
            "quality": "speed",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{API_BASE}/videos/generations",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=30.0,
            )
            try:
                data = resp.json()
            except Exception:
                return VideoResult(task_id="", status="failed", error=f"HTTP {resp.status_code}")

            if resp.status_code != 200:
                msg = data.get("error", {}).get("message", "") or data.get("message", "Unknown error")
                return VideoResult(task_id="", status="failed", error=f"CogVideo API error: {msg}")

            task_id = data.get("id", "")
            return VideoResult(task_id=task_id, status="processing")

    async def query(self, task_id: str) -> VideoResult:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{API_BASE}/async-result/{task_id}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30.0,
            )
            try:
                data = resp.json()
            except Exception:
                return VideoResult(task_id=task_id, status="failed", error=f"HTTP {resp.status_code}")

            task_status = data.get("task_status", "")

            if task_status == "SUCCESS":
                videos = data.get("video_result", [])
                url = videos[0]["url"] if videos else None
                return VideoResult(task_id=task_id, status="success", video_url=url)
            elif task_status == "FAIL":
                return VideoResult(task_id=task_id, status="failed", error="Video generation failed")
            else:
                return VideoResult(task_id=task_id, status="processing")

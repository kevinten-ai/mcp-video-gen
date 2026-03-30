"""SiliconFlow provider (硅基流动) - Registration bonus credits."""

from __future__ import annotations
import httpx
from . import BaseProvider, VideoResult

API_BASE = "https://api.siliconflow.com/v1"


class SiliconFlowProvider(BaseProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    @property
    def name(self) -> str:
        return "siliconflow"

    @property
    def description(self) -> str:
        return "SiliconFlow (硅基流动) - Wan 2.2 video generation, fast and affordable"

    @property
    def free_tier_info(self) -> str:
        return "$1 registration bonus (~3 free videos), then ~$0.29/video"

    async def generate(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        image_url: str | None = None,
    ) -> VideoResult:
        size_map = {
            "16:9": "1280x720",
            "9:16": "720x1280",
            "1:1": "720x720",
        }
        image_size = size_map.get(aspect_ratio, "1280x720")

        body = {
            "model": "Wan-AI/Wan2.1-T2V-14B",
            "prompt": prompt,
            "image_size": image_size,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{API_BASE}/video/submit",
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
                msg = data.get("message", "") or data.get("error", "Unknown error")
                return VideoResult(task_id="", status="failed", error=f"SiliconFlow API error: {msg}")

            request_id = data.get("requestId", "")
            if not request_id:
                return VideoResult(task_id="", status="failed", error="No requestId returned")
            return VideoResult(task_id=request_id, status="processing")

    async def query(self, task_id: str) -> VideoResult:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{API_BASE}/video/status",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"requestId": task_id},
                timeout=30.0,
            )
            try:
                data = resp.json()
            except Exception:
                return VideoResult(task_id=task_id, status="failed", error=f"HTTP {resp.status_code}")

            status = data.get("status", "")

            if status == "Succeed":
                results = data.get("results", {})
                videos = results.get("videos", [])
                url = videos[0].get("url", "") if videos else ""
                return VideoResult(task_id=task_id, status="success", video_url=url)
            elif status in ("Failed", "InternalError"):
                reason = data.get("reason", "Video generation failed")
                return VideoResult(task_id=task_id, status="failed", error=reason)
            else:
                return VideoResult(task_id=task_id, status="processing")

"""Alibaba DashScope / Wan provider (通义万相) - 50s free video quota."""

from __future__ import annotations
import httpx
from . import BaseProvider, VideoResult

API_BASE = "https://dashscope.aliyuncs.com/api/v1"


class DashScopeProvider(BaseProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    @property
    def name(self) -> str:
        return "dashscope"

    @property
    def description(self) -> str:
        return "Alibaba Wan 2.6 (通义万相) - High quality video generation (up to 1080P, 5-10s)"

    @property
    def free_tier_info(self) -> str:
        return "50 seconds free for new users (valid 90 days)"

    async def generate(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "16:9",
    ) -> VideoResult:
        size_map = {
            "16:9": "1280*720",
            "9:16": "720*1280",
            "1:1": "720*720",
        }
        size = size_map.get(aspect_ratio, "1280*720")

        body = {
            "model": "wan2.6-t2v",
            "input": {
                "prompt": prompt,
            },
            "parameters": {
                "size": size,
                "duration": duration,
                "prompt_extend": True,
            },
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{API_BASE}/services/aigc/video-generation/video-synthesis",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "X-DashScope-Async": "enable",
                },
                json=body,
                timeout=30.0,
            )
            try:
                data = resp.json()
            except Exception:
                return VideoResult(task_id="", status="failed", error=f"HTTP {resp.status_code}")

            if resp.status_code != 200:
                msg = data.get("message", "") or data.get("error", {}).get("message", "Unknown error")
                return VideoResult(task_id="", status="failed", error=f"DashScope API error: {msg}")

            task_id = data.get("output", {}).get("task_id", "")
            if not task_id:
                return VideoResult(task_id="", status="failed", error="No task_id returned")
            return VideoResult(task_id=task_id, status="processing")

    async def query(self, task_id: str) -> VideoResult:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{API_BASE}/tasks/{task_id}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30.0,
            )
            try:
                data = resp.json()
            except Exception:
                return VideoResult(task_id=task_id, status="failed", error=f"HTTP {resp.status_code}")

            output = data.get("output", {})
            task_status = output.get("task_status", "")

            if task_status == "SUCCEEDED":
                video_url = output.get("video_url", "")
                return VideoResult(task_id=task_id, status="success", video_url=video_url)
            elif task_status in ("FAILED", "UNKNOWN"):
                msg = output.get("message", "Video generation failed")
                return VideoResult(task_id=task_id, status="failed", error=msg)
            else:
                return VideoResult(task_id=task_id, status="processing")

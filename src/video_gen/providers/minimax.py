"""MiniMax Hailuo provider (海螺) - Paid video generation."""

from __future__ import annotations
import httpx
from . import BaseProvider, VideoResult


class MiniMaxProvider(BaseProvider):
    def __init__(self, api_key: str, api_host: str = "https://api.minimax.chat"):
        self.api_key = api_key
        self.api_host = api_host

    @property
    def name(self) -> str:
        return "minimax"

    @property
    def description(self) -> str:
        return "MiniMax Hailuo 2.3 - High quality video generation (up to 1080P, 6-10s)"

    @property
    def free_tier_info(self) -> str:
        return "Paid. ~$0.10/video (512P 6s) to ~$0.52/video (1080P 6s)"

    async def generate(
        self,
        prompt: str,
        duration: int = 6,
        aspect_ratio: str = "16:9",
        image_url: str | None = None,
    ) -> VideoResult:
        body = {
            "model": "MiniMax-Hailuo-2.3",
            "prompt": prompt,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.api_host}/v1/video_generation",
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

            base_resp = data.get("base_resp", {})
            if base_resp.get("status_code", 0) != 0:
                msg = base_resp.get("status_msg", "Unknown error")
                return VideoResult(task_id="", status="failed", error=f"MiniMax API error: {msg}")

            task_id = data.get("task_id", "")
            return VideoResult(task_id=task_id, status="processing")

    async def query(self, task_id: str) -> VideoResult:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.api_host}/v1/query/video_generation",
                headers={"Authorization": f"Bearer {self.api_key}"},
                params={"task_id": task_id},
                timeout=30.0,
            )
            try:
                data = resp.json()
            except Exception:
                return VideoResult(task_id=task_id, status="failed", error=f"HTTP {resp.status_code}")

            base_resp = data.get("base_resp", {})
            if base_resp.get("status_code", 0) != 0:
                msg = base_resp.get("status_msg", "Unknown error")
                return VideoResult(task_id=task_id, status="failed", error=f"MiniMax API error: {msg}")

            status = data.get("status", "")

            if status == "Success":
                file_id = data.get("file_id", "")
                url = f"{self.api_host}/v1/files/retrieve?file_id={file_id}" if file_id else None
                # Hailuo returns download_url directly in some API versions
                url = data.get("download_url") or url
                return VideoResult(task_id=task_id, status="success", video_url=url)
            elif status in ("Failed", "Timeout"):
                return VideoResult(task_id=task_id, status="failed", error=f"Video generation {status}")
            else:
                return VideoResult(task_id=task_id, status="processing")

"""Volcengine Ark Seedance provider for video generation."""

from __future__ import annotations

import os
from typing import Any

import httpx

from . import BaseProvider, VideoResult

DEFAULT_API_BASE = "https://ark.cn-beijing.volces.com/api/v3"
DEFAULT_MODEL = "doubao-seedance-2-0-fast-260128"
MODELS = {
    "doubao-seedance-2-0-fast-260128": {
        "name": "Seedance 2.0 Fast",
        "resolution": "720p",
        "pricing": "Ark video billing",
    },
}


def _api_base() -> str:
    """Return a video-generation Ark API base URL, never the CodingPlan chat URL."""
    configured = os.getenv("ARK_VIDEO_BASE_URL", "").strip()
    if not configured:
        configured = os.getenv("ARK_BASE_URL", "").strip()
    if not configured or "/api/coding/" in configured:
        configured = DEFAULT_API_BASE
    return configured.rstrip("/")


def _payload(data: dict[str, Any]) -> dict[str, Any]:
    nested = data.get("data")
    return nested if isinstance(nested, dict) else data


def _message(data: dict[str, Any]) -> str:
    error = data.get("error")
    if isinstance(error, dict):
        return str(error.get("message") or error.get("code") or error)
    return str(data.get("message") or data.get("msg") or error or "Unknown error")


def _task_id(data: dict[str, Any]) -> str:
    payload = _payload(data)
    for key in ("id", "task_id", "taskId"):
        value = payload.get(key)
        if value:
            return str(value)
    return ""


def _status(data: dict[str, Any]) -> str:
    payload = _payload(data)
    for key in ("status", "task_status", "state"):
        value = payload.get(key)
        if value:
            return str(value).lower()
    return ""


def _video_url(value: Any) -> str | None:
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        return value
    if isinstance(value, dict):
        for key in ("video_url", "url", "download_url", "uri"):
            found = _video_url(value.get(key))
            if found:
                return found
        for key in ("content", "result", "output", "video", "videos", "video_result"):
            found = _video_url(value.get(key))
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = _video_url(item)
            if found:
                return found
    return None


class ArkVideoProvider(BaseProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_base = _api_base()
        self.model = os.getenv("ARK_VIDEO_MODEL", DEFAULT_MODEL)
        self.resolution = os.getenv("ARK_VIDEO_RESOLUTION", "720p")

    @property
    def name(self) -> str:
        return "ark"

    @property
    def description(self) -> str:
        return "Volcengine Ark Seedance video generation (async task API)"

    @property
    def free_tier_info(self) -> str:
        return "Paid Ark video generation; may not be covered by CodingPlan chat quota"

    @property
    def models(self) -> dict:
        return MODELS

    @property
    def default_model(self) -> str:
        return self.model

    def _prompt_text(self, prompt: str, duration: int) -> str:
        duration = max(1, min(int(duration or 5), 10))
        return f"{prompt.strip()} --resolution {self.resolution} --duration {duration}"

    async def generate(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        image_url: str | None = None,
        model: str | None = None,
    ) -> VideoResult:
        content: list[dict[str, Any]] = [
            {"type": "text", "text": self._prompt_text(prompt, duration)}
        ]
        if image_url:
            content.append({
                "type": "image_url",
                "image_url": {"url": image_url},
                "role": "first_frame",
            })

        body = {
            "model": model or self.model,
            "content": content,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.api_base}/contents/generations/tasks",
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

            if resp.status_code not in (200, 201, 202):
                return VideoResult(task_id="", status="failed", error=f"Ark video API error: {_message(data)}")

            task_id = _task_id(data)
            if not task_id:
                return VideoResult(task_id="", status="failed", error=f"Ark video API did not return a task id: {_message(data)}")
            return VideoResult(task_id=task_id, status="processing")

    async def query(self, task_id: str) -> VideoResult:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.api_base}/contents/generations/tasks/{task_id}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30.0,
            )
            try:
                data = resp.json()
            except Exception:
                return VideoResult(task_id=task_id, status="failed", error=f"HTTP {resp.status_code}")

            if resp.status_code != 200:
                return VideoResult(task_id=task_id, status="failed", error=f"Ark video API error: {_message(data)}")

            state = _status(data)
            if state in ("succeeded", "success", "done", "completed"):
                return VideoResult(task_id=task_id, status="success", video_url=_video_url(_payload(data)))
            if state in ("failed", "fail", "error", "cancelled", "canceled"):
                return VideoResult(task_id=task_id, status="failed", error=_message(_payload(data)))
            return VideoResult(task_id=task_id, status="processing")

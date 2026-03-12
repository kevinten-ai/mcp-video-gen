from __future__ import annotations
import asyncio
import os
from datetime import datetime
from pathlib import Path

import httpx
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio

from .providers import (
    BaseProvider,
    VideoResult,
    register_provider,
    get_provider,
    list_providers as get_all_providers,
)
from .providers.cogvideo import CogVideoProvider
from .providers.kling import KlingProvider
from .providers.minimax import MiniMaxProvider
from .providers.dashscope import DashScopeProvider
from .providers.siliconflow import SiliconFlowProvider
from .providers.vidu import ViduProvider

VIDEO_OUTPUT_DIR = os.getenv("VIDEO_OUTPUT_DIR", os.path.join(os.getcwd(), "output"))

server = Server("mcp-video-gen")


def _init_providers() -> None:
    """Register providers based on available environment variables."""
    cogvideo_key = os.getenv("COGVIDEO_API_KEY", "")
    if cogvideo_key:
        register_provider(CogVideoProvider(cogvideo_key))

    kling_ak = os.getenv("KLING_ACCESS_KEY", "")
    kling_sk = os.getenv("KLING_SECRET_KEY", "")
    if kling_ak and kling_sk:
        register_provider(KlingProvider(kling_ak, kling_sk))

    minimax_key = os.getenv("MINIMAX_API_KEY", "")
    if minimax_key:
        minimax_host = os.getenv("MINIMAX_API_HOST", "https://api.minimax.chat")
        register_provider(MiniMaxProvider(minimax_key, minimax_host))

    dashscope_key = os.getenv("DASHSCOPE_API_KEY", "")
    if dashscope_key:
        register_provider(DashScopeProvider(dashscope_key))

    siliconflow_key = os.getenv("SILICONFLOW_API_KEY", "")
    if siliconflow_key:
        register_provider(SiliconFlowProvider(siliconflow_key))

    vidu_key = os.getenv("VIDU_API_KEY", "")
    if vidu_key:
        register_provider(ViduProvider(vidu_key))


_init_providers()


def _default_provider_name() -> str | None:
    """Return the default provider name (prefer free providers)."""
    providers = get_all_providers()
    for name in ("cogvideo", "dashscope", "kling", "siliconflow", "vidu", "minimax"):
        if name in providers:
            return name
    return None


async def _try_download(url: str, output_dir: str, prefix: str) -> str | None:
    """Try to download video to local disk. Returns filepath or None on failure."""
    try:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = out / f"{prefix}_{timestamp}.mp4"
        async with httpx.AsyncClient(verify=False, follow_redirects=True) as client:
            resp = await client.get(url, timeout=120.0)
            if resp.status_code == 200 and len(resp.content) > 0:
                filepath.write_bytes(resp.content)
                return str(filepath)
    except Exception:
        pass
    return None


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    providers = get_all_providers()
    provider_names = list(providers.keys())
    default = _default_provider_name()

    tools = [
        types.Tool(
            name="generate_video",
            description=f"Generate a video from a text prompt. Available providers: {', '.join(provider_names) or 'none configured'}. Default: {default or 'none'}.",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Text prompt describing the video to generate",
                    },
                    "provider": {
                        "type": "string",
                        "description": f"Provider to use: {', '.join(provider_names)}. Default: {default}",
                        "enum": provider_names if provider_names else ["none"],
                    },
                    "duration": {
                        "type": "integer",
                        "description": "Video duration in seconds (5 or 10). Default: 5",
                        "default": 5,
                    },
                    "aspect_ratio": {
                        "type": "string",
                        "description": "Aspect ratio: 16:9, 9:16, or 1:1. Default: 16:9",
                        "default": "16:9",
                    },
                    "output_directory": {
                        "type": "string",
                        "description": "Directory to save video. Optional.",
                    },
                },
                "required": ["prompt"],
            },
        ),
        types.Tool(
            name="query_video_status",
            description="Query the status of a video generation task and download the result.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "Task ID returned by generate_video",
                    },
                    "provider": {
                        "type": "string",
                        "description": f"Provider that was used: {', '.join(provider_names)}",
                        "enum": provider_names if provider_names else ["none"],
                    },
                    "output_directory": {
                        "type": "string",
                        "description": "Directory to save video. Optional.",
                    },
                },
                "required": ["task_id", "provider"],
            },
        ),
        types.Tool(
            name="list_providers",
            description="List all available video generation providers and their free tier info.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]
    return tools


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent]:
    if not arguments:
        arguments = {}

    if name == "list_providers":
        providers = get_all_providers()
        if not providers:
            return [types.TextContent(type="text", text="No providers configured. Set API keys in environment variables.")]
        lines = []
        for p in providers.values():
            lines.append(f"**{p.name}** - {p.description}\n  Free tier: {p.free_tier_info}")
        return [types.TextContent(type="text", text="\n\n".join(lines))]

    if name == "generate_video":
        prompt = arguments.get("prompt")
        if not prompt:
            return [types.TextContent(type="text", text="Missing prompt")]

        provider_name = arguments.get("provider") or _default_provider_name()
        if not provider_name:
            return [types.TextContent(type="text", text="No providers configured. Set API keys in environment variables.")]

        provider = get_provider(provider_name)
        if not provider:
            available = ", ".join(get_all_providers().keys())
            return [types.TextContent(type="text", text=f"Unknown provider: {provider_name}. Available: {available}")]

        duration = arguments.get("duration", 5)
        aspect_ratio = arguments.get("aspect_ratio", "16:9")

        result = await provider.generate(prompt, duration=duration, aspect_ratio=aspect_ratio)

        if result.status == "failed":
            return [types.TextContent(type="text", text=f"Failed: {result.error}")]

        return [types.TextContent(
            type="text",
            text=f"Video generation submitted via **{provider_name}**.\nTask ID: `{result.task_id}`\nUse `query_video_status` with task_id=`{result.task_id}` and provider=`{provider_name}` to check status.",
        )]

    if name == "query_video_status":
        task_id = arguments.get("task_id")
        provider_name = arguments.get("provider")
        if not task_id or not provider_name:
            return [types.TextContent(type="text", text="Missing task_id or provider")]

        provider = get_provider(provider_name)
        if not provider:
            return [types.TextContent(type="text", text=f"Unknown provider: {provider_name}")]

        result = await provider.query(task_id)

        if result.status == "processing":
            return [types.TextContent(type="text", text=f"Still processing (provider: {provider_name}, task: {task_id}). Try again in 30 seconds.")]

        if result.status == "failed":
            return [types.TextContent(type="text", text=f"Failed: {result.error}")]

        # Success - try to download
        results = [types.TextContent(type="text", text=f"Video ready!\nURL: {result.video_url}")]

        if result.video_url:
            output_dir = arguments.get("output_directory") or VIDEO_OUTPUT_DIR
            filepath = await _try_download(result.video_url, output_dir, provider_name)
            if filepath:
                results.append(types.TextContent(type="text", text=f"Downloaded to: {filepath}"))
            else:
                results.append(types.TextContent(type="text", text="Auto-download failed. Use the URL above to download manually."))

        return results

    return [types.TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mcp-video-gen",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())

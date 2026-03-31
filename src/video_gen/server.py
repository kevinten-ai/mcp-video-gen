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
try:
    from .providers.veo import VeoProvider
except ImportError:
    VeoProvider = None  # google-auth not installed
from .audio import (
    register_tts,
    register_music,
    get_tts,
    get_music,
    list_tts as get_all_tts,
    list_music as get_all_music,
)
from .audio.minimax_tts import MiniMaxTTSProvider
from .audio.minimax_music import MiniMaxMusicProvider
try:
    from .audio.google_lyria import GoogleLyriaProvider
    from .audio.google_tts import GoogleTTSProvider
    from .audio.google_stt import transcribe as google_transcribe
except ImportError:
    GoogleLyriaProvider = None
    GoogleTTSProvider = None
    google_transcribe = None

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

    # Veo (Google Vertex AI) — API key or ADC auth
    gcp_project = os.getenv("GCP_PROJECT_ID", "")
    gcp_api_key = os.getenv("GEMINI_API_KEY", "") or os.getenv("GCP_API_KEY", "")
    if gcp_project and (gcp_api_key or VeoProvider is not None):
        gcp_region = os.getenv("GCP_REGION", "us-central1")
        # VeoProvider handles auth internally (API key preferred, ADC fallback)
        try:
            from .providers.veo import VeoProvider as _Veo
            register_provider(_Veo(gcp_project, gcp_region))
        except ImportError:
            pass  # google-auth not installed and no API key fallback possible

    # Audio providers (TTS + Music)
    if minimax_key:
        minimax_host = os.getenv("MINIMAX_API_HOST", "https://api.minimax.chat")
        register_tts(MiniMaxTTSProvider(minimax_key, minimax_host))
        register_music(MiniMaxMusicProvider(minimax_key, minimax_host))

    # Google Lyria (music) — works with Vertex AI API key
    if gcp_project and (gcp_api_key or GoogleLyriaProvider is not None):
        gcp_region = os.getenv("GCP_REGION", "us-central1")
        if GoogleLyriaProvider is not None:
            register_music(GoogleLyriaProvider(gcp_project, gcp_region))

    # Google TTS — requires ADC (OAuth2), does NOT work with API keys
    if GoogleTTSProvider is not None:
        try:
            import google.auth
            google.auth.default()
            register_tts(GoogleTTSProvider())
        except Exception:
            pass  # ADC not configured, skip Google TTS


_init_providers()


def _default_provider_name() -> str | None:
    """Return the default provider name (prefer free providers)."""
    providers = get_all_providers()
    for name in ("cogvideo", "dashscope", "kling", "siliconflow", "vidu", "minimax", "veo"):
        if name in providers:
            return name
    return None


async def _try_download(url: str, output_dir: str, prefix: str, ext: str = "mp4") -> str | None:
    """Try to download file to local disk. Returns filepath or None on failure."""
    try:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = out / f"{prefix}_{timestamp}.{ext}"
        async with httpx.AsyncClient(verify=False, follow_redirects=True) as client:
            resp = await client.get(url, timeout=120.0)
            if resp.status_code == 200 and len(resp.content) > 0:
                filepath.write_bytes(resp.content)
                return str(filepath)
    except Exception:
        pass
    return None


def _save_audio_bytes(data: bytes, output_dir: str, prefix: str, ext: str = "mp3") -> str:
    """Save raw audio bytes to disk."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = out / f"{prefix}_{timestamp}.{ext}"
    filepath.write_bytes(data)
    return str(filepath)


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    providers = get_all_providers()
    provider_names = list(providers.keys())
    default = _default_provider_name()

    tools = [
        types.Tool(
            name="generate_video",
            description=f"Generate a video from a text prompt (text-to-video) or from an image + prompt (image-to-video, veo only). Available providers: {', '.join(provider_names) or 'none configured'}. Default: {default or 'none'}.",
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
                    "image_url": {
                        "type": "string",
                        "description": "Reference image for image-to-video generation (veo only). Accepts: local file path, HTTP URL, or gs:// URI. Optional.",
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
            description="List all available video, TTS, and music providers.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]

    # TTS tool
    tts_providers = get_all_tts()
    if tts_providers:
        tts_names = list(tts_providers.keys())
        default_tts = tts_names[0]
        tts_voice_desc = (
            "Voice ID. MiniMax: female-shaonv, male-qn-qingse, cute_boy, Charming_Lady. "
            "Google TTS: charon (male-en), achernar (female-en), charon-zh (male-zh), kore-zh (female-zh). Optional."
        )
        tools.append(types.Tool(
            name="generate_speech",
            description=f"Convert text to speech audio. Available TTS providers: {', '.join(tts_names)}. Default: {default_tts}.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text to convert to speech",
                    },
                    "provider": {
                        "type": "string",
                        "description": f"TTS provider: {', '.join(tts_names)}. Default: {default_tts}",
                        "enum": tts_names,
                    },
                    "voice_id": {
                        "type": "string",
                        "description": tts_voice_desc,
                    },
                    "speed": {
                        "type": "number",
                        "description": "Speech speed (0.5-2.0). Default: 1.0",
                        "default": 1.0,
                    },
                    "output_directory": {
                        "type": "string",
                        "description": "Directory to save audio. Optional.",
                    },
                },
                "required": ["text"],
            },
        ))

    # Music tool
    music_providers = get_all_music()
    if music_providers:
        music_names = list(music_providers.keys())
        default_music = music_names[0]
        tools.append(types.Tool(
            name="generate_music",
            description=f"Generate music from a style prompt and optional lyrics. Available providers: {', '.join(music_names)}. Default: {default_music}. google-lyria: instrumental only, ~33s WAV.",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Music style description (e.g. 'Pop music, upbeat, suitable for workout'). 10-300 characters.",
                    },
                    "provider": {
                        "type": "string",
                        "description": f"Music provider: {', '.join(music_names)}. Default: {default_music}",
                        "enum": music_names,
                    },
                    "lyrics": {
                        "type": "string",
                        "description": "Optional lyrics with structure tags like [Verse], [Chorus], [Bridge]. Use \\n for line breaks. 10-600 characters. Note: google-lyria only generates instrumental music.",
                    },
                    "output_directory": {
                        "type": "string",
                        "description": "Directory to save audio. Optional.",
                    },
                },
                "required": ["prompt"],
            },
        ))

    # STT tool (transcribe audio to text)
    gcp_project = os.getenv("GCP_PROJECT_ID", "")
    gcp_api_key = os.getenv("GEMINI_API_KEY", "") or os.getenv("GCP_API_KEY", "")
    if (gcp_project or gcp_api_key) and google_transcribe is not None:
        tools.append(types.Tool(
            name="transcribe_audio",
            description="Transcribe audio/video file to text with word-level timestamps using Google Chirp 2. Supports: mp3, wav, flac, ogg. Use for subtitle generation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "audio_path": {
                        "type": "string",
                        "description": "Path to audio or video file to transcribe",
                    },
                    "language_code": {
                        "type": "string",
                        "description": "Language code (e.g. en-US, cmn-CN, ja-JP). Default: en-US",
                        "default": "en-US",
                    },
                },
                "required": ["audio_path"],
            },
        ))

    return tools


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent]:
    if not arguments:
        arguments = {}

    if name == "list_providers":
        lines = []
        providers = get_all_providers()
        if providers:
            lines.append("**Video Providers:**")
            for p in providers.values():
                lines.append(f"  **{p.name}** - {p.description}\n    Free tier: {p.free_tier_info}")
        tts = get_all_tts()
        if tts:
            lines.append("\n**TTS Providers:**")
            for p in tts.values():
                lines.append(f"  **{p.name}** - {p.description}")
        music = get_all_music()
        if music:
            lines.append("\n**Music Providers:**")
            for p in music.values():
                lines.append(f"  **{p.name}** - {p.description}")
        if not lines:
            return [types.TextContent(type="text", text="No providers configured.")]
        return [types.TextContent(type="text", text="\n".join(lines))]

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
        image_url = arguments.get("image_url")

        result = await provider.generate(prompt, duration=duration, aspect_ratio=aspect_ratio, image_url=image_url)

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

        # Success
        video_url = result.video_url or ""
        is_local_file = video_url.startswith("/") or video_url.startswith(".")
        results = []

        if is_local_file:
            results.append(types.TextContent(type="text", text=f"Video ready!\nSaved to: {video_url}"))
        else:
            results.append(types.TextContent(type="text", text=f"Video ready!\nURL: {video_url}"))
            if video_url:
                output_dir = arguments.get("output_directory") or VIDEO_OUTPUT_DIR
                filepath = await _try_download(video_url, output_dir, provider_name)
                if filepath:
                    results.append(types.TextContent(type="text", text=f"Downloaded to: {filepath}"))
                else:
                    results.append(types.TextContent(type="text", text="Auto-download failed. Use the URL above to download manually."))

        return results

    if name == "generate_speech":
        text = arguments.get("text")
        if not text:
            return [types.TextContent(type="text", text="Missing text")]

        tts_providers = get_all_tts()
        if not tts_providers:
            return [types.TextContent(type="text", text="No TTS providers configured. Set MINIMAX_API_KEY or GCP_PROJECT_ID.")]

        provider_name = arguments.get("provider") or list(tts_providers.keys())[0]
        provider = tts_providers.get(provider_name)
        if not provider:
            return [types.TextContent(type="text", text=f"Unknown TTS provider: {provider_name}. Available: {', '.join(tts_providers.keys())}")]

        voice_id = arguments.get("voice_id")
        speed = arguments.get("speed", 1.0)

        result = await provider.speak(text, voice_id=voice_id, speed=speed)

        if result.status == "failed":
            return [types.TextContent(type="text", text=f"TTS failed: {result.error}")]

        output_dir = arguments.get("output_directory") or VIDEO_OUTPUT_DIR
        ext = "wav" if provider_name == "google-lyria" else "mp3"
        results = []

        if result.audio_url:
            results.append(types.TextContent(type="text", text=f"Audio URL: {result.audio_url}"))
            filepath = await _try_download(result.audio_url, output_dir, provider_name, ext=ext)
            if filepath:
                results.append(types.TextContent(type="text", text=f"Saved to: {filepath}"))
        elif result.audio_data:
            filepath = _save_audio_bytes(result.audio_data, output_dir, provider_name, ext=ext)
            results.append(types.TextContent(type="text", text=f"Saved to: {filepath}"))

        return results or [types.TextContent(type="text", text="No audio generated")]

    if name == "generate_music":
        prompt = arguments.get("prompt")
        if not prompt:
            return [types.TextContent(type="text", text="Missing prompt")]

        music_providers = get_all_music()
        if not music_providers:
            return [types.TextContent(type="text", text="No music providers configured. Set MINIMAX_API_KEY or GCP_PROJECT_ID.")]

        provider_name = arguments.get("provider") or list(music_providers.keys())[0]
        provider = music_providers.get(provider_name)
        if not provider:
            return [types.TextContent(type="text", text=f"Unknown music provider: {provider_name}. Available: {', '.join(music_providers.keys())}")]

        lyrics = arguments.get("lyrics")

        result = await provider.generate(prompt, lyrics=lyrics)

        if result.status == "failed":
            return [types.TextContent(type="text", text=f"Music generation failed: {result.error}")]

        output_dir = arguments.get("output_directory") or VIDEO_OUTPUT_DIR
        ext = "wav" if provider_name == "google-lyria" else "mp3"
        results = []

        if result.audio_url:
            results.append(types.TextContent(type="text", text=f"Music URL: {result.audio_url}"))
            filepath = await _try_download(result.audio_url, output_dir, provider_name, ext=ext)
            if filepath:
                results.append(types.TextContent(type="text", text=f"Saved to: {filepath}"))
        elif result.audio_data:
            filepath = _save_audio_bytes(result.audio_data, output_dir, provider_name, ext=ext)
            results.append(types.TextContent(type="text", text=f"Saved to: {filepath}"))

        return results or [types.TextContent(type="text", text="No music generated")]

    if name == "transcribe_audio":
        audio_path = arguments.get("audio_path")
        if not audio_path:
            return [types.TextContent(type="text", text="Missing audio_path")]

        if google_transcribe is None:
            return [types.TextContent(type="text", text="STT not available. Install --extra gcp.")]

        language_code = arguments.get("language_code", "en-US")
        result = await google_transcribe(audio_path, language_code=language_code)

        if result["error"]:
            return [types.TextContent(type="text", text=f"Transcription failed: {result['error']}")]

        lines = [f"**Transcript:**\n{result['transcript']}"]
        if result["words"]:
            lines.append(f"\n**Words ({len(result['words'])} total, with timestamps):**")
            # Show first/last few words as preview
            words = result["words"]
            preview = words[:5]
            for w in preview:
                lines.append(f"  [{w['start']:.1f}s-{w['end']:.1f}s] {w['word']}")
            if len(words) > 5:
                lines.append(f"  ... ({len(words) - 5} more words)")

        return [types.TextContent(type="text", text="\n".join(lines))]

    return [types.TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mcp-video-gen",
                server_version="1.2.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())

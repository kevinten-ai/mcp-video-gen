# CLAUDE.md — mcp-video-gen

## Project Overview

Multi-provider MCP server for AI video, speech, music, and transcription. 7 video providers (including Veo img2vid) + 2 TTS + 2 music + STT under one unified interface.

## Architecture

- **Entry**: `src/video_gen/__init__.py` → `server.main()` via asyncio
- **Core**: `src/video_gen/server.py` — 7 MCP tool handlers, provider registry init, download helpers
- **Video Providers**: `src/video_gen/providers/` — one file per provider, all implement `BaseProvider`
- **Audio**: `src/video_gen/audio/` — TTS, music, and STT modules

## Key Design Decisions

- **Registry pattern**: Providers register at import time via `_init_providers()`, gated by env var presence
- **Async two-step**: All video APIs are async — `generate()` returns task_id, `query()` polls until done
- **Veo dual auth**: API key preferred (`?key=`), ADC fallback. Env vars read at call time, not import time.
- **Optional deps**: `google-auth` is in `[project.optional-dependencies]` under `gcp` extra. Import wrapped in `try/except ImportError`.
- **Local file detection**: `query_video_status` checks if `video_url` starts with `/` to skip HTTP download (Veo base64 mode saves locally in `query()`)
- **img2vid**: `BaseProvider.generate()` accepts optional `image_url` param. Only VeoProvider uses it; others ignore.
- **Lyria is synchronous**: Uses `:predict` (not `predictLongRunning`), returns audio inline. Response field is `bytesBase64Encoded` (same as Imagen).
- **Google TTS requires ADC**: Cloud TTS endpoint rejects Vertex AI API keys. Only registered when `google.auth.default()` succeeds.
- **STT module is standalone**: Not a provider class — just an async `transcribe()` function called directly from server.py.

## Provider Patterns

Video providers follow this structure:
1. `__init__` takes API key(s)
2. `generate(prompt, duration, aspect_ratio, image_url)` → `VideoResult(task_id, status="processing")`
3. `query(task_id)` → `VideoResult` with status and video_url

Audio providers:
- TTS: `speak(text, voice_id, speed)` → `AudioResult`
- Music: `generate(prompt, lyrics)` → `AudioResult`
- STT: standalone `transcribe(audio_path, language_code)` → `dict`

## Common Pitfalls

- **uv --extra placement**: `--extra gcp` must come AFTER `run`. `uv --directory /path run --extra gcp video-gen`
- **Veo env vars at import time**: `_get_api_key()` reads env at call time because MCP reconnect may reuse a process started before env changes
- **Lyria response field**: Vertex AI predict returns `bytesBase64Encoded`, NOT `audioContent` as docs suggest
- **Lyria recitation check**: Too-specific music style prompts may trigger copyright protection. Use abstract descriptions.
- **Cloud TTS auth split**: Vertex AI endpoints accept API keys; standalone Cloud APIs (TTS, STT v2) do NOT
- **SiliconFlow URL expiry**: Download URLs expire in 10 minutes, auto-download is critical
- **MiniMax lyrics required**: Music API requires `lyrics` field — defaults to `"[Instrumental]"` if not provided

## Development

```bash
uv sync --extra gcp     # all deps
uv run video-gen        # run server
npx @modelcontextprotocol/inspector uv --directory . run --extra gcp video-gen  # debug
```

# CLAUDE.md — mcp-video-gen

## Project Overview

Multi-provider MCP server for AI video, speech, and music generation. 7 video providers + MiniMax audio under one unified interface.

## Architecture

- **Entry**: `src/video_gen/__init__.py` → `server.main()` via asyncio
- **Core**: `src/video_gen/server.py` — MCP tool handlers, provider registry init, download helpers
- **Providers**: `src/video_gen/providers/` — one file per provider, all implement `BaseProvider`
- **Audio**: `src/video_gen/audio/` — TTS and music providers, implement `BaseTTSProvider` / `BaseMusicProvider`

## Key Design Decisions

- **Registry pattern**: Providers register at import time via `_init_providers()`, gated by env var presence
- **Async two-step**: All video APIs are async — `generate()` returns task_id, `query()` polls until done
- **Veo dual auth**: API key preferred (`?key=`), ADC fallback. Env vars read at call time, not import time.
- **Optional deps**: `google-auth` is in `[project.optional-dependencies]` under `gcp` extra. Import wrapped in `try/except ImportError`.
- **Local file detection**: `query_video_status` checks if `video_url` starts with `/` to skip HTTP download (Veo base64 mode saves locally in `query()`)

## Provider Patterns

Each provider file follows the same structure:
1. `__init__` takes API key(s)
2. `generate()` — POST to create endpoint → return `VideoResult(task_id, status="processing")`
3. `query()` — GET/POST to status endpoint → return `VideoResult` with status and video_url

Status values: `"processing"` | `"success"` | `"failed"`

## Common Pitfalls

- **uv --extra placement**: `--extra gcp` must come AFTER `run`, not before. `uv --directory /path run --extra gcp video-gen` ✓
- **Veo env vars at import time**: `_get_api_key()` reads env at call time because MCP reconnect may reuse a process started before env changes
- **Kling JWT**: Uses PyJWT to generate HS256 tokens with access_key as issuer and secret_key for signing
- **SiliconFlow URL expiry**: Download URLs expire in 10 minutes, auto-download is critical
- **MiniMax lyrics required**: Music API requires `lyrics` field — defaults to `"[Instrumental]"` if not provided

## Development

```bash
uv sync --extra gcp     # all deps
uv run video-gen        # run server
npx @modelcontextprotocol/inspector uv --directory . run --extra gcp video-gen  # debug
```

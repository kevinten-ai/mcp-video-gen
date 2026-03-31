# mcp-video-gen

<p align="center">
  <img src="docs/banner.png" alt="mcp-video-gen banner" width="800">
</p>

<p align="center">
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+"></a>
  <a href="https://modelcontextprotocol.io/"><img src="https://img.shields.io/badge/MCP-compatible-green.svg" alt="MCP"></a>
  <img src="https://img.shields.io/badge/version-1.2.0-blue.svg" alt="Version 1.2.0">
</p>

<p align="center">
  <strong>Multi-provider AI video, speech, music & transcription MCP server.</strong><br>
  7 video providers + image-to-video + TTS + music + STT — one unified interface.<br>
  Works with Claude Code, Claude Desktop, Cursor, and any MCP-compatible client.
</p>

<p align="center">
  <a href="README_CN.md">中文文档</a>
</p>

## Features

- **7 video providers** — CogVideoX, DashScope/Wan, Kling, SiliconFlow, Vidu, MiniMax, Google Veo (2/3/3.1)
- **Image-to-video** — generate videos from reference images (Veo)
- **TTS** — text-to-speech via MiniMax (+ Google Chirp 3 HD with ADC)
- **Music generation** — MiniMax Music + **Google Lyria** (instrumental, ~33s, GCP credits)
- **Speech-to-text** — transcribe audio with word-level timestamps via Google Chirp 2 (for subtitle generation)
- **Free-tier focused** — CogVideoX is completely free with unlimited usage
- **Provider switching** — choose the best provider per request via `provider` parameter
- **Auto-download** — generated videos/audio saved to local disk automatically

## Architecture

<p align="center">
  <img src="docs/architecture.png" alt="Architecture" width="800">
</p>

### How It Works

```
User Prompt → AI Assistant (Claude / Cursor) → MCP Server → Provider API
                                                    ↓
                                        generate_video() → task_id
                                        query_video_status(task_id) → download to disk
```

All video providers use an **async pattern**: submit a generation request, get a task ID, then poll until complete. The MCP server handles this transparently — the AI assistant calls `generate_video`, then `query_video_status` in a loop until the video is ready.

## Supported Providers

### Video Providers

| Provider | Model | Free Tier | Quality | Duration | Best for |
|---|---|---|---|---|---|
| **CogVideoX-Flash** (智谱) | cogvideox-flash | **Unlimited free** | 1440x960 | 6s | Getting started, free usage |
| **DashScope / Wan** (通义万相) | wan2.6-t2v | 50s free (90 days) | Up to 1080P | 5-10s | High quality, Chinese content |
| **Kling AI** (可灵) | kling-v2-master | 66 credits/day (web only) | 720p | 5-10s | Good quality, daily free credits |
| **SiliconFlow** (硅基流动) | Wan2.1-T2V-14B | $1 signup bonus | 720p | varies | Quick testing |
| **Vidu** (生数科技) | vidu-2.0 | 200 promo credits | 720p | 4s | Short clips |
| **MiniMax Hailuo** (海螺) | Hailuo 2.3 | Paid | Up to 1080P | 6-10s | Highest quality |
| **Google Veo** (Vertex AI) | veo-2.0/3.0/3.1 | GCP credits | 720p-4K | 5-8s | Production quality, GCP users |

#### Provider selection guide

```
Need a video?
  ├─ Free / just trying it out?
  │   └─ cogvideo ✅ (unlimited free, no signup hassle)
  │
  ├─ Need highest quality?
  │   ├─ minimax (best Chinese provider, paid)
  │   └─ veo (best international, GCP credits)
  │
  ├─ Have GCP credits to spend?
  │   ├─ Budget-conscious → veo-3.0-fast ($0.15/sec, 1080p)
  │   └─ Best quality → veo-2.0 ($0.50/sec) or veo-3.0 ($0.75/sec)
  │
  └─ Need long videos (10s)?
      ├─ dashscope / kling / minimax (support 10s)
      └─ veo max 8s
```

### Audio Providers

| Provider | Capability | Model | Pricing | Env Var |
|---|---|---|---|---|
| **MiniMax TTS** | Text-to-Speech | speech-2.6-hd | ~¥0.01/req | `MINIMAX_API_KEY` |
| **Google TTS** | Text-to-Speech | Chirp 3 HD (52 languages) | ~$30/1M chars | ADC only |
| **MiniMax Music** | Music Generation (with lyrics) | music-2.0 | ~¥0.1/song | `MINIMAX_API_KEY` |
| **Google Lyria** | Instrumental Music | lyria-002 (~33s WAV) | ~$0.06/clip | `GCP_PROJECT_ID` |

### Transcription

| Provider | Capability | Model | Pricing | Env Var |
|---|---|---|---|---|
| **Google STT** | Speech-to-Text + timestamps | Chirp 2 | ~$0.016/min | `GCP_PROJECT_ID` |

> - MiniMax tools auto-enable when `MINIMAX_API_KEY` is set
> - Google Lyria and STT auto-enable when `GCP_PROJECT_ID` is set (uses `GEMINI_API_KEY`)
> - Google TTS requires ADC (`gcloud auth application-default login`)

## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/kevinten-ai/mcp-video-gen.git
cd mcp-video-gen
uv sync              # basic deps
uv sync --extra gcp  # add this if using Google Veo
```

### 2. Configure MCP

Only configure the providers you want to use. At least one API key is required.

<details>
<summary><b>Claude Code (CLI) — recommended</b></summary>

```bash
# Minimal (free CogVideoX only)
claude mcp add -s user mcp-video-gen \
  --env COGVIDEO_API_KEY=your_key \
  -- uv --directory /path/to/mcp-video-gen run video-gen

# Full (all providers including Veo)
claude mcp add -s user mcp-video-gen \
  --env COGVIDEO_API_KEY=your_key \
  --env KLING_ACCESS_KEY=your_ak \
  --env KLING_SECRET_KEY=your_sk \
  --env MINIMAX_API_KEY=your_key \
  --env GCP_PROJECT_ID=your-project-id \
  --env GEMINI_API_KEY=your_gcp_api_key \
  -- uv --directory /path/to/mcp-video-gen run --extra gcp video-gen
```

> **Important:** `--extra gcp` must come after `run`, not before it. This is a `uv run` option, not a global `uv` option.

</details>

<details>
<summary><b>Claude Desktop / Cursor (JSON config)</b></summary>

```json
{
  "mcpServers": {
    "mcp-video-gen": {
      "command": "uv",
      "args": ["--directory", "/path/to/mcp-video-gen", "run", "--extra", "gcp", "video-gen"],
      "env": {
        "COGVIDEO_API_KEY": "your_key",
        "GCP_PROJECT_ID": "your-project-id",
        "GEMINI_API_KEY": "your_gcp_api_key"
      }
    }
  }
}
```

</details>

### 3. Use it

Ask your AI assistant to generate a video:

```
"Generate a video of a cat playing piano"
```

The assistant will call `generate_video`, wait, then call `query_video_status` to download the result.

## Tools (7 total)

### Video
- **generate_video** — Text-to-video or image-to-video generation. Params: `prompt`, `provider`, `duration` (5/10), `aspect_ratio` (16:9/9:16/1:1), `image_url` (for img2vid, Veo only).
- **query_video_status** — Poll generation status and auto-download. Params: `task_id`, `provider`.

### Audio
- **generate_speech** — Text-to-speech. Params: `text`, `provider` (minimax/google-tts), `voice_id`, `speed` (0.5-2.0).
- **generate_music** — AI music generation. Params: `prompt`, `provider` (minimax/google-lyria), `lyrics` (optional, supports `[Verse]`/`[Chorus]`/`[Bridge]`).

### Transcription
- **transcribe_audio** — Speech-to-text with word-level timestamps (Google Chirp 2). Params: `audio_path`, `language_code` (en-US/cmn-CN/ja-JP/...). Use with `ffmpeg add_subtitles` for full subtitle pipeline.

### Utility
- **list_providers** — Show all configured video, TTS, music, and STT providers.

## API Key Registration Guide

<details>
<summary><b>1. CogVideoX-Flash (智谱清影) — Free Unlimited ✅ Recommended starting point</b></summary>

| Item | Detail |
|---|---|
| Platform | 智谱 AI 开放平台 |
| URL | https://open.bigmodel.cn |
| Free Tier | **Completely free, no daily limit** |
| Env Var | `COGVIDEO_API_KEY` |

**Steps:**
1. Visit https://open.bigmodel.cn → "注册" (Sign Up)
2. Register with phone number or email
3. Go to **API Keys**: https://open.bigmodel.cn/usercenter/apikeys
4. Click "创建 API Key" → copy (format: `xxxxxxxx.xxxxxxxxxx`)

> Note: May be overloaded during peak hours — retry if you get "访问量过大".

</details>

<details>
<summary><b>2. DashScope / Wan (通义万相) — 50s Free</b></summary>

| Item | Detail |
|---|---|
| Platform | 阿里云百炼 (Alibaba Bailian) |
| URL | https://bailian.console.aliyun.com |
| Free Tier | **50 seconds free (valid 90 days)** |
| Env Var | `DASHSCOPE_API_KEY` |

**Steps:**
1. Register at https://www.aliyun.com (phone/email)
2. Go to https://bailian.console.aliyun.com → activate DashScope
3. **API-KEY 管理**: https://bailian.console.aliyun.com/?apiKey=1#/api-key
4. Click "创建 API Key" → copy (format: `sk-xxxxxxxxxxxxxxxx`)

</details>

<details>
<summary><b>3. Kling AI (可灵) — 66 Credits/Day</b></summary>

| Item | Detail |
|---|---|
| Platform | Kling AI Developer Platform |
| URL | https://klingai.com/global/dev |
| Free Tier | **66 credits/day (web only); API requires purchased resource pack** |
| Env Vars | `KLING_ACCESS_KEY`, `KLING_SECRET_KEY` |

**Steps:**
1. Sign up at https://klingai.com
2. Developer Console: https://app.klingai.com/global/dev/document-api/quickStart/userManual
3. **Settings** > **API Keys** → create key pair (Access Key + Secret Key)

> **Important:** 66 daily credits are web-only, NOT for API. API requires purchasing a resource pack.

</details>

<details>
<summary><b>4. SiliconFlow (硅基流动) — $1 Signup Bonus</b></summary>

| Item | Detail |
|---|---|
| Platform | SiliconFlow |
| URL | https://siliconflow.cn |
| Free Tier | **$1 bonus (~3 videos at $0.29/video)** |
| Env Var | `SILICONFLOW_API_KEY` |

**Steps:**
1. Register at https://cloud.siliconflow.cn/account/login (Chinese phone)
2. **API Keys**: https://cloud.siliconflow.cn/account/ak → "新建 API Key"
3. Copy (format: `sk-xxxxxxxxxxxxxxxx`)

> Video download URLs expire in 10 minutes — the MCP server auto-downloads on query.

</details>

<details>
<summary><b>5. Vidu (生数科技) — Promotional Credits</b></summary>

| Item | Detail |
|---|---|
| Platform | Vidu Platform |
| URL | https://platform.vidu.com |
| Free Tier | **Apply for 200 free API credits (promotional)** |
| Env Var | `VIDU_API_KEY` |

**Steps:**
1. Sign up at https://www.vidu.com → API Platform: https://platform.vidu.com
2. Create API key → copy

> API credits are separate from web credits (800/month web credits don't apply to API).

</details>

<details>
<summary><b>6. MiniMax Hailuo (海螺) — Paid (Best Quality)</b></summary>

| Item | Detail |
|---|---|
| Platform | MiniMax Open Platform |
| URL | https://platform.minimaxi.com |
| Free Tier | **None. ~¥0.7/video (512P 6s) to ~¥3.7/video (1080P 6s)** |
| Env Vars | `MINIMAX_API_KEY`, `MINIMAX_API_HOST` (optional) |

**Steps:**
1. Register at https://platform.minimaxi.com (Chinese phone)
2. Complete real-name verification (实名认证)
3. Create API key (format: `sk-api-xxxxxxxxxxxxxxxx`)
4. Top up at billing center (min ~¥10)

> Setting `MINIMAX_API_KEY` also enables TTS and music generation tools.

</details>

<details>
<summary><b>7. Google Veo (Vertex AI) — GCP Credits</b></summary>

| Item | Detail |
|---|---|
| Platform | Google Cloud Vertex AI |
| URL | https://console.cloud.google.com |
| Free Tier | **No free tier. Uses GCP credits/billing.** |
| Env Vars | `GCP_PROJECT_ID`, `GEMINI_API_KEY` (recommended) |

**Prerequisites:**
1. GCP project with billing: https://console.cloud.google.com/projectcreate
2. Enable Vertex AI API: https://console.cloud.google.com/apis/library/aiplatform.googleapis.com
3. GCP API Key: https://console.cloud.google.com/apis/credentials

**Models:**

| Model | Resolution | Pricing | Best for |
|---|---|---|---|
| `veo-2.0-generate-001` (default) | 720p | ~$0.50/sec | Stable, GA |
| `veo-3.0-generate-001` | 1080p | ~$0.75/sec | High quality |
| `veo-3.0-fast-generate-001` | 1080p | ~$0.15/sec | Cost-effective |
| `veo-3.1-generate-001` | **4K** | ~$0.75/sec | Highest quality |
| `veo-3.1-fast-generate-001` | 1080p | ~$0.10/sec | **Best value** ✅ |

**Auth options:**
1. **GCP API Key** (recommended) — set `GEMINI_API_KEY=your_gcp_api_key`. Simplest setup, no extra deps.
2. **OAuth2 / ADC** — run `gcloud auth application-default login`. Requires `--extra gcp` for `google-auth`.

**Optional env vars:**

| Variable | Default | Description |
|---|---|---|
| `VEO_MODEL` | `veo-2.0-generate-001` | Model to use |
| `VEO_GCS_BUCKET` | — | GCS bucket for output (omit for base64 inline) |
| `GCP_REGION` | `us-central1` | Vertex AI region |
| `GEMINI_API_KEY` | — | GCP API key (shared with mcp-image-gen) |

</details>

## Environment Variables

| Variable | Provider | Required |
|---|---|---|
| `COGVIDEO_API_KEY` | CogVideoX (智谱) | At least one provider |
| `DASHSCOPE_API_KEY` | Wan / DashScope (阿里) | must be configured |
| `KLING_ACCESS_KEY` | Kling AI (可灵) | |
| `KLING_SECRET_KEY` | Kling AI (可灵) | |
| `SILICONFLOW_API_KEY` | SiliconFlow (硅基流动) | |
| `VIDU_API_KEY` | Vidu (生数) | |
| `MINIMAX_API_KEY` | MiniMax (海螺 + TTS + Music) | |
| `MINIMAX_API_HOST` | MiniMax | Optional, default: `https://api.minimax.chat` |
| `GCP_PROJECT_ID` | Google Veo | Required for Veo |
| `GEMINI_API_KEY` | Google Veo | Recommended for Veo (or use ADC) |
| `GCP_REGION` | Google Veo | Optional, default: `us-central1` |
| `VEO_MODEL` | Google Veo | Optional, default: `veo-2.0-generate-001` |
| `VEO_GCS_BUCKET` | Google Veo | Optional, GCS bucket for video output |
| `VIDEO_OUTPUT_DIR` | All providers | Optional, default: `./output` |

## Troubleshooting

### Common Errors

| Error | Provider | Root Cause | Solution |
|---|---|---|---|
| `No providers configured` | All | No API keys set | Set at least one provider's API key in MCP env config |
| `Unknown provider: xxx` | All | Typo or provider not configured | Check `list_providers` for available options |
| `Still processing` | All | Video not ready yet | Normal — call `query_video_status` again in 30 seconds |

### Provider-Specific Errors

| Error | Provider | Solution |
|---|---|---|
| `访问量过大` (too many requests) | CogVideoX | Free model overloaded — wait and retry |
| `JWT token error` | Kling | Check both `KLING_ACCESS_KEY` and `KLING_SECRET_KEY` are set |
| `base_resp.status_code != 0` | MiniMax | Check API key, ensure account has balance |
| `Auth failed: credentials not found` | Veo | Set `GEMINI_API_KEY` or run `gcloud auth application-default login` |
| `429 quota exceeded` | Veo | Vertex AI rate limit (10 RPM). Wait 1 min or switch model via `VEO_MODEL` |
| `Video blocked by safety filter` | Veo | Content flagged — rephrase prompt to avoid restricted content |

### Veo-Specific Notes

- **API Key vs ADC:** `GEMINI_API_KEY` is the simplest auth method. Same key works for both mcp-image-gen and mcp-video-gen.
- **`--extra gcp` placement:** Must come after `run` in the uv command: `uv --directory /path run --extra gcp video-gen` (NOT `uv --directory /path --extra gcp run video-gen`)
- **Base64 mode:** Without `VEO_GCS_BUCKET`, videos are returned as base64 in the API response and decoded locally. Works well for videos under 8s.
- **Cost control:** Use `veo-3.0-fast-generate-001` ($0.15/sec) instead of default Veo 2 ($0.50/sec) for 70% savings with 1080p output.

### Download Issues

| Issue | Solution |
|---|---|
| `Auto-download failed` | Video URL may have expired. SiliconFlow URLs expire in 10 min. |
| Video file is 0 bytes | Provider returned empty response. Retry generation. |
| SSL verification errors | Server disables SSL verify for downloads (some providers use self-signed certs) |

## Project Structure

```
src/video_gen/
├── __init__.py
├── server.py              # MCP server + tool handlers
├── providers/
│   ├── __init__.py        # BaseProvider abstract class + registry
│   ├── cogvideo.py        # 智谱 CogVideoX-Flash
│   ├── dashscope.py       # 阿里 通义万相 Wan 2.6
│   ├── kling.py           # 可灵 Kling AI (JWT auth)
│   ├── siliconflow.py     # 硅基流动 SiliconFlow
│   ├── vidu.py            # 生数 Vidu
│   ├── minimax.py         # MiniMax 海螺
│   └── veo.py             # Google Veo (Vertex AI, API key + ADC)
└── audio/
    ├── __init__.py        # BaseTTSProvider + BaseMusicProvider + registry
    ├── minimax_tts.py     # MiniMax TTS (speech-2.6-hd)
    ├── minimax_music.py   # MiniMax Music (music-2.0)
    ├── google_lyria.py    # Google Lyria 2 instrumental music (Vertex AI)
    ├── google_tts.py      # Google Cloud TTS Chirp 3 HD (ADC only)
    └── google_stt.py      # Google Cloud STT Chirp 2 (transcription)
```

### Adding a New Provider

1. Create `src/video_gen/providers/your_provider.py`
2. Implement `BaseProvider` (properties: `name`, `description`, `free_tier_info`; methods: `generate()`, `query()`)
3. Register in `server.py:_init_providers()` with env var check
4. Provider appears automatically in `list_providers` and `generate_video` tool schema

## Local Development

```bash
git clone https://github.com/kevinten-ai/mcp-video-gen.git
cd mcp-video-gen
uv sync --extra gcp  # all deps including google-auth

# Run directly
uv run video-gen

# Debug with MCP Inspector
npx @modelcontextprotocol/inspector uv --directory . run --extra gcp video-gen
```

## Related Projects

- [mcp-image-gen](https://github.com/kevinten-ai/mcp-image-gen) — AI image generation MCP server (Gemini + Imagen)
- [mcp-3d-gen](https://github.com/kevinten-ai/mcp-3d-gen) — AI 3D model generation MCP server

## License

MIT — see [LICENSE](LICENSE) for details.

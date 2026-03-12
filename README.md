# mcp-video-gen

MCP server for AI video generation with multiple providers. Focus on free-tier models.

## Supported Providers

| Provider | Model | Free Tier | Quality |
|---|---|---|---|
| **CogVideoX-Flash** (智谱) | cogvideox-flash | Unlimited free | 1440x960, 6s |
| **DashScope / Wan** (通义万相) | wan2.6-t2v | 50s free (90 days) | Up to 1080P, 5-10s |
| **Kling AI** (可灵) | kling-v2-master | 66 credits/day | 720p, 5-10s |
| **SiliconFlow** (硅基流动) | Wan2.1-T2V-14B | $1 signup bonus | 720p |
| **Vidu** (生数科技) | vidu-2.0 | 200 promo credits | 720p, 4s |
| **MiniMax Hailuo** (海螺) | Hailuo 2.3 | Paid | Up to 1080P, 6-10s |

## Installation

### Claude Code (Global)

```bash
claude mcp add -s user mcp-video-gen \
  --env COGVIDEO_API_KEY=your_key \
  --env DASHSCOPE_API_KEY=your_key \
  --env KLING_ACCESS_KEY=your_ak \
  --env KLING_SECRET_KEY=your_sk \
  --env SILICONFLOW_API_KEY=your_key \
  --env VIDU_API_KEY=your_key \
  --env MINIMAX_API_KEY=your_key \
  -- uv --directory /path/to/mcp-video-gen run video-gen
```

Only configure the providers you want to use. At least one API key is required.

## API Key Registration Guide

### 1. CogVideoX-Flash (智谱清影) — Free Unlimited

| Item | Detail |
|---|---|
| Platform | 智谱 AI 开放平台 |
| URL | https://open.bigmodel.cn |
| Free Tier | **Completely free, no daily limit** |
| Env Var | `COGVIDEO_API_KEY` |

**Steps:**
1. Visit https://open.bigmodel.cn and click "注册" (Sign Up)
2. Register with phone number (Chinese mobile) or email
3. After login, go to **API Keys** page: https://open.bigmodel.cn/usercenter/apikeys
4. Click "创建 API Key" to generate a new key
5. Copy the key (format: `xxxxxxxx.xxxxxxxxxx`)

> Note: CogVideoX-Flash is a free model but may be overloaded during peak hours. If you get "访问量过大", try again later.

---

### 2. DashScope / Wan (阿里通义万相) — 50s Free

| Item | Detail |
|---|---|
| Platform | 阿里云百炼 (Alibaba Bailian) |
| URL | https://bailian.console.aliyun.com |
| Free Tier | **50 seconds free for new users (valid 90 days)** |
| Env Var | `DASHSCOPE_API_KEY` |

**Steps:**
1. Visit https://www.aliyun.com and register an Alibaba Cloud account (supports phone/email)
2. Go to https://bailian.console.aliyun.com
3. Activate the DashScope service if prompted
4. Navigate to **API-KEY 管理**: https://bailian.console.aliyun.com/?apiKey=1#/api-key
5. Click "创建 API Key", select a workspace
6. Copy the key (format: `sk-xxxxxxxxxxxxxxxx`)

> The free 50-second quota is auto-activated for new users. Check your remaining quota at the billing page.

---

### 3. Kling AI (可灵) — 66 Credits/Day

| Item | Detail |
|---|---|
| Platform | Kling AI Developer Platform |
| URL | https://klingai.com/global/dev |
| Free Tier | **66 credits/day on web UI; API requires purchased resource pack** |
| Env Vars | `KLING_ACCESS_KEY`, `KLING_SECRET_KEY` |

**Steps:**
1. Visit https://klingai.com and sign up (email or phone)
2. Go to Developer Console: https://app.klingai.com/global/dev/document-api/quickStart/userManual
3. Navigate to **Settings** > **API Keys**
4. Create an API key pair — you will get an **Access Key** (ak) and **Secret Key** (sk)
5. Copy both keys

> **Important:** The daily 66 free credits only work on the web UI, NOT via API. API calls require purchasing a resource pack. Cheapest standard 5s video costs ~2 credits.

---

### 4. SiliconFlow (硅基流动) — $1 Signup Bonus

| Item | Detail |
|---|---|
| Platform | SiliconFlow |
| URL | https://siliconflow.cn |
| Free Tier | **$1 registration bonus (~3 free videos at $0.29/video)** |
| Env Var | `SILICONFLOW_API_KEY` |

**Steps:**
1. Visit https://cloud.siliconflow.cn/account/login and register (Chinese phone number)
2. After login, go to **API Keys**: https://cloud.siliconflow.cn/account/ak
3. Click "新建 API Key"
4. Copy the key (format: `sk-xxxxxxxxxxxxxxxx`)

> Registration bonus is one-time only. After it's spent, video generation costs ~$0.29/video (Wan2.1 model). Video result URLs expire in 10 minutes — download immediately.

---

### 5. Vidu (生数科技) — Promotional Free Credits

| Item | Detail |
|---|---|
| Platform | Vidu Platform |
| URL | https://platform.vidu.com |
| Free Tier | **Apply for 200 free API credits (promotional, not guaranteed)** |
| Env Var | `VIDU_API_KEY` |

**Steps:**
1. Visit https://www.vidu.com and sign up
2. Go to API Platform: https://platform.vidu.com
3. Navigate to **API Keys** and create a new key
4. Copy the key
5. Check if free credit promotion is active — apply for 200 free points if available

> API credits are separate from web UI credits (800/month on web do NOT apply to API). The 200 free credit promotion may not always be available.

---

### 6. MiniMax Hailuo (海螺) — Paid

| Item | Detail |
|---|---|
| Platform | MiniMax Open Platform |
| URL | https://platform.minimaxi.com |
| Free Tier | **None for API. ~¥0.7/video (512P 6s) to ~¥3.7/video (1080P 6s)** |
| Env Vars | `MINIMAX_API_KEY`, `MINIMAX_API_HOST` (default: `https://api.minimax.chat`) |

**Steps:**
1. Visit https://platform.minimaxi.com and register (Chinese phone number)
2. Complete real-name verification (实名认证) — required for API access
3. Go to **API Keys** page and create a new key
4. Copy the key (format: `sk-api-xxxxxxxxxxxxxxxx`)
5. Top up your account at the billing center (minimum ~¥10)

> MiniMax API host defaults to `https://api.minimax.chat`. Hailuo 2.3 model delivers the best quality among all providers listed here.

---

## Environment Variables Summary

| Variable | Provider | Required |
|---|---|---|
| `COGVIDEO_API_KEY` | CogVideoX (智谱) | At least one |
| `DASHSCOPE_API_KEY` | Wan / DashScope (阿里) | provider |
| `KLING_ACCESS_KEY` | Kling AI (可灵) | must be |
| `KLING_SECRET_KEY` | Kling AI (可灵) | configured |
| `SILICONFLOW_API_KEY` | SiliconFlow (硅基流动) | |
| `VIDU_API_KEY` | Vidu (生数) | |
| `MINIMAX_API_KEY` | MiniMax (海螺) | |
| `MINIMAX_API_HOST` | MiniMax (海螺) | Optional, default: `https://api.minimax.chat` |
| `VIDEO_OUTPUT_DIR` | Output path | Optional, default: `./output` |

## Tools

- **generate_video** — Generate a video from a text prompt. Specify `provider` to choose backend.
- **query_video_status** — Check generation status and download the result.
- **list_providers** — Show all available providers and their free tier info.

## Architecture

```
src/video_gen/
├── __init__.py
├── server.py              # MCP server + tool definitions
└── providers/
    ├── __init__.py        # BaseProvider + registry
    ├── cogvideo.py        # 智谱 CogVideoX-Flash
    ├── dashscope.py       # 阿里 通义万相 Wan 2.6
    ├── kling.py           # 可灵 Kling AI
    ├── siliconflow.py     # 硅基流动 SiliconFlow
    ├── vidu.py            # 生数 Vidu
    └── minimax.py         # MiniMax 海螺
```

### Adding a New Provider

1. Create a new file under `src/video_gen/providers/` (e.g., `newprovider.py`)
2. Implement the `BaseProvider` abstract class with `generate()` and `query()` methods
3. Register it in `server.py:_init_providers()` with an env var check

## License

MIT

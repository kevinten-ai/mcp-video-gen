# mcp-video-gen

<p align="center">
  <img src="docs/banner.png" alt="mcp-video-gen banner" width="800">
</p>

<p align="center">
  <strong>多平台 AI 视频、语音、音乐生成 MCP 服务器，专注于免费额度模型。</strong>
</p>

<p align="center">
  <a href="README.md">English</a>
</p>

## 架构图

<p align="center">
  <img src="docs/architecture.png" alt="架构图" width="800">
</p>

## 支持的平台

| 平台 | 模型 | 免费额度 | 画质 |
|---|---|---|---|
| **智谱清影** CogVideoX-Flash | cogvideox-flash | 完全免费，无限量 | 1440x960, 6秒 |
| **阿里通义万相** Wan 2.6 | wan2.6-t2v | 新用户50秒（90天有效） | 最高1080P, 5-10秒 |
| **可灵** Kling AI | kling-v2-master | 网页端每天66积分 | 720p, 5-10秒 |
| **硅基流动** SiliconFlow | Wan2.1-T2V-14B | 注册送$1（约3个视频） | 720p |
| **生数科技** Vidu | vidu-2.0 | 申请200积分（促销） | 720p, 4秒 |
| **MiniMax 海螺** Hailuo 2.3 | Hailuo 2.3 | 付费 | 最高1080P, 6-10秒 |
| **Google Veo** (Vertex AI) | veo-2.0/3.0/3.0-fast | GCP 赠金 | 720p-1080p, 5-8秒 |

### 音频能力（语音合成 & 音乐生成）

| 平台 | 能力 | 模型 | 价格 |
|---|---|---|---|
| **MiniMax 海螺语音** | 文字转语音 (TTS) | speech-2.6-hd | 付费（约 ¥0.01/次） |
| **MiniMax 海螺音乐** | AI 音乐生成 | music-2.0 | 付费（约 ¥0.1/首） |

> 配置 `MINIMAX_API_KEY` 后，TTS 和音乐生成功能自动启用，无需额外配置。

## 安装

### Claude Code 全局配置

```bash
claude mcp add -s user mcp-video-gen \
  --env COGVIDEO_API_KEY=你的key \
  --env DASHSCOPE_API_KEY=你的key \
  --env KLING_ACCESS_KEY=你的ak \
  --env KLING_SECRET_KEY=你的sk \
  --env SILICONFLOW_API_KEY=你的key \
  --env VIDU_API_KEY=你的key \
  --env MINIMAX_API_KEY=你的key \
  -- uv --directory /path/to/mcp-video-gen run video-gen
```

只需配置你要使用的平台，至少配置一个。

## API Key 注册指南

### 1. 智谱清影 CogVideoX-Flash — 完全免费

| 项目 | 详情 |
|---|---|
| 平台 | 智谱 AI 开放平台 |
| 地址 | https://open.bigmodel.cn |
| 免费额度 | **完全免费，无每日限制** |
| 环境变量 | `COGVIDEO_API_KEY` |

**注册步骤：**
1. 访问 https://open.bigmodel.cn ，点击"注册"
2. 使用手机号或邮箱注册
3. 登录后，进入 **API Keys** 页面：https://open.bigmodel.cn/usercenter/apikeys
4. 点击"创建 API Key"
5. 复制 Key（格式：`xxxxxxxx.xxxxxxxxxx`）

> 提示：CogVideoX-Flash 是免费模型，但高峰期可能提示"访问量过大"，稍后重试即可。

---

### 2. 阿里通义万相 DashScope — 50秒免费

| 项目 | 详情 |
|---|---|
| 平台 | 阿里云百炼 |
| 地址 | https://bailian.console.aliyun.com |
| 免费额度 | **新用户赠送50秒视频生成额度（90天有效）** |
| 环境变量 | `DASHSCOPE_API_KEY` |

**注册步骤：**
1. 访问 https://www.aliyun.com 注册阿里云账号（支持手机号/邮箱）
2. 进入百炼平台：https://bailian.console.aliyun.com
3. 如提示，开通 DashScope 服务
4. 进入 **API-KEY 管理**：https://bailian.console.aliyun.com/?apiKey=1#/api-key
5. 点击"创建 API Key"，选择工作空间
6. 复制 Key（格式：`sk-xxxxxxxxxxxxxxxx`）

> 50秒免费额度在新用户开通时自动激活，可在计费页面查看剩余额度。

---

### 3. 可灵 Kling AI — 每天66积分

| 项目 | 详情 |
|---|---|
| 平台 | Kling AI 开发者平台 |
| 地址 | https://klingai.com/global/dev |
| 免费额度 | **网页端每天66积分；API 需购买资源包** |
| 环境变量 | `KLING_ACCESS_KEY`, `KLING_SECRET_KEY` |

**注册步骤：**
1. 访问 https://klingai.com 注册（邮箱或手机号）
2. 进入开发者控制台：https://app.klingai.com/global/dev/document-api/quickStart/userManual
3. 在 **设置** > **API Keys** 中创建密钥对
4. 获得 **Access Key**（ak）和 **Secret Key**（sk）
5. 复制两个 Key

> **注意：** 每天66积分仅限网页端使用，API 调用需要单独购买资源包。标准模式5秒视频约消耗2积分。

---

### 4. 硅基流动 SiliconFlow — 注册送$1

| 项目 | 详情 |
|---|---|
| 平台 | 硅基流动 |
| 地址 | https://siliconflow.cn |
| 免费额度 | **注册赠送$1（约可生成3个视频，$0.29/个）** |
| 环境变量 | `SILICONFLOW_API_KEY` |

**注册步骤：**
1. 访问 https://cloud.siliconflow.cn/account/login 注册（需中国手机号）
2. 登录后进入 **API Keys**：https://cloud.siliconflow.cn/account/ak
3. 点击"新建 API Key"
4. 复制 Key（格式：`sk-xxxxxxxxxxxxxxxx`）

> 注册赠送为一次性额度，用完后视频生成约$0.29/个。生成的视频下载链接10分钟后过期，请及时下载。

---

### 5. 生数科技 Vidu — 促销送200积分

| 项目 | 详情 |
|---|---|
| 平台 | Vidu 开放平台 |
| 地址 | https://platform.vidu.com |
| 免费额度 | **申请200免费 API 积分（促销活动，不保证常驻）** |
| 环境变量 | `VIDU_API_KEY` |

**注册步骤：**
1. 访问 https://www.vidu.com 注册
2. 进入 API 平台：https://platform.vidu.com
3. 在 **API Keys** 页面创建新 Key
4. 复制 Key
5. 查看是否有免费积分促销活动，如有则申请200积分

> API 积分与网页端积分独立（网页端每月800积分不适用于 API）。200积分促销活动可能随时结束。

---

### 6. MiniMax 海螺 — 付费

| 项目 | 详情 |
|---|---|
| 平台 | MiniMax 开放平台 |
| 地址 | https://platform.minimaxi.com |
| 免费额度 | **无免费额度。约 ¥0.7/视频 (512P 6秒) 至 ¥3.7/视频 (1080P 6秒)** |
| 环境变量 | `MINIMAX_API_KEY`，`MINIMAX_API_HOST`（默认 `https://api.minimax.chat`） |

**注册步骤：**
1. 访问 https://platform.minimaxi.com 注册（需中国手机号）
2. 完成实名认证（API 访问必须）
3. 在 **API Keys** 页面创建新 Key
4. 复制 Key（格式：`sk-api-xxxxxxxxxxxxxxxx`）
5. 在充值中心充值（最低约 ¥10）

> 海螺 2.3 模型在所有平台中画质最好。API Host 默认为 `https://api.minimax.chat`。

---

### 7. Google Veo (Vertex AI) — GCP 赠金

| 项目 | 详情 |
|---|---|
| 平台 | Google Cloud Vertex AI |
| 地址 | https://console.cloud.google.com |
| 免费额度 | **无免费额度。使用 GCP 赠金/计费。~$0.15-$0.75/秒** |
| 环境变量 | `GCP_PROJECT_ID`，`GCP_REGION`（可选） |

**配置步骤：**
1. 创建 GCP 项目并启用计费：https://console.cloud.google.com/projectcreate
2. 启用 Vertex AI API：https://console.cloud.google.com/apis/library/aiplatform.googleapis.com
3. 安装 gcloud CLI 并认证：`gcloud auth application-default login`
4. 安装 GCP 依赖：`uv sync --extra gcp`

**可用模型：**

| 模型 | 分辨率 | 价格 |
|---|---|---|
| `veo-2.0-generate-001`（默认） | 720p | ~$0.50/秒 |
| `veo-3.0-generate-001` | 1080p | ~$0.75/秒 |
| `veo-3.0-fast-generate-001` | 1080p | ~$0.15/秒 |

**可选环境变量：**

| 变量 | 默认值 | 说明 |
|---|---|---|
| `VEO_MODEL` | `veo-2.0-generate-001` | 使用的模型 |
| `VEO_GCS_BUCKET` | — | 视频输出 GCS 存储桶（不设则用 base64 内联返回） |
| `GCP_REGION` | `us-central1` | Vertex AI 区域 |

> **认证方式：** Veo 支持两种认证：
> 1. **GCP API Key**（推荐）— 设置 `GEMINI_API_KEY=你的gcp_api_key`，最简单
> 2. **OAuth2 / ADC** — 运行 `gcloud auth application-default login`，无需 API Key，需加 `--extra gcp`

---

## 环境变量汇总

| 变量 | 平台 | 说明 |
|---|---|---|
| `COGVIDEO_API_KEY` | 智谱清影 | 至少 |
| `DASHSCOPE_API_KEY` | 阿里通义万相 | 配置 |
| `KLING_ACCESS_KEY` | 可灵 | 一个 |
| `KLING_SECRET_KEY` | 可灵 | 平台 |
| `SILICONFLOW_API_KEY` | 硅基流动 | |
| `VIDU_API_KEY` | 生数 Vidu | |
| `MINIMAX_API_KEY` | MiniMax 海螺 | |
| `MINIMAX_API_HOST` | MiniMax 海螺 | 可选，默认 `https://api.minimax.chat` |
| `GCP_PROJECT_ID` | Google Veo | Veo 必填 |
| `GCP_REGION` | Google Veo | 可选，默认 `us-central1` |
| `VEO_MODEL` | Google Veo | 可选，默认 `veo-2.0-generate-001` |
| `VEO_GCS_BUCKET` | Google Veo | 可选，视频输出 GCS 存储桶 |
| `VIDEO_OUTPUT_DIR` | 输出目录 | 可选，默认 `./output` |

## 工具说明

### 视频
- **generate_video** — 根据文字描述生成视频。通过 `provider` 参数选择平台。
- **query_video_status** — 查询视频生成状态，完成后自动下载。

### 音频
- **generate_speech** — 文字转语音。参数：`text`（文本）、`voice_id`（可选，声音ID）、`speed`（0.5-2.0，语速）。
- **generate_music** — 根据风格描述生成音乐，支持歌词。参数：`prompt`（风格描述）、`lyrics`（可选，支持 `[Verse]`/`[Chorus]` 结构标签）。

### 工具
- **list_providers** — 列出所有可用的视频、语音、音乐平台。

## 项目结构

```
src/video_gen/
├── __init__.py
├── server.py              # MCP 服务器 + 工具定义
├── providers/
│   ├── __init__.py        # Provider 基类 + 注册机制
│   ├── cogvideo.py        # 智谱 CogVideoX-Flash
│   ├── dashscope.py       # 阿里 通义万相 Wan 2.6
│   ├── kling.py           # 可灵 Kling AI
│   ├── siliconflow.py     # 硅基流动 SiliconFlow
│   ├── vidu.py            # 生数 Vidu
│   ├── minimax.py         # MiniMax 海螺
│   └── veo.py             # Google Veo (Vertex AI)
└── audio/
    ├── __init__.py        # TTS/音乐 基类 + 注册机制
    ├── minimax_tts.py     # MiniMax 语音合成 (speech-2.6-hd)
    └── minimax_music.py   # MiniMax 音乐生成 (music-2.0)
```

### 添加新平台

1. 在 `src/video_gen/providers/` 或 `src/video_gen/audio/` 下创建新文件
2. 实现对应的抽象基类（`BaseProvider`、`BaseTTSProvider` 或 `BaseMusicProvider`）
3. 在 `server.py:_init_providers()` 中注册，通过环境变量控制启用

## 许可证

MIT

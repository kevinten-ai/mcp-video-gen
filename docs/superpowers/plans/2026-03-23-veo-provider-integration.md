# Veo Provider Integration Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Google Veo (2.0/3.0/3.0-fast) as a video generation provider in mcp-video-gen, enabling high-quality video generation via Vertex AI with GCP credits.

**Architecture:** New `VeoProvider` class implementing `BaseProvider`, using Vertex AI's `predictLongRunning` / `fetchPredictOperation` async pattern. Authentication via ADC (`google-auth`). Video returned as base64 (default) or stored in GCS bucket (optional). Added as optional dependency under `[gcp]` extra.

**Tech Stack:** Python 3.10+, httpx, google-auth, Vertex AI REST API

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `src/video_gen/providers/veo.py` | VeoProvider class — generate/query via Vertex AI |
| Modify | `src/video_gen/server.py:42-77` | Register VeoProvider in `_init_providers()` |
| Modify | `src/video_gen/server.py:80-86` | Add "veo" to default provider fallback list |
| Modify | `pyproject.toml` | Add `[project.optional-dependencies]` gcp extra, bump version |
| Modify | `README.md` | Add Veo to provider table and setup docs |
| Modify | `README_CN.md` | Chinese version of the same |

---

## Chunk 1: Core Provider Implementation

### Task 1: Add google-auth optional dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add gcp optional dependency and bump version**

In `pyproject.toml`, add after the `[project.scripts]` section:

```toml
[project.optional-dependencies]
gcp = ["google-auth>=2.20.0"]
```

And change version from `"1.0.0"` to `"1.1.0"`.

- [ ] **Step 2: Sync dependencies**

Run: `cd /Users/kevinten/projects/mcp-video-gen && uv sync --extra gcp`
Expected: installs google-auth and its dependencies

- [ ] **Step 3: Verify import works**

Run: `cd /Users/kevinten/projects/mcp-video-gen && uv run --extra gcp python -c "import google.auth; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
cd /Users/kevinten/projects/mcp-video-gen
git add pyproject.toml uv.lock
git commit -m "feat: add google-auth as optional gcp dependency (v1.1.0)"
```

---

### Task 2: Create VeoProvider

**Files:**
- Create: `src/video_gen/providers/veo.py`

- [ ] **Step 1: Create the VeoProvider implementation**

Create `src/video_gen/providers/veo.py`:

```python
"""Google Veo provider — Vertex AI video generation (Veo 2/3)."""

from __future__ import annotations

import base64
from pathlib import Path
from datetime import datetime
import os

import httpx
from . import BaseProvider, VideoResult

# Supported models
MODELS = {
    "veo-2.0-generate-001": {"name": "Veo 2", "resolution": "720p", "pricing": "~$0.50/s"},
    "veo-3.0-generate-001": {"name": "Veo 3", "resolution": "1080p", "pricing": "~$0.75/s"},
    "veo-3.0-fast-generate-001": {"name": "Veo 3 Fast", "resolution": "1080p", "pricing": "~$0.15/s"},
}

DEFAULT_MODEL = os.getenv("VEO_MODEL", "veo-2.0-generate-001")
GCS_BUCKET = os.getenv("VEO_GCS_BUCKET", "")


def _get_access_token() -> str:
    """Get OAuth2 access token via Application Default Credentials."""
    import google.auth
    import google.auth.transport.requests

    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    credentials.refresh(google.auth.transport.requests.Request())
    return credentials.token


class VeoProvider(BaseProvider):
    def __init__(self, project_id: str, region: str = "us-central1"):
        self.project_id = project_id
        self.region = region

    @property
    def name(self) -> str:
        return "veo"

    @property
    def description(self) -> str:
        models = ", ".join(MODELS.keys())
        return f"Google Veo (Vertex AI) — High quality video generation. Models: {models}. Default: {DEFAULT_MODEL}"

    @property
    def free_tier_info(self) -> str:
        return "Uses GCP credits/billing. No free tier."

    def _base_url(self, model: str) -> str:
        return (
            f"https://{self.region}-aiplatform.googleapis.com/v1/"
            f"projects/{self.project_id}/locations/{self.region}/"
            f"publishers/google/models/{model}"
        )

    async def generate(
        self,
        prompt: str,
        duration: int = 8,
        aspect_ratio: str = "16:9",
    ) -> VideoResult:
        model = DEFAULT_MODEL
        url = f"{self._base_url(model)}:predictLongRunning"

        parameters: dict = {
            "sampleCount": 1,
            "durationSeconds": min(max(duration, 5), 8),
            "aspectRatio": aspect_ratio,
            "enhancePrompt": True,
            "personGeneration": "allow_adult",
        }
        if GCS_BUCKET:
            parameters["storageUri"] = f"gs://{GCS_BUCKET}/"

        body = {
            "instances": [{"prompt": prompt}],
            "parameters": parameters,
        }

        try:
            token = _get_access_token()
        except Exception as e:
            return VideoResult(
                task_id="", status="failed",
                error=f"Auth failed: {e}. Run: gcloud auth application-default login",
            )

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=60.0,
            )
            try:
                data = resp.json()
            except Exception:
                return VideoResult(task_id="", status="failed", error=f"HTTP {resp.status_code}")

            if resp.status_code != 200:
                msg = data.get("error", {}).get("message", "Unknown error")
                return VideoResult(task_id="", status="failed", error=f"Veo API error ({resp.status_code}): {msg}")

            # Response: {"name": "projects/.../operations/OPERATION_ID"}
            operation_name = data.get("name", "")
            if not operation_name:
                return VideoResult(task_id="", status="failed", error="No operation name returned")

            return VideoResult(task_id=operation_name, status="processing")

    async def query(self, task_id: str) -> VideoResult:
        # task_id is the full operation name:
        # "projects/{PROJECT}/locations/{REGION}/publishers/google/models/{MODEL}/operations/{OP_ID}"
        # Extract model from it to build the fetchPredictOperation URL
        try:
            parts = task_id.split("/")
            model_idx = parts.index("models") + 1
            model = parts[model_idx]
        except (ValueError, IndexError):
            model = DEFAULT_MODEL

        url = f"{self._base_url(model)}:fetchPredictOperation"

        try:
            token = _get_access_token()
        except Exception as e:
            return VideoResult(
                task_id=task_id, status="failed",
                error=f"Auth failed: {e}",
            )

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={"operationName": task_id},
                timeout=60.0,
            )
            try:
                data = resp.json()
            except Exception:
                return VideoResult(task_id=task_id, status="failed", error=f"HTTP {resp.status_code}")

            if resp.status_code != 200:
                msg = data.get("error", {}).get("message", "Unknown error")
                return VideoResult(task_id=task_id, status="failed", error=f"Veo query error: {msg}")

            done = data.get("done", False)
            if not done:
                return VideoResult(task_id=task_id, status="processing")

            # Done — extract video
            response = data.get("response", {})
            videos = response.get("videos", [])

            if not videos:
                filtered = response.get("raiMediaFilteredCount", 0)
                if filtered:
                    return VideoResult(task_id=task_id, status="failed", error=f"Video blocked by safety filter ({filtered} filtered)")
                return VideoResult(task_id=task_id, status="failed", error="No video in response")

            video = videos[0]

            # GCS mode: return gcsUri as video_url
            if "gcsUri" in video:
                return VideoResult(task_id=task_id, status="success", video_url=video["gcsUri"])

            # Base64 mode: decode and save locally
            if "bytesBase64Encoded" in video:
                video_bytes = base64.b64decode(video["bytesBase64Encoded"])
                output_dir = os.getenv("VIDEO_OUTPUT_DIR", os.path.join(os.getcwd(), "output"))
                out = Path(output_dir)
                out.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath = out / f"veo_{timestamp}.mp4"
                filepath.write_bytes(video_bytes)
                # Return local file path as video_url so server.py can report it
                return VideoResult(task_id=task_id, status="success", video_url=str(filepath))

            return VideoResult(task_id=task_id, status="failed", error="Unknown video format in response")
```

- [ ] **Step 2: Verify the file is syntactically correct**

Run: `cd /Users/kevinten/projects/mcp-video-gen && uv run --extra gcp python -c "from video_gen.providers.veo import VeoProvider; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
cd /Users/kevinten/projects/mcp-video-gen
git add src/video_gen/providers/veo.py
git commit -m "feat: add VeoProvider with Vertex AI predictLongRunning support"
```

---

### Task 3: Register VeoProvider in server.py

**Files:**
- Modify: `src/video_gen/server.py:20-25` (imports)
- Modify: `src/video_gen/server.py:42-77` (`_init_providers`)
- Modify: `src/video_gen/server.py:80-86` (`_default_provider_name`)
- Modify: `src/video_gen/server.py:306-335` (`query_video_status` handler)

- [ ] **Step 1: Add VeoProvider import**

After `from .providers.vidu import ViduProvider` (line 25), add:

```python
try:
    from .providers.veo import VeoProvider
except ImportError:
    VeoProvider = None  # google-auth not installed
```

- [ ] **Step 2: Register Veo in _init_providers()**

After the vidu block (line 68), add:

```python
    # Veo (Google Vertex AI) — requires google-auth
    gcp_project = os.getenv("GCP_PROJECT_ID", "")
    if gcp_project and VeoProvider is not None:
        gcp_region = os.getenv("GCP_REGION", "us-central1")
        register_provider(VeoProvider(gcp_project, gcp_region))
```

- [ ] **Step 3: Add "veo" to default provider fallback**

In `_default_provider_name()`, change the `for` loop tuple from:
```python
    for name in ("cogvideo", "dashscope", "kling", "siliconflow", "vidu", "minimax"):
```
to:
```python
    for name in ("cogvideo", "dashscope", "kling", "siliconflow", "vidu", "minimax", "veo"):
```

Veo is last because it costs money — free providers should be preferred by default.

- [ ] **Step 4: Handle Veo's local-file video_url in query_video_status**

In the `query_video_status` handler (around line 324-335), the current code calls `_try_download(result.video_url, ...)`. For Veo base64 mode, `video_url` is already a local filepath (no download needed). Modify the success handling:

Replace the block:
```python
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
```

With:
```python
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
```

- [ ] **Step 5: Bump server version**

Change `server_version="1.0.0"` to `server_version="1.1.0"` (around line 410).

- [ ] **Step 6: Verify server starts without GCP config**

Run: `cd /Users/kevinten/projects/mcp-video-gen && uv run python -c "from video_gen.server import server; print('ok')"`
Expected: `ok` (Veo not registered since GCP_PROJECT_ID not set, but no import error)

- [ ] **Step 7: Commit**

```bash
cd /Users/kevinten/projects/mcp-video-gen
git add src/video_gen/server.py
git commit -m "feat: register VeoProvider, handle local file paths in query result"
```

---

## Chunk 2: Documentation & Testing

### Task 4: Update README.md

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add Veo to the provider comparison table**

Add a new row to the provider table:

```markdown
| Google Veo | veo-2.0-generate-001 | GCP credits | 720p-1080p | 5-8s |
```

- [ ] **Step 2: Add Veo setup section**

Add a new section under the Vidu setup (or after all providers):

```markdown
### Google Veo (Vertex AI)

Requires GCP project with billing and Vertex AI API enabled.

**1. Prerequisites**
- GCP project with billing: https://console.cloud.google.com/projectcreate
- Enable Vertex AI API: https://console.cloud.google.com/apis/library/aiplatform.googleapis.com
- Install gcloud CLI and run: `gcloud auth application-default login`

**2. Install with GCP support**
\`\`\`bash
uv sync --extra gcp
\`\`\`

**3. Configure**
\`\`\`bash
claude mcp add --transport stdio mcp-video \
  --env GCP_PROJECT_ID=your-project-id \
  --env GCP_REGION=us-central1 \
  -- uv --directory /path/to/mcp-video-gen --extra gcp run video-gen
\`\`\`

**Optional environment variables:**
| Variable | Default | Description |
|---|---|---|
| `VEO_MODEL` | `veo-2.0-generate-001` | Model to use. Options: `veo-2.0-generate-001`, `veo-3.0-generate-001`, `veo-3.0-fast-generate-001` |
| `VEO_GCS_BUCKET` | — | GCS bucket for video output. If unset, uses base64 inline return. |
| `GCP_REGION` | `us-central1` | Vertex AI region |
```

- [ ] **Step 3: Add Veo to the environment variables table**

Add rows:
```markdown
| `GCP_PROJECT_ID` | Veo only | — | GCP project ID |
| `GCP_REGION` | No | `us-central1` | Vertex AI region |
| `VEO_MODEL` | No | `veo-2.0-generate-001` | Veo model ID |
| `VEO_GCS_BUCKET` | No | — | GCS bucket for video output |
```

- [ ] **Step 4: Commit**

```bash
cd /Users/kevinten/projects/mcp-video-gen
git add README.md
git commit -m "docs: add Veo provider setup and configuration to README"
```

---

### Task 5: Update README_CN.md

**Files:**
- Modify: `README_CN.md`

- [ ] **Step 1: Mirror Veo additions in Chinese README**

Add equivalent Chinese content:
- Provider table row
- Setup section
- Environment variables

- [ ] **Step 2: Commit**

```bash
cd /Users/kevinten/projects/mcp-video-gen
git add README_CN.md
git commit -m "docs: add Veo provider to Chinese README"
```

---

### Task 6: Smoke test with real Vertex AI

**Files:** None (manual testing)

- [ ] **Step 1: Start server with Veo configured**

Run:
```bash
cd /Users/kevinten/projects/mcp-video-gen
GCP_PROJECT_ID=logical-bird-240509 GCP_REGION=us-central1 \
  uv run --extra gcp python -c "
from video_gen.providers import list_providers
from video_gen.server import _init_providers
print('Providers:', list(list_providers().keys()))
assert 'veo' in list_providers(), 'Veo not registered'
print('OK: Veo registered')
"
```
Expected: `OK: Veo registered`

- [ ] **Step 2: Test generate via MCP Inspector (optional)**

Run:
```bash
GCP_PROJECT_ID=logical-bird-240509 \
  npx @modelcontextprotocol/inspector uv --directory /Users/kevinten/projects/mcp-video-gen --extra gcp run video-gen
```

Call `generate_video` with `provider=veo`, `prompt="A drone shot flying over ocean waves at sunset"`.
Expected: Returns task_id (operation name).

Then call `query_video_status` with the task_id and `provider=veo`.
Expected: Eventually returns "success" with saved file path.

- [ ] **Step 3: Final push**

```bash
cd /Users/kevinten/projects/mcp-video-gen
git push
```

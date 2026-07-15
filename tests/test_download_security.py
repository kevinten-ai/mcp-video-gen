import asyncio

from video_gen import server
from video_gen.providers import veo


class FakeResponse:
    def __init__(self, content=b"video", headers=None):
        self.status_code = 200
        self.content = content
        self.headers = headers or {}

    async def aiter_bytes(self):
        yield self.content


class FakeStream:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self.response

    async def __aexit__(self, *_args):
        return None


class FakeClient:
    def __init__(self, captured, response=None, **kwargs):
        self.captured = captured
        self.response = response or FakeResponse()
        captured["client_kwargs"] = kwargs
        captured["constructed"] = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def get(self, url, **kwargs):
        self.captured["url"] = url
        return self.response

    def stream(self, method, url, **kwargs):
        self.captured["method"] = method
        self.captured["url"] = url
        return FakeStream(self.response)


def test_auto_download_keeps_tls_verification_enabled(monkeypatch, tmp_path):
    captured = {}
    monkeypatch.setattr(
        server.httpx,
        "AsyncClient",
        lambda **kwargs: FakeClient(captured, **kwargs),
    )

    result = asyncio.run(
        server._try_download("https://cdn.example/video.mp4", str(tmp_path), "veo")
    )

    assert result is not None
    assert captured["client_kwargs"].get("verify", True) is True


def test_auto_download_rejects_non_http_urls(monkeypatch, tmp_path):
    captured = {"constructed": False}
    monkeypatch.setattr(
        server.httpx,
        "AsyncClient",
        lambda **kwargs: FakeClient(captured, **kwargs),
    )

    result = asyncio.run(
        server._try_download("file:///etc/passwd", str(tmp_path), "veo")
    )

    assert result is None
    assert captured["constructed"] is False


def test_auto_download_handles_malformed_urls(monkeypatch, tmp_path):
    captured = {"constructed": False}
    monkeypatch.setattr(
        server.httpx,
        "AsyncClient",
        lambda **kwargs: FakeClient(captured, **kwargs),
    )

    result = asyncio.run(server._try_download("http://[", str(tmp_path), "veo"))

    assert result is None
    assert captured["constructed"] is False


def test_veo_reference_image_keeps_tls_verification_enabled(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        veo.httpx,
        "AsyncClient",
        lambda **kwargs: FakeClient(
            captured,
            FakeResponse(content=b"image", headers={"content-type": "image/png"}),
            **kwargs,
        ),
    )

    result = asyncio.run(
        veo.VeoProvider("project")._load_image("https://cdn.example/image.png")
    )

    assert result is not None
    assert captured["client_kwargs"].get("verify", True) is True


def test_veo_reference_image_rejects_local_network_urls(monkeypatch):
    captured = {"constructed": False}
    monkeypatch.setattr(
        veo.httpx,
        "AsyncClient",
        lambda **kwargs: FakeClient(captured, **kwargs),
    )

    result = asyncio.run(
        veo.VeoProvider("project")._load_image("http://127.0.0.1/private.png")
    )

    assert result is None
    assert captured["constructed"] is False


def test_veo_reference_image_rejects_oversized_remote_files(monkeypatch):
    captured = {}
    response = FakeResponse(
        content=b"small fixture",
        headers={
            "content-type": "image/png",
            "content-length": str(veo.MAX_REFERENCE_IMAGE_BYTES + 1),
        },
    )
    monkeypatch.setattr(
        veo.httpx,
        "AsyncClient",
        lambda **kwargs: FakeClient(captured, response, **kwargs),
    )

    result = asyncio.run(
        veo.VeoProvider("project")._load_image("https://cdn.example/large.png")
    )

    assert result is None


def test_veo_reference_image_stops_streams_without_content_length(monkeypatch):
    captured = {}
    monkeypatch.setattr(veo, "MAX_REFERENCE_IMAGE_BYTES", 4)
    monkeypatch.setattr(
        veo.httpx,
        "AsyncClient",
        lambda **kwargs: FakeClient(
            captured,
            FakeResponse(content=b"12345", headers={"content-type": "image/png"}),
            **kwargs,
        ),
    )

    result = asyncio.run(
        veo.VeoProvider("project")._load_image("https://cdn.example/large.png")
    )

    assert result is None

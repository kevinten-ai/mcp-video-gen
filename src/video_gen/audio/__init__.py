from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AudioResult:
    status: str  # "success", "failed"
    audio_url: str | None = None
    audio_data: bytes | None = None
    error: str | None = None


class BaseTTSProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @abstractmethod
    async def speak(self, text: str, voice_id: str | None = None, speed: float = 1.0) -> AudioResult: ...


class BaseMusicProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @abstractmethod
    async def generate(self, prompt: str, lyrics: str | None = None) -> AudioResult: ...


_tts_providers: dict[str, BaseTTSProvider] = {}
_music_providers: dict[str, BaseMusicProvider] = {}


def register_tts(provider: BaseTTSProvider) -> None:
    _tts_providers[provider.name] = provider


def register_music(provider: BaseMusicProvider) -> None:
    _music_providers[provider.name] = provider


def get_tts(name: str) -> BaseTTSProvider | None:
    return _tts_providers.get(name)


def get_music(name: str) -> BaseMusicProvider | None:
    return _music_providers.get(name)


def list_tts() -> dict[str, BaseTTSProvider]:
    return dict(_tts_providers)


def list_music() -> dict[str, BaseMusicProvider]:
    return dict(_music_providers)

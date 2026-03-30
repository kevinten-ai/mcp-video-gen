from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class VideoResult:
    task_id: str
    status: str  # "processing", "success", "failed"
    video_url: str | None = None
    error: str | None = None


class BaseProvider(ABC):
    """Base class for video generation providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @property
    @abstractmethod
    def free_tier_info(self) -> str:
        ...

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        image_url: str | None = None,
    ) -> VideoResult:
        ...

    @abstractmethod
    async def query(self, task_id: str) -> VideoResult:
        ...


# Provider registry
_providers: dict[str, BaseProvider] = {}


def register_provider(provider: BaseProvider) -> None:
    _providers[provider.name] = provider


def get_provider(name: str) -> BaseProvider | None:
    return _providers.get(name)


def list_providers() -> dict[str, BaseProvider]:
    return dict(_providers)

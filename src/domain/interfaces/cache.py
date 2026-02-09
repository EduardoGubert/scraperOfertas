from __future__ import annotations

from typing import Protocol


class ICache(Protocol):
    async def exists(self, key: str) -> bool:
        ...

    async def set(self, key: str) -> None:
        ...

    async def delete(self, key: str) -> None:
        ...

    async def close(self) -> None:
        ...

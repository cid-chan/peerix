import typing as t
from peerix.store import NarInfo, Store


class PrefixStore(Store):
    def __init__(self, prefix: str, backend: Store):
        self.backend = backend
        self.prefix = prefix

    async def cache_info(self):
        return await self.backend.cache_info()

    async def narinfo(self, hsh: str) -> t.Optional[NarInfo]:
        info = await self.backend.narinfo(hsh)
        if info is None:
            return None
        return info._replace(url=f"{self.prefix}/{info.url}")

    async def nar(self, path: str) -> t.AsyncIterable[bytes]:
        if not path.startswith(self.prefix + "/"):
            raise FileNotFoundError("Not found.")

        async for chunk in self.backend.nar(path[len(self.prefix)+1:]):
            yield chunk


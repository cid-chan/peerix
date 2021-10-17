import typing as t


class NarInfo(t.NamedTuple):
    storePath: str
    url: str
    compression: t.Literal["none"]
    narHash: str
    narSize: int
    references: t.Sequence[str]
    deriver: t.Optional[str]
    signatures: t.Sequence[str]

    def dump(self) -> str:
        lines = [
            f"StorePath: {self.storePath}",
            f"URL: {self.url}",
            f"Compression: {self.compression}",
            f"NarHash: {self.narHash}",
            f"NarSize: {self.narSize}"
        ]
        if self.references:
            lines.append(f"References: {' '.join(self.references)}")
        if self.deriver:
            lines.append(f"Deriver: {self.deriver} ")
        for sig in self.signatures:
            lines.append(f"Sig: {sig}")

        return "\n".join(lines)

    @classmethod
    def parse(cls, data: str) -> "NarInfo":
        storePath = ""
        url = ""
        compression = "none"
        narHash = ""
        narSize = -1
        references = []
        deriver = None
        signatures = []

        for line in data.splitlines():
            k, v = line.split(":", 1)
            v = v.strip()
            k = k.strip()

            if k == "StorePath":
                storePath = v
            elif k == "URL":
                url = v
            elif k == "Compression" and v == "none":
                compression = v
            elif k == "NarHash":
                narHash = v
            elif k == "NarSize":
                narSize = int(v)
            elif k == "References":
                references = v.split(" ")
            elif k == "Deriver":
                deriver = v
            elif k == "Sig":
                signatures.append(v)

        return NarInfo(storePath, url, compression, narHash, narSize, references, deriver, signatures)
        


class CacheInfo(t.NamedTuple):
    storeDir: str
    wantMassQuery: int
    priority: int

    def dump(self) -> str:
        return "\n".join((
            f"StoreDir: {self.storeDir}",
            f"WantMassQuery: {self.wantMassQuery}",
            f"Priority: {self.priority}"
        ))


class Store:

    async def cache_info(self) -> CacheInfo:
        raise NotImplementedError()

    async def narinfo(self, hsh: str) -> t.Optional[NarInfo]:
        raise NotImplementedError()

    async def nar(self, url: str) -> t.AsyncIterable[bytes]:
        raise NotImplementedError()
        

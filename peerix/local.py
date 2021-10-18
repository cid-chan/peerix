import typing as t

import contextlib
import subprocess
import tempfile
import logging
import asyncio
import shutil
import base64
import sys
import os

import aiohttp

from peerix.store import NarInfo, CacheInfo, Store


nix_serve = shutil.which("nix-serve")
if nix_serve is None:
    raise RuntimeError("nix-serve is not installed.")

nix = shutil.which("nix")
if nix is None:
    raise RuntimeError("nix is not installed.")

assert nix_serve is not None
assert nix is not None


logger = logging.getLogger("peerix.local")


class LocalStore(Store):

    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self._cache: t.Optional[CacheInfo] = None

    async def cache_info(self) -> CacheInfo:
        if self._cache is None:
            async with self.session.get("http://_/nix-cache-info") as resp:
                storeDir = ""
                wantMassQuery = -1
                priority = 50

                for line in (await resp.text()).splitlines():
                    k, v = line.split(":", 1)
                    v = v.strip()
                    k = k.strip()

                    if k == "StoreDir":
                        storeDir = v
                    elif k == "WantMassQuery":
                        wantMassQuery = int(v)
                    elif k == "Priority":
                        priority = int(v)

                self._cache = CacheInfo(storeDir, wantMassQuery, priority)

        return self._cache


    async def narinfo(self, hsh: str) -> t.Optional[NarInfo]:
        async with self.session.get(f"http://_/{hsh}.narinfo") as resp:
            if resp.status == 404:
                return None
            info = NarInfo.parse(await resp.text())
        return info._replace(url=base64.b64encode(info.storePath.encode("utf-8")).replace(b"/", b"_").decode("ascii")+".nar")

    async def nar(self, sp: str) -> t.Awaitable[t.AsyncIterable[bytes]]:
        if sp.endswith(".nar"):
            sp = sp[:-4]
        path = base64.b64decode(sp.replace("_", "/")).decode("utf-8")
        if not path.startswith((await self.cache_info()).storeDir):
            raise FileNotFoundError()

        if not os.path.exists(path):
            raise FileNotFoundError()

        return self._nar_pull(path)

    async def _nar_pull(self, path: str) -> t.AsyncIterable[bytes]:
        logger.info(f"Serving {path}")
        process = await asyncio.create_subprocess_exec(
                nix, "dump-path", "--", path,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )

        assert process.stdout is not None
        while not process.stdout.at_eof():
            yield await process.stdout.read(10*1024*1024)

        logger.debug(f"Served {path}")
        try:
            process.terminate()
        except ProcessLookupError:
            pass


@contextlib.asynccontextmanager
async def local():
    with tempfile.TemporaryDirectory() as tmpdir:
        sock = f"{tmpdir}/server.sock"

        logger.info("Launching nix-serve.")
        process = await asyncio.create_subprocess_exec(
            nix_serve, "--listen", sock,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=sys.stderr
        )
        for _ in range(10):
            if os.path.exists(sock):
                break
            await asyncio.sleep(1)
        else:
            raise RuntimeError("Failed to start up local store.")

        try:
            connector = aiohttp.UnixConnector(sock)
            async with aiohttp.ClientSession(connector_owner=True, connector=connector) as session:
                yield LocalStore(session)
        finally:
            try:
                process.terminate()
            except ProcessLookupError:
                pass

            logger.info("nix-serve exited.")


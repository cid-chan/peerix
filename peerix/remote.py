import typing as t

import socket
import logging
import asyncio
import ipaddress
import contextlib

import psutil
import aiohttp


from peerix.store import NarInfo, Store


logger = logging.getLogger("peerix.remote")



def get_brdcasts():
    for interface, iaddrs in psutil.net_if_addrs().items():
        for iaddr in iaddrs:
            if iaddr.broadcast is None or iaddr.family != socket.AF_INET:
                continue

            ifa = ipaddress.IPv4Interface(f"{iaddr.address}/{iaddr.netmask}")
            if not ifa.network.is_private:
                continue

            yield str(ifa.network.broadcast_address)


def get_myself():
    for interface, iaddrs in psutil.net_if_addrs().items():
        for iaddr in iaddrs:
            if iaddr.broadcast is None or iaddr.family != socket.AF_INET:
                continue

            yield str(iaddr.address)


class DiscoveryProtocol(asyncio.DatagramProtocol, Store):
    idx: int
    transport: asyncio.DatagramTransport
    waiters: t.Dict[int, asyncio.Future]
    store: Store
    session: aiohttp.ClientSession
    local_port: int
    prefix: str
    timeout: float

    def __init__(self, store: Store, session: aiohttp.ClientSession, local_port: int, prefix: str, timeout: float):
        self.idx = 0
        self.waiters = {}
        self.store = store
        self.session = session
        self.local_port = local_port
        self.prefix = prefix
        self.timeout = timeout

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr: t.Tuple[str, int]) -> None:
        if addr[0] in set(get_myself()):
            logger.debug(f"Ignoring packet from {addr[0]}")
            return

        # 0 => Response to a command of mine.
        if data[0] == 1:
            idx = int.from_bytes(data[1:5], "big")
            if idx not in self.waiters:
                return

            self.waiters[idx].set_result((int.from_bytes(data[5:9], "big"), data[9:].decode("utf-8"), addr))

        # 1 => Request from another server.
        elif data[0] == 0:
            asyncio.create_task(self.respond(data, addr))

    def stop(self):
        self.transport.close()

    async def cache_info(self):
        return await self.store.cache_info()

    async def respond(self, data: bytes, addr: t.Tuple[str, int]) -> None:
        hsh = data[5:].decode("utf-8")
        logger.info(f"Got request from {addr[0]}:{addr[1]} for {hsh}")
        narinfo = await self.store.narinfo(hsh)
        if narinfo is None:
            logger.debug(f"{hsh} not found")
            return

        logger.debug(f"{hsh} was found.")
        self.transport.sendto(b"".join([
            b"\x01",
            data[1:5],
            self.local_port.to_bytes(4, "big"),
            self.prefix.encode("utf-8"),
            b"/",
            hsh.encode("utf-8"),
            b".narinfo"
        ]), addr)

    async def narinfo(self, hsh: str) -> t.Optional[NarInfo]:
        fut = asyncio.get_running_loop().create_future()
        self.idx = (idx := self.idx)+1
        self.waiters[idx] = fut
        fut.add_done_callback(lambda _: self.waiters.pop(idx, None))
        logging.info(f"Requesting {hsh} from direct local network.")
        for addr in set(get_brdcasts()):
            logging.debug(f"Sending request for {hsh} to {addr}:{self.local_port}")
            self.transport.sendto(b"".join([b"\x00", idx.to_bytes(4, "big"), hsh.encode("utf-8")]), (addr, self.local_port))

        try:
            # This must have a short timeout so it does not noticably slow down
            # querying of other caches.
            port, url, addr = await asyncio.wait_for(fut, self.timeout)
        except asyncio.TimeoutError:
            logging.debug(f"No response for {hsh}")
            return None

        logging.info(f"{addr[0]}:{addr[1]} responded for {hsh} with http://{addr[0]}:{port}/{url}")

        async with self.session.get(f"http://{addr[0]}:{port}/{url}") as resp:
            if resp.status != 200:
                return
            info = NarInfo.parse(await resp.text())

        return info._replace(url = f"{addr[0]}/{port}/{hsh}/{info.url}")

    async def nar(self, sp: str) -> t.Awaitable[t.AsyncIterable[bytes]]:
        try:
            return await self._nar_req(sp)
        except (FileNotFoundError, aiohttp.ServerTimeoutError):
            addr1, addr2, hsh = sp.split("/", 2)
            logging.warn(f"Remote({addr1}:{addr2})-store path is dead: {sp}")
            pass

        _, _, hsh, _ = sp.split("/", 3)
        narinfo = await self.narinfo(hsh)
        if narinfo is None:
            logging.warn(f"All sources are gone.")
            raise FileNotFoundError()

        return await self._nar_req(narinfo.url)

    async def _nar_req(self, url: str) -> t.Awaitable[t.AsyncIterable[bytes]]:
        addr1, addr2, _, p = url.split("/", 3)
        resp = await self.session.get(f"http://{addr1}:{addr2}/{p}")
        if resp.status == 200:
            return self._nar_direct(resp)
        else:
            raise FileNotFoundError()


    async def _nar_direct(self, resp: aiohttp.ClientResponse) -> t.AsyncIterable[bytes]:
        try:
            content = resp.content
            while not content.at_eof():
                yield await content.readany()
        finally:
            resp.close()
            await resp.wait_for_close()


@contextlib.asynccontextmanager
async def remote(store: Store, local_port: int, local_addr: str="0.0.0.0", prefix: str="local", timeout: float = 0.05):
    protocol: DiscoveryProtocol
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(sock_connect=timeout)) as session:
        _, protocol = await asyncio.get_running_loop().create_datagram_endpoint(
            lambda: DiscoveryProtocol(store, session, local_port, prefix, timeout),
            local_addr=(local_addr, local_port),
            family=socket.AF_INET,
            allow_broadcast=True
        )
        try:
            yield protocol
        finally:
            protocol.stop()

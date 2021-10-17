import typing as t

import socket
import asyncio
import ipaddress
import contextlib

import psutil
import aiohttp


from peerix.store import NarInfo, Store


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

    def __init__(self, store: Store, session: aiohttp.ClientSession, local_port: int):
        self.idx = 0
        self.waiters = {}
        self.store = store
        self.session = session
        self.local_port = local_port

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr: t.Tuple[str, int]) -> None:
        print(set(get_myself()))
        if addr[0] in set(get_myself()):
            print(f"Ignoring packet from {addr[0]}")
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
        print(f"Got request from {addr[0]}:{addr[1]} for {hsh}")
        narinfo = await self.store.narinfo(hsh)
        if narinfo is None:
            return

        self.transport.sendto(b"\x01" + data[1:5] + self.local_port.to_bytes(4, "big") + narinfo.url.encode("utf-8"), addr)

    async def narinfo(self, hsh: str) -> t.Optional[NarInfo]:
        fut = asyncio.get_running_loop().create_future()
        self.idx = (idx := self.idx)+1
        self.waiters[idx] = fut
        fut.add_done_callback(lambda _: self.waiters.pop(idx, None))
        print(f"Requesting {hsh} from direct local network.")
        for addr in set(get_brdcasts()):
            self.transport.sendto(b"".join([b"\x00", idx.to_bytes(4, "big"), hsh.encode("utf-8")]), (addr, self.local_port))

        try:
            port, url, addr = await asyncio.wait_for(fut, 0.5)
        except asyncio.TimeoutError:
            print(f"No response for {hsh}")
            return None

        print(f"{addr[0]}:{addr[1]} responded for {hsh} with http://{addr[0]}:{port}/{url}")

        async with self.session.get(f"http://{addr[0]}:{port}/{url}") as resp:
            if resp.status != 200:
                return
            info = NarInfo.parse(await resp.text())

        return info._replace(url = f"{addr[0]}/{port}/{info.url}")

    async def nar(self, sp: str) -> t.AsyncIterable[bytes]:
        addr1, addr2, p = sp.split("/", 2)
        async with self.session.get(f"http://{addr1}:{addr2}/{p}") as resp:
            if resp.status != 200:
                raise FileNotFoundError("Not found.")
            content = resp.content
            while not content.at_eof():
                yield await content.readany()



@contextlib.asynccontextmanager
async def remote(store: Store, local_port: int, local_addr: str="0.0.0.0"):
    protocol: DiscoveryProtocol
    async with aiohttp.ClientSession() as session:
        _, protocol = await asyncio.get_running_loop().create_datagram_endpoint(
            lambda: DiscoveryProtocol(store, session, local_port),
            local_addr=(local_addr, local_port),
            family=socket.AF_INET,
            allow_broadcast=True
        )
        try:
            yield protocol
        finally:
            protocol.stop()

import asyncio
import contextlib

from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.applications import Starlette

from peerix.local import local
from peerix.remote import remote
from peerix.prefix import PrefixStore



@contextlib.asynccontextmanager
async def _setup_stores(local_port: int):
    global l_access, r_access
    async with local() as l:
        l_access = PrefixStore("local/nar", l)
        lp = PrefixStore("local", l)
        async with remote(lp, local_port, "0.0.0.0") as r:
            r_access = PrefixStore("remote", r)
            yield
setup_store = _setup_stores(12304)


app = Starlette()

@app.on_event("startup")
async def _setup_stores_init():
    await setup_store.__aenter__()

@app.on_event("shutdown")
async def _setup_stores_deinit():
    await setup_store.__aexit__(None, None, None)


@app.route("/nix-cache-info")
async def cache_info(_: Request) -> Response:
    ci = await l_access.cache_info()
    ci = ci._replace(priority=20)
    return Response(content=ci.dump())


@app.route("/{hash:str}.narinfo")
async def narinfo(req: Request) -> Response:
    if req.client.host != "127.0.0.1":
        return Response(content="Permission denied.", status_code=403)
    
    ni = await r_access.narinfo(req.path_params["hash"])
    if ni is None:
        return Response(content="Not found", status_code=404)

    return Response(content=ni.dump(), status_code=200, media_type="text/x-nix-narinfo")

@app.route("/local/{hash:str}.narinfo")
async def access_narinfo(req: Request) -> Response:
    ni = await l_access.narinfo(req.path_params["hash"])
    if ni is None:
        return Response(content="Not found", status_code=404)

    return Response(content=ni.dump(), status_code=200, media_type="text/x-nix-narinfo")


@app.route("/local/nar/{path:str}")
async def push_nar(req: Request) -> Response:
    return StreamingResponse(l_access.nar(f"local/nar/{req.path_params['path']}"), media_type="text/plain")


@app.route("/remote/{path:path}")
async def pull_nar(req: Request) -> Response:
    return StreamingResponse(l_access.nar(f"remote/{req.path_params['path']}"), media_type="text/plain")

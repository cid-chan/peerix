import asyncio
import uvloop
from hypercorn import Config
from hypercorn.asyncio import serve

from peerix.app import app


if __name__ == "__main__":
    uvloop.install()
    config = Config()
    config.bind = ["0.0.0.0:12304"]
    asyncio.run(serve(app, config))

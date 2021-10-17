import logging
import asyncio

import uvloop
from hypercorn import Config
from hypercorn.asyncio import serve

from peerix.app import app


def run():
    logging.basicConfig()
    uvloop.install()
    config = Config()
    config.bind = ["0.0.0.0:12304"]
    asyncio.run(serve(app, config))


if __name__ == "__main__":
    run()

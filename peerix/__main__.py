import os
import logging
import asyncio
import argparse

import uvloop
from hypercorn import Config
from hypercorn.asyncio import serve

from peerix.app import app, setup_stores


parser = argparse.ArgumentParser(description="Peerix nix binary cache.")
parser.add_argument("--verbose", action="store_const", const=logging.DEBUG, default=logging.INFO, dest="loglevel")
parser.add_argument("--port", default=12304, type=int)
parser.add_argument("--private-key", required=False)
parser.add_argument("--timeout", type=int, default=50)

def run():
    args = parser.parse_args()
    if args.private_key is not None:
        os.environ["NIX_SECRET_KEY_FILE"] = os.path.abspath(os.path.expanduser(args.private_key))

    logging.basicConfig(level=args.loglevel)
    uvloop.install()

    asyncio.run(main(args.port, args.timeout / 1000.0))


async def main(port: int, timeout: float):
    config = Config()
    config.bind = [f"0.0.0.0:{port}"]

    async with setup_stores(port, timeout):
        await serve(app, config)


if __name__ == "__main__":
    run()

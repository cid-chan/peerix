#setup.py:
import os
from distutils.core import setup

DIR = os.path.dirname(__file__)

with open(os.path.join(DIR, "requirements.txt")) as f:
    requirements = [l.strip() for l in f.readlines()]

with open(os.path.join(DIR, "VERSION")) as f:
    version = f.read().strip()

setup(
    name="peerix",
    entry_points={
        "console_scripts": [
            'peerix = peerix.__main__:run'
        ]
    },
    version=version,
    requires=requirements
)

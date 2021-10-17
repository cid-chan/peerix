#setup.py:
import os
from setuptools import setup, find_packages

DIR = os.path.dirname(__file__)

with open(os.path.join(DIR, "requirements.txt")) as f:
    requirements = [l.strip() for l in f.readlines()]

with open(os.path.join(DIR, "VERSION")) as f:
    version = f.read().strip()

setup(
    name="peerix",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            'peerix = peerix.__main__:run'
        ]
    },
    version=version,
    requires=requirements
)

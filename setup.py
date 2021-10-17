#setup.py:

from distutils.core import setup
from Cython.Build import cythonize
from distutils.extension import Extension

ext_modules = [
    Extension(
        name="peerix._nix",
        sources=["peerix/_nix.pyx"],
        language="c++",
        extra_compile_args=["-std=c++17"],
   )
]

ext_modules = cythonize(ext_modules)

setup(
    name="peerix",
    ext_modules=ext_modules,
)

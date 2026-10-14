"""Run the verified pip wheel with the private Windows interpreter."""

import runpy
import sys

wheel, target, requirements = sys.argv[1:]
sys.path.insert(0, wheel)
sys.argv = [
    "pip",
    "install",
    "--disable-pip-version-check",
    "--only-binary=:all:",
    "--require-hashes",
    "--target",
    target,
    "--upgrade",
    "-r",
    requirements,
]
runpy.run_module("pip", run_name="__main__")

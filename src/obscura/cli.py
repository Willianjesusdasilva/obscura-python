"""Command-line entry point installed with the Python SDK."""

import subprocess
import sys
from ._process import ObscuraExecutableNotFound, ensure_executable


def main() -> int:
    try:
        executable = ensure_executable()
    except ObscuraExecutableNotFound as exc:
        print(str(exc), file=sys.stderr)
        return 127
    try:
        return subprocess.call([executable, *sys.argv[1:]])
    except OSError as exc:
        print(f"Could not execute Obscura: {exc}", file=sys.stderr)
        return 126

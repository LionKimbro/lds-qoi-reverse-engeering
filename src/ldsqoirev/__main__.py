"""Command-line entry point for read-only LDS inspection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .inspect import inspect_lds


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect LDS ZIP/CDOC/QOI structure without modifying files.")
    parser.add_argument("paths", nargs="+", type=Path, help="LDS file(s) to inspect")
    parser.add_argument("--indent", type=int, default=2, help="JSON indentation")
    args = parser.parse_args()
    for path in args.paths:
        print(json.dumps(inspect_lds(path), indent=args.indent))


if __name__ == "__main__":
    main()

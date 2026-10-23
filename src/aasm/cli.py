"""Command line entry point: one sub-command per module."""
from __future__ import annotations

import argparse
import sys

from aasm import __version__


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="aasm", description="AI Act standards map")
    p.add_argument("--version", action="store_true", help="print the version and exit")
    p.add_subparsers(dest="cmd")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.version:
        print(f"aasm {__version__}")
        return 0
    build_parser().print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())

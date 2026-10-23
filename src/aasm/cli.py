"""Command line entry point: one sub-command per module."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from aasm import __version__
from aasm.curated import check_tables

DEFAULT_CURATED = Path("data/curated")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="aasm", description="AI Act standards map")
    p.add_argument("--version", action="store_true", help="print the version and exit")
    sub = p.add_subparsers(dest="cmd")
    chk = sub.add_parser("check", help="validate the curated tables")
    chk.add_argument("--curated", type=Path, default=DEFAULT_CURATED)
    fe = sub.add_parser("fetch-eurostat", help="download adoption data with lineage")
    fe.add_argument("--out", type=Path, default=Path("data/fetched"))
    fe.add_argument("--from-file", type=Path, default=None, help="offline: a saved JSON-stat response")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(f"aasm {__version__}")
        return 0
    if args.cmd == "check":
        errors = check_tables(args.curated)
        for e in errors:
            print(e)
        print(f"{len(errors)} problem(s)" if errors else "curated tables OK")
        return 1 if errors else 0
    if args.cmd == "fetch-eurostat":
        from aasm.eurostat import fetch, fetch_from_file

        lineage = fetch_from_file(args.out, args.from_file) if args.from_file else fetch(args.out)
        print(f"{lineage['rows']} rows, sha256 {lineage['sha256'][:12]}")
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())

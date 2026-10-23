"""Command line entry point: one sub-command per module."""
from __future__ import annotations

import argparse
import sys
from datetime import date
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
    dv = sub.add_parser("derive", help="write the derived tables")
    dv.add_argument("--curated", type=Path, default=DEFAULT_CURATED)
    dv.add_argument("--out", type=Path, default=Path("data/derived"))
    dv.add_argument("--as-of", type=date.fromisoformat, default=None)
    ws = sub.add_parser("watch-standards", help="detect changes on the public pages of the work items")
    ws.add_argument("--curated", type=Path, default=DEFAULT_CURATED)
    ws.add_argument("--state", type=Path, default=Path("data/watch_state.json"))
    ws.add_argument("--history", type=Path, default=Path("data/derived/standards_history.csv"))
    ws.add_argument("--no-issues", action="store_true", help="print notifications instead of opening issues")
    rp = sub.add_parser("report", help="write docs/quality.md")
    rp.add_argument("--root", type=Path, default=Path("."))
    bd = sub.add_parser("build", help="render the static site into _site/")
    bd.add_argument("--root", type=Path, default=Path("."))
    bd.add_argument("--out", type=Path, default=Path("_site"))
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
    if args.cmd == "derive":
        from aasm.curated import load_all
        from aasm.derive import write_derived

        errors = check_tables(args.curated)
        if errors:
            print("\n".join(errors))
            return 1
        counts = write_derived(load_all(args.curated), args.as_of or date.today(), args.out)
        print(", ".join(f"{k}: {v} rows" for k, v in counts.items()))
        return 0
    if args.cmd == "watch-standards":
        from aasm import watch

        notify = (lambda item: print(f"[notify] {item[0]}")) if args.no_issues else watch._notify_with_gh
        res = watch.run(args.curated, args.state, args.history, date.today(), notify=notify)
        print(f"changed: {len(res.changed)}, failed: {len(res.failed)}, history rows added: {res.appended}")
        return 1 if res.failed else 0
    if args.cmd == "report":
        from aasm.report import write as write_report

        print(f"wrote {write_report(args.root, date.today())}")
        return 0
    if args.cmd == "build":
        from aasm.site import build

        print(f"site written to {build(args.root, args.out, date.today())}")
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())

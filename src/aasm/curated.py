"""Load and validate the hand-curated CSV tables."""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from aasm.schema import BOOLS, ENUMS, TABLES, Table

Rows = list[dict[str, str]]


def load_table(curated_dir: Path, name: str) -> Rows:
    path = curated_dir / f"{name}.csv"
    with path.open(encoding="utf-8", newline="") as fh:
        return [dict(r) for r in csv.DictReader(fh)]


def load_all(curated_dir: Path) -> dict[str, Rows]:
    return {name: load_table(curated_dir, name) for name in TABLES}


def check_tables(curated_dir: Path) -> list[str]:
    errors: list[str] = []
    loaded: dict[str, Rows] = {}
    for name, table in TABLES.items():
        rows = _check_one(curated_dir, table, errors)
        if rows is not None:
            loaded[name] = rows
    _check_refs(loaded, errors)
    return errors


def _check_one(curated_dir: Path, table: Table, errors: list[str]) -> Rows | None:
    fname = f"{table.name}.csv"
    path = curated_dir / fname
    if not path.exists():
        errors.append(f"{fname}: missing")
        return None
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        errors.append(f"{fname}: starts with a UTF-8 BOM; save as plain UTF-8")
        return None
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        header = tuple(reader.fieldnames or ())
        if header != table.columns:
            errors.append(f"{fname}: header is {list(header)}, expected {list(table.columns)}")
            return None
        rows = [dict(r) for r in reader]
    seen: set[str] = set()
    for i, row in enumerate(rows, start=2):
        key = row[table.key]
        if key in seen:
            errors.append(f"{fname}:{i}: duplicate {table.key} {key!r}")
        seen.add(key)
        if _is_ragged(row):
            errors.append(f"{fname}:{i}: wrong number of fields")
            continue
        for col in table.required:
            if not row[col].strip():
                errors.append(f"{fname}:{i}: {col} is empty")
        if not row["source_url"].startswith("https://"):
            errors.append(f"{fname}:{i}: source_url must start with https://")
        for col in table.dates:
            if row[col] and not _is_iso_date(row[col]):
                errors.append(f"{fname}:{i}: {col} {row[col]!r} is not YYYY-MM-DD")
        for col in table.bools:
            if row[col] not in BOOLS:
                errors.append(f"{fname}:{i}: {col} must be true or false, got {row[col]!r}")
        if table.name == "standards":
            if row["ojeu_cited"] == "true" and not row["ojeu_date"]:
                errors.append(f"{fname}:{i}: ojeu_cited is true but ojeu_date is empty")
            if row["ojeu_cited"] == "false" and row["ojeu_date"]:
                errors.append(f"{fname}:{i}: ojeu_date is set but ojeu_cited is false")
        for (tname, col), allowed in ENUMS.items():
            if tname == table.name and row[col] not in allowed:
                errors.append(f"{fname}:{i}: {col} {row[col]!r} not in {sorted(allowed)}")
    return [row for row in rows if not _is_ragged(row)]


def _check_refs(loaded: dict[str, Rows], errors: list[str]) -> None:
    for name, table in TABLES.items():
        rows = loaded.get(name)
        for col, other, other_key in table.refs:
            if rows is None or other not in loaded:
                continue
            keys = {r[other_key] for r in loaded[other]}
            for i, row in enumerate(rows, start=2):
                for ref in filter(None, (x.strip() for x in row[col].split("|"))):
                    if ref not in keys:
                        errors.append(f"{name}.csv:{i}: {col} {ref!r} not found in {other}.csv")


def _is_ragged(row: dict[str, str | None]) -> bool:
    # DictReader fills missing fields with None and stores extra fields under a None key
    return None in row or None in row.values()


def _is_iso_date(text: str) -> bool:
    try:
        date.fromisoformat(text)
    except ValueError:
        return False
    return len(text) == 10

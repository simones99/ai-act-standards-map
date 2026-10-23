"""Eurostat isoc_eb_ain2: share of enterprises (10+ employees) using AI, by NACE sector, country and year."""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import UTC, datetime
from itertools import product
from pathlib import Path
from urllib.parse import urlencode

import requests

TABLE = "isoc_eb_ain2"
API = f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{TABLE}"
INDICATOR = "E_AI_TANY"   # enterprises using at least one AI technology
UNIT = "PC_ENT"           # % of enterprises
SIZE = "GE10"             # 10 employees or more
GEOS = ["EU27_2020", "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES", "FI", "FR", "HR", "HU",
        "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK"]
ADOPTION_COLUMNS = ("nace_r2", "geo", "year", "value", "flag")


def build_url(geos: list[str]) -> str:
    params = [("format", "JSON"), ("lang", "EN"), ("size_emp", SIZE), ("indic_is", INDICATOR), ("unit", UNIT)]
    params += [("geo", g) for g in geos]
    return f"{API}?{urlencode(params)}"


def _at(seq, flat: int):
    """A value or status cell: JSON-stat writes them as a sparse dict or as a list."""
    if isinstance(seq, dict):
        return seq.get(str(flat))
    return seq[flat] if flat < len(seq) else None


def decode_jsonstat(js: dict) -> list[dict]:
    """JSON-stat 2.0 dataset -> rows {dimension: code, ..., value, flag}; keeps flagged empty cells."""
    ids, sizes = js["id"], js["size"]
    cats = []
    for dim in ids:
        index = js["dimension"][dim]["category"]["index"]
        if isinstance(index, list):
            ordered = index
        else:
            ordered = [c for c, _ in sorted(index.items(), key=lambda kv: kv[1])]
        cats.append(ordered)
    if [len(c) for c in cats] != sizes:
        raise ValueError("JSON-stat: inconsistent dimensions")
    values, status = js.get("value", {}), js.get("status", {})
    rows = []
    for flat, combo in enumerate(product(*cats)):
        v = _at(values, flat)
        f = (_at(status, flat) or "").replace("|", "").strip().lower()
        if v is not None or f:
            rows.append({**dict(zip(ids, combo, strict=True)), "value": v, "flag": f})
    return rows


def to_adoption_rows(js: dict, geos: list[str]) -> list[dict]:
    for dim, wanted in (("geo", geos), ("indic_is", [INDICATOR]), ("unit", [UNIT])):
        present = set(js["dimension"][dim]["category"]["index"])
        missing = sorted(set(wanted) - present)
        if missing:
            raise ValueError(f"{TABLE}: requested {dim} not in response: {', '.join(missing)}")
    out = []
    for r in decode_jsonstat(js):
        if r["indic_is"] != INDICATOR or r["unit"] != UNIT or r["geo"] not in geos:
            continue
        out.append({"nace_r2": r["nace_r2"], "geo": r["geo"], "year": r["time"],
                    "value": None if r["value"] is None else round(float(r["value"]), 1), "flag": r["flag"]})
    out.sort(key=lambda r: (r["nace_r2"], r["geo"], r["year"]))
    return out


def fetch(out_dir: Path, geos: list[str] = GEOS, get=requests.get) -> dict:
    url = build_url(geos)
    resp = get(url, timeout=60)
    resp.raise_for_status()
    raw: bytes = resp.content
    rows = to_adoption_rows(json.loads(raw), geos)
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "adoption.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=ADOPTION_COLUMNS, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({**r, "value": "" if r["value"] is None else r["value"]})
    lineage = {
        "table": TABLE,
        "url": url,
        "retrieved_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "rows": len(rows),
        "eurostat_updated": json.loads(raw).get("updated"),
        "licence": "Source: Eurostat",
    }
    (out_dir / "lineage.json").write_text(json.dumps(lineage, indent=2) + "\n", encoding="utf-8")
    return lineage


def fetch_from_file(out_dir: Path, path: Path, geos: list[str] | None = None) -> dict:
    """Offline mode for tests and CI: read a saved JSON-stat response instead of calling the API.

    Without `geos`, every geo in the saved file is kept (it may cover fewer countries than GEOS).
    """
    raw = path.read_bytes()
    if geos is None:
        geos = list(json.loads(raw)["dimension"]["geo"]["category"]["index"])

    class _Resp:
        status_code = 200
        content = raw

        def raise_for_status(self):
            pass

    return fetch(out_dir, geos, get=lambda url, timeout: _Resp())

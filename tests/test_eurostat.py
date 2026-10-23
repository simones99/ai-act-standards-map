import csv
import json
from pathlib import Path

import pytest

from aasm.eurostat import GEOS, build_url, decode_jsonstat, fetch, to_adoption_rows

FIX = Path(__file__).parent / "fixtures" / "isoc_eb_ain2.json"


def test_decode_returns_one_row_per_cell_with_value_or_flag():
    js = json.loads(FIX.read_text())
    rows = decode_jsonstat(js)
    assert rows, "no rows decoded"
    assert set(rows[0]) == {"freq", "size_emp", "nace_r2", "indic_is", "unit", "geo", "time", "value", "flag"}


def test_adoption_rows_keep_only_the_adoption_indicator_in_percent():
    js = json.loads(FIX.read_text())
    rows = to_adoption_rows(js, geos=["IT", "EU27_2020"])
    assert rows
    assert {r["geo"] for r in rows} <= {"IT", "EU27_2020"}
    assert all(set(r) == {"nace_r2", "geo", "year", "value", "flag"} for r in rows)
    assert all(r["value"] is None or 0 <= float(r["value"]) <= 100 for r in rows)


def test_missing_requested_geo_raises():
    js = json.loads(FIX.read_text())
    with pytest.raises(ValueError, match="geo"):
        to_adoption_rows(js, geos=["IT", "XX"])


def test_build_url_lists_every_geo_and_pins_the_indicator():
    url = build_url(["IT", "DE"])
    assert url.startswith("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/isoc_eb_ain2?")
    assert "geo=IT" in url and "geo=DE" in url
    assert "indic_is=E_AI_TANY" in url and "unit=PC_ENT" in url and "size_emp=GE10" in url


def test_fetch_writes_csv_and_lineage(tmp_path):
    raw = FIX.read_bytes()

    class Resp:
        status_code = 200
        content = raw

        def raise_for_status(self):
            pass

        def json(self):
            return json.loads(raw)

    lineage = fetch(tmp_path, geos=["IT", "EU27_2020"], get=lambda url, timeout: Resp())
    rows = list(csv.DictReader((tmp_path / "adoption.csv").open()))
    assert rows and rows[0].keys() == {"nace_r2", "geo", "year", "value", "flag"}
    saved = json.loads((tmp_path / "lineage.json").read_text())
    assert saved == lineage
    assert saved["table"] == "isoc_eb_ain2"
    assert saved["rows"] == len(rows)
    assert len(saved["sha256"]) == 64
    assert saved["retrieved_at"].endswith("Z")
    assert saved["url"] == build_url(["IT", "EU27_2020"])


def test_default_geos_include_italy_and_eu():
    assert "IT" in GEOS and "EU27_2020" in GEOS

"""Static site: one page with the coverage matrix and the timeline, plus the CSVs for download."""
from __future__ import annotations

import csv
import json
import shutil
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from aasm import __version__
from aasm.schema import TABLES

REPO_URL = "https://github.com/simones99/ai-act-standards-map"
TEMPLATES = Path(__file__).resolve().parents[2] / "site" / "templates"
STATUS_ORDER = ["uncovered", "in_progress", "published", "harmonised"]
STATUS_COLOURS = ["#9b1c1c", "#c98a00", "#1f4e79", "#1e6b3a"]


def _read_csv(path: Path) -> list[dict]:
    return list(csv.DictReader(path.open(encoding="utf-8", newline=""))) if path.exists() else []


def vega_specs(coverage: list[dict], timeline: list[dict]) -> dict[str, dict]:
    coverage_spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "Coverage status of each requirement",
        "data": {"values": coverage, "format": {"parse": {"article": "number"}}},
        "mark": "bar",
        "height": {"step": 26},
        "width": "container",
        "encoding": {
            "y": {"field": "title", "type": "nominal", "sort": {"field": "article"}, "title": None},
            "x": {"field": "n_work_items", "type": "quantitative", "title": "Work items reached"},
            "color": {"field": "status", "type": "nominal",
                      "scale": {"domain": STATUS_ORDER, "range": STATUS_COLOURS}, "title": "Status"},
            "tooltip": [{"field": "article", "title": "Article"}, {"field": "title"}, {"field": "status"},
                        {"field": "n_work_items", "title": "Work items"}],
        },
    }
    # One point per work item: colour against the earliest deadline; every deadline is still drawn as a rule.
    first = min(timeline, key=lambda r: r["deadline_date"])["deadline_id"] if timeline else ""
    timeline_spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "Target publication of each work item against the application dates",
        "data": {"values": timeline},
        "width": "container",
        "height": {"step": 26},
        "layer": [
            {"mark": {"type": "rule", "strokeDash": [4, 4], "color": "#9b1c1c"},
             "encoding": {"x": {"field": "deadline_date", "type": "temporal"}}},
            {"mark": {"type": "point", "filled": True, "size": 90},
             "transform": [{"filter": {"field": "deadline_id", "equal": first}}],
             "encoding": {
                 "x": {"field": "target_pub_date", "type": "temporal", "title": "Target publication"},
                 "y": {"field": "wi_ref", "type": "nominal", "title": None},
                 "color": {"field": "late_vs_deadline", "type": "nominal", "title": f"Late vs {first}",
                           "scale": {"domain": ["false", "true", "target_passed", "unknown"],
                                     "range": ["#1e6b3a", "#9b1c1c", "#c98a00", "#888888"]}},
                 "tooltip": [{"field": "wi_ref"}, {"field": "stage_name", "title": "Stage"},
                             {"field": "target_pub_date", "title": "Target"},
                             {"field": "deadline_id", "title": "Deadline"}],
             }},
        ],
    }
    return {"coverage": coverage_spec, "timeline": timeline_spec}


def build(root: Path, out_dir: Path, today: date) -> Path:
    data = root / "data"
    derived, curated, fetched = data / "derived", data / "curated", data / "fetched"
    coverage = _read_csv(derived / "coverage_by_requirement.csv")
    timeline = _read_csv(derived / "timeline.csv")
    deliverables = _read_csv(curated / "request_deliverables.csv")
    # A judged mapping must be visible where the status is shown, not only in the CSV
    coverage_notes = [{"article": r["article"], "deliverable_id": d["deliverable_id"], "note": d["note"]}
                      for r in coverage for d in deliverables
                      if d.get("note") and r["req_id"] in d.get("covers_req_ids", "").split("|")]
    lin_path = fetched / "lineage.json"
    lineage = json.loads(lin_path.read_text()) if lin_path.exists() else None

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "data").mkdir(exist_ok=True)
    curated_files = []
    for name in TABLES:
        src = curated / f"{name}.csv"
        if src.exists():
            shutil.copy(src, out_dir / "data" / src.name)
            curated_files.append(src.name)
    for src in list(derived.glob("*.csv")) + [fetched / "adoption.csv"]:
        if src.exists():
            shutil.copy(src, out_dir / "data" / src.name)
    quality = root / "docs" / "quality.md"
    if quality.exists():
        shutil.copy(quality, out_dir / "quality.md")
    (out_dir / ".nojekyll").write_text("")

    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=True)
    page = env.get_template("index.html.j2").render(
        today=today.isoformat(), version=__version__, coverage=coverage, coverage_notes=coverage_notes,
        timeline=timeline,
        curated_files=curated_files, lineage=lineage, repo_url=REPO_URL,
        specs=vega_specs(coverage, timeline),
    )
    (out_dir / "index.html").write_text(page, encoding="utf-8")
    return out_dir

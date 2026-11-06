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
STATIC = TEMPLATES.parent / "static"
ROW = 46  # px: one chart step and one row of the table beside the chart (--row in the template)
STATUS_ORDER = ["uncovered", "in_progress", "published", "harmonised"]
STATUS_COLOURS = ["#9b1c1c", "#8a5a00", "#1f4e79", "#1e6b3a"]  # each at least 4.5:1 on white, as text too
LATE_ORDER = ["false", "true", "target_passed", "unknown"]
LATE_COLOURS = ["#1e6b3a", "#9b1c1c", "#8a5a00", "#6b6b6b"]
LATE_LABELS = {"false": "target before the {first} deadline", "true": "target after the deadline",
               "target_passed": "target date passed, not published", "unknown": "no target date"}
INK, MUTED, LINE = "#1b1b1b", "#5b5b5b", "#e3e3e3"
CHART_CONFIG = {
    "font": "IBM Plex Sans, system-ui, sans-serif",
    "view": {"stroke": None},
    "axis": {"labelFontSize": 14, "titleFontSize": 13, "titleFontWeight": 500, "labelColor": INK,
             "titleColor": MUTED, "gridColor": LINE, "domainColor": LINE, "tickColor": LINE,
             "labelLimit": 220, "labelPadding": 8, "titlePadding": 8},
    "text": {"fontSize": 14},
}
# Nothing above the plot: row i of a chart then sits beside row i of its table
CHART_PADDING = {"left": 0, "top": 0, "right": 8, "bottom": 0}


def _read_csv(path: Path) -> list[dict]:
    return list(csv.DictReader(path.open(encoding="utf-8", newline=""))) if path.exists() else []


def timeline_by_item(timeline: list[dict]) -> tuple[list[dict], list[dict]]:
    """One row per work item, with its days to each deadline; deadlines earliest first."""
    seen = {r["deadline_id"]: r["deadline_date"] for r in timeline}
    deadlines = [{"deadline_id": k, "deadline_date": v}
                 for k, v in sorted(seen.items(), key=lambda kv: kv[1])]
    items: dict[str, dict] = {}
    for r in timeline:
        per_deadline = ("deadline_id", "deadline_date", "days_target_to_deadline", "late_vs_deadline")
        item = items.setdefault(r["wi_ref"], {**{k: v for k, v in r.items() if k not in per_deadline},
                                              "days": {}})
        item["days"][r["deadline_id"]] = {"days": r["days_target_to_deadline"],
                                          "late": r["late_vs_deadline"]}
    for item in items.values():
        item["days"] = {d["deadline_id"]: item["days"][d["deadline_id"]]
                        for d in deadlines if d["deadline_id"] in item["days"]}
    return deadlines, list(items.values())


def vega_specs(coverage: list[dict], timeline: list[dict], as_of: str | None = None) -> dict[str, dict]:
    coverage_spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "Coverage status of each requirement",
        "data": {"values": coverage, "format": {"parse": {"article": "number"}}},
        "transform": [{"calculate": "'Article ' + datum.article", "as": "article_label"},
                      {"calculate": "replace(datum.status, '_', ' ')", "as": "status_label"}],
        "height": {"step": ROW},
        "width": "container",
        "background": "transparent",
        "padding": CHART_PADDING,
        "config": CHART_CONFIG,
        "encoding": {
            "y": {"field": "article_label", "type": "nominal", "sort": {"field": "article"}, "title": None},
            "x": {"field": "n_work_items", "type": "quantitative", "title": "Work items reached",
                  "axis": {"tickMinStep": 1, "format": "d"}, "scale": {"nice": False, "padding": 0}},
            # the label on each bar names the status, so the chart needs no legend
            "color": {"field": "status", "type": "nominal", "legend": None,
                      "scale": {"domain": STATUS_ORDER, "range": STATUS_COLOURS}},
            "tooltip": [{"field": "article", "title": "Article"}, {"field": "title", "title": "Requirement"},
                        {"field": "status_label", "title": "Status"},
                        {"field": "n_work_items", "title": "Work items"}],
        },
        # The label carries the status colour where the bar has no length (no work item reached)
        "layer": [
            {"mark": {"type": "bar", "height": {"band": 0.68}}},
            {"mark": {"type": "text", "align": "left", "dx": 6, "fontWeight": 500},
             "encoding": {"text": {"field": "status_label", "type": "nominal"}}},
        ],
    }
    # One point per work item: colour against the earliest deadline; every deadline is still drawn as a rule.
    first = min(timeline, key=lambda r: r["deadline_date"])["deadline_id"] if timeline else ""
    # the key is written in the page, above chart and table: a legend here would push the rows down
    late = {"field": "late_vs_deadline", "type": "nominal", "title": f"Target vs {first} deadline",
            "legend": None}
    timeline_spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "Target publication of each work item against the application dates",
        "data": {"values": timeline},
        "width": "container",
        "height": {"step": ROW},
        "background": "transparent",
        "padding": CHART_PADDING,
        "config": CHART_CONFIG,
        "layer": [
            {"mark": {"type": "rule", "strokeDash": [4, 4], "color": INK},
             "encoding": {"x": {"field": "deadline_date", "type": "temporal"}}},
            {"mark": {"type": "point", "filled": True, "size": 230, "opacity": 1},
             "transform": [{"filter": {"field": "deadline_id", "equal": first}}],
             "encoding": {
                 "x": {"field": "target_pub_date", "type": "temporal", "title": "Target publication",
                       "axis": {"format": "%b %Y", "labelFlush": False}, "scale": {"padding": 16}},
                 # the grid line runs through each mark towards its row in the table
                 "y": {"field": "wi_ref", "type": "nominal", "title": None, "sort": None,
                       "axis": {"grid": True}},
                 "color": {**late, "scale": {"domain": LATE_ORDER, "range": LATE_COLOURS}},
                 # shape repeats the colour, so the reading does not depend on colour alone
                 "shape": {**late, "scale": {"domain": LATE_ORDER,
                                             "range": ["circle", "triangle-up", "diamond", "square"]}},
                 "tooltip": [{"field": "wi_ref", "title": "Work item"}, {"field": "title", "title": "Title"},
                             {"field": "stage_name", "title": "Stage"},
                             {"field": "target_pub_date", "title": "Target"},
                             {"field": "deadline_id", "title": "Deadline"}],
             }},
            # labels run down the rules, so they do not collide on a narrow screen
            {"mark": {"type": "text", "angle": 270, "align": "right", "baseline": "bottom", "dx": -4,
                      "dy": -4, "color": INK, "fontWeight": 500},
             "transform": [{"aggregate": [{"op": "count", "as": "n"}],
                            "groupby": ["deadline_id", "deadline_date"]}],
             "encoding": {"x": {"field": "deadline_date", "type": "temporal"}, "y": {"value": 0},
                          "text": {"field": "deadline_id", "type": "nominal"}}},
        ],
    }
    if as_of:
        today = {"values": [{"as_of": as_of}]}
        timeline_spec["layer"] += [
            {"data": today, "mark": {"type": "rule", "color": MUTED},
             "encoding": {"x": {"field": "as_of", "type": "temporal"}}},
            {"data": today,
             "mark": {"type": "text", "angle": 270, "align": "right", "baseline": "bottom", "dx": -4,
                      "dy": -4, "color": MUTED},
             "encoding": {"x": {"field": "as_of", "type": "temporal"}, "y": {"value": 0},
                          "text": {"value": f"as of {as_of}"}}},
        ]
    return {"coverage": coverage_spec, "timeline": timeline_spec}


def build(root: Path, out_dir: Path, today: date) -> Path:
    data = root / "data"
    derived, curated, fetched = data / "derived", data / "curated", data / "fetched"
    coverage = _read_csv(derived / "coverage_by_requirement.csv")
    timeline = _read_csv(derived / "timeline.csv")
    deadlines, items = timeline_by_item(timeline)
    scopes = {d["deadline_id"]: d["scope"] for d in _read_csv(curated / "deadlines.csv")}
    for d in deadlines:
        d["scope"] = scopes.get(d["deadline_id"], "")
    deliverables = _read_csv(curated / "request_deliverables.csv")
    # A judged mapping must be visible where the status is shown, not only in the CSV
    coverage_notes = [{"article": r["article"], "deliverable_id": d["deliverable_id"], "note": d["note"]}
                      for r in coverage for d in deliverables
                      if d.get("note") and r["req_id"] in d.get("covers_req_ids", "").split("|")]
    judged = {n["article"] for n in coverage_notes}
    counts = {status: sum(1 for r in coverage if r["status"] == status) for status in STATUS_ORDER}
    first = deadlines[0]["deadline_id"] if deadlines else ""
    seen = {r["late_vs_deadline"] for r in timeline}
    late_key = [{"late": k, "label": v.format(first=first)} for k, v in LATE_LABELS.items()
                if k != "unknown" or k in seen]
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
    other_files = []
    for src in list(derived.glob("*.csv")) + [fetched / "adoption.csv"]:
        if src.exists():
            shutil.copy(src, out_dir / "data" / src.name)
            other_files.append(src.name)
    quality = root / "docs" / "quality.md"
    if quality.exists():
        shutil.copy(quality, out_dir / "quality.md")
    if (STATIC / "fonts").exists():
        shutil.copytree(STATIC / "fonts", out_dir / "fonts", dirs_exist_ok=True)
    (out_dir / ".nojekyll").write_text("")

    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=True)
    page = env.get_template("index.html.j2").render(
        today=today.isoformat(), version=__version__, coverage=coverage, coverage_notes=coverage_notes,
        deadlines=deadlines, items=items, judged=judged, counts=counts, late_key=late_key, row=ROW,
        curated_files=curated_files, other_files=other_files, lineage=lineage, repo_url=REPO_URL,
        specs=vega_specs(coverage, timeline, today.isoformat()),
    )
    (out_dir / "index.html").write_text(page, encoding="utf-8")
    return out_dir

"""Static site: one page with the coverage matrix and the timeline, plus the CSVs for download."""
from __future__ import annotations

import csv
import json
import re
import shutil
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlencode

from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup, escape

from aasm import __version__
from aasm.derive import linked_by_judgement
from aasm.schema import TABLES

REPO_URL = "https://github.com/simones99/ai-act-standards-map"
TEMPLATES = Path(__file__).resolve().parents[2] / "site" / "templates"
STATIC = TEMPLATES.parent / "static"
ROW = 46  # px: one row of the plot and one row of the table beside it (--row in the template)
AUTHOR = "Mezzabotta, S."  # as in CITATION.cff
STATUS_ORDER = ["harmonised", "published", "in_progress", "uncovered"]
TRACK_ORDER = {status: i for i, status in enumerate(reversed(STATUS_ORDER))}  # how far along the track
STEPS = ("Drafting", "Enquiry", "Approval", "Published", "Cited in the Official Journal")
STEPS_SHORT = {"Cited in the Official Journal": "Cited in the OJ"}
# what each step holds, in the codes of the CEN-CENELEC work programme (see docs/methodology.md)
STEP_NOTES = ("stages 00–30", "stage 40, vote and comments", "stage 50, formal vote", "stage 60 or 90",
              "harmonised")
# Curated ids are for the tables; the page names each application date in words
DEADLINE_LABELS = {"HR_ANNEX3": "Annex III application date", "HR_ANNEX1": "Annex I application date"}
# A published standard is a fact, a target is a forecast: the plot tells them apart
MARK_ORDER = ["published", "false", "true", "target_passed"]
MARK_LABELS = {"published": "published", "false": "target before the {first}",
               "true": "target after the {first}", "target_passed": "target date passed, not published"}
STALE_AFTER = 8  # days: the update is weekly, so data older than a week and a day mean a run was missed
RULE_LINE = 20  # px: each rule of the plot is named on its own line, so the names never collide


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


def deadline_label(deadline_id: str) -> str:
    return DEADLINE_LABELS.get(deadline_id, deadline_id)


def step_of(standard: dict, as_of: str) -> int:
    """Index in STEPS of the furthest step a work item has reached at as_of."""
    if standard.get("ojeu_cited") == "true" and "" < standard.get("ojeu_date", "") <= as_of:
        return 4
    code = int(standard["stage_code"])
    return 3 if 60 <= code < 95 else 2 if 50 <= code < 60 else 1 if 40 <= code < 50 else 0


def stage_track(coverage: list[dict], deliverables: list[dict], standards: list[dict]) -> list[dict]:
    """Each coverage row with its work items laid out by step, and what in it rests on a judgement.

    Same perimeter as the coverage: a stage dated after as_of has not been reached. A row is judged when
    the link of a deliverable to it is (link_basis). A work item is judged as `aasm derive` counts it:
    when the link of its own deliverable is, or its own link to that deliverable. A work item under a
    sourced deliverable stays sourced beside a judged one. A note alone never makes a judgement.
    """
    rows = []
    for r in coverage:
        mine = [d for d in deliverables if r["req_id"] in d.get("covers_req_ids", "").split("|")]
        ids = {d["deliverable_id"] for d in mine}
        judged_ids = {d["deliverable_id"] for d in mine if d.get("link_basis") == "judged"}
        steps: list[list[dict]] = [[] for _ in STEPS]
        for s in standards:
            if s["deliverable_id"] in ids and s["stage_date"] <= r["as_of"]:
                steps[step_of(s, r["as_of"])].append(
                    {**s, "judged": linked_by_judgement(s, judged_ids)})
        rows.append({**r, "steps": steps, "judged": bool(judged_ids)})
    return rows


def requirement_when(row: dict, as_of: str, deadline: dict | None) -> dict | None:
    """When a requirement was or may be covered, on public sources alone: the date of its furthest step,
    or for a draft the earliest target and how it falls against the first application date."""
    sourced = [(i, s) for i, step in enumerate(row["steps"]) for s in step if not s["judged"]]
    if not sourced:
        return None
    top = max(i for i, _ in sourced)
    if top >= 3:
        field, word = ("ojeu_date", "cited") if top == 4 else ("stage_date", "published")
        first = min((s for i, s in sourced if i == top), key=lambda s: s[field])
        return {"short": f"{word} {first[field]}", "detail": "", "wi_ref": first["wi_ref"]}
    dated = sorted((s for _, s in sourced if s["target_pub_date"]), key=lambda s: s["target_pub_date"])
    if not dated:
        return {"short": "no target date", "detail": "", "wi_ref": None}
    first, detail, short = dated[0], "", f"target {dated[0]['target_pub_date']}"
    if first["target_pub_date"] < as_of:
        short, detail = f"{short}, passed", "not published"
    elif deadline:
        target = date.fromisoformat(first["target_pub_date"])
        days = (date.fromisoformat(deadline["deadline_date"]) - target).days
        side = "before" if days >= 0 else "after"
        detail = f"{abs(days)} days {side} the {deadline['label']}"
    return {"short": short, "detail": detail, "wi_ref": first["wi_ref"]}


def keep_dates(text: str) -> Markup:
    """Escape the text and keep each ISO date on one line: a date must never break at its hyphens."""
    wrapped = re.sub(r"(\d{4}-\d{2}-\d{2})", r'<span class="nowrap">\1</span>', str(escape(text)))
    return Markup(wrapped)  # the text is escaped first; only the span is added


def anchor(wi_ref: str) -> str:
    """The fragment of a work item's row in the timeline: its reference with every other sign a hyphen."""
    return "wi-" + re.sub(r"[^A-Za-z0-9]+", "-", wi_ref).strip("-")


def report_url(subject: str, source_url: str) -> str:
    """A new review issue in the repository, already naming the row and the source it rests on."""
    body = (f"Row: {subject}\nSource: {source_url or 'none'}\n\n"
            "What is wrong, and the public page that shows it:\n")
    return f"{REPO_URL}/issues/new?" + urlencode(
        {"labels": "needs-review", "title": f"Correction: {subject}", "body": body})


def watch_summary(state: dict, standards: list[dict]) -> dict | None:
    """How many work-item pages the weekly watch reached at its last run, and which it did not."""
    if not state:
        return None
    latest = max(v["checked_at"] for v in state.values())
    missing = [s["wi_ref"] for s in standards if state.get(s["wi_ref"], {}).get("checked_at", "") < latest]
    return {"n": len(standards), "latest": latest, "missing": missing}


def by_target_date(items: list[dict]) -> list[dict]:
    """Work items in the order of their target date; those without one last."""
    return sorted(items, key=lambda i: (not i["target_pub_date"], i["target_pub_date"]))


def timeline_plot(items: list[dict], deadlines: list[dict], as_of: str) -> dict:
    """Positions, in percent of the plot width, of the marks, the rules and the axis ticks."""
    first = deadlines[0]["deadline_id"] if deadlines else ""
    dated = ([i["target_pub_date"] for i in items if i["target_pub_date"]]
             + [d["deadline_date"] for d in deadlines] + [as_of])
    lo, hi = date.fromisoformat(min(dated)), date.fromisoformat(max(dated))
    span = max((hi - lo).days, 1)

    def x(day: date) -> float:
        return round(3 + 94 * (day - lo).days / span, 2)  # 3% of air on each side

    marks = []
    for i in items:
        if 60 <= int(i["stage_code"]) < 95:
            state = "published"
        elif not i["target_pub_date"]:
            state = "unknown"
        else:
            state = i["days"].get(first, {}).get("late", "false")
        marks.append({"x": x(date.fromisoformat(i["target_pub_date"])) if i["target_pub_date"] else None,
                      "state": state})
    rules = [{"kind": "deadline", "date": d["deadline_date"], "label": deadline_label(d["deadline_id"])}
             for d in deadlines] + [{"kind": "as_of", "date": as_of, "label": "as of"}]
    for r in rules:
        r["x"] = x(date.fromisoformat(r["date"]))
        r["side"] = "left" if r["x"] > 50 else "right"  # the name sits on the side with room
    # a tick each quarter; April and October are minor, a phone names only January and July
    ticks = [{"x": x(day), "label": day.strftime("%b %Y"), "minor": month in (4, 10)}
             for year in range(lo.year, hi.year + 1) for month in (1, 4, 7, 10)
             if lo < (day := date(year, month, 1)) < hi]
    return {"marks": marks, "rules": rules, "ticks": ticks, "head": RULE_LINE * len(rules) + 8}


def build(root: Path, out_dir: Path, today: date) -> Path:
    data = root / "data"
    derived, curated, fetched = data / "derived", data / "curated", data / "fetched"
    coverage = _read_csv(derived / "coverage_by_requirement.csv")
    timeline = _read_csv(derived / "timeline.csv")
    standards = _read_csv(curated / "standards.csv")
    deliverables = _read_csv(curated / "request_deliverables.csv")
    requirements = _read_csv(curated / "requirements.csv")
    data_as_of = coverage[0]["as_of"] if coverage else today.isoformat()
    # the oldest check says how fresh the page is; the latest alone would overstate it
    days = sorted({s["retrieved_at"] for s in standards if s["retrieved_at"]})
    checked = "" if not days else days[0] if len(days) == 1 else f"{days[0]} to {days[-1]}"

    deadlines, items = timeline_by_item(timeline)
    curated_deadlines = {d["deadline_id"]: d for d in _read_csv(curated / "deadlines.csv")}
    for d in deadlines:
        row = curated_deadlines.get(d["deadline_id"], {})
        d.update(scope=row.get("scope", ""), source_url=row.get("source_url", ""),
                 note=row.get("note", ""), label=deadline_label(d["deadline_id"]))
    # every row leads to its public source and names the articles it serves, in the words of the track
    by_ref = {s["wi_ref"]: s for s in standards}
    article_of = {r["req_id"]: r["article"] for r in requirements}
    covers = {d["deliverable_id"]: [x for x in d.get("covers_req_ids", "").split("|") if x]
              for d in deliverables}
    basis = {d["deliverable_id"]: d.get("link_basis", "") for d in deliverables}
    items = by_target_date(items)
    for item in items:
        standard = by_ref.get(item["wi_ref"])
        item["source_url"] = standard["source_url"] if standard else ""
        item["step"] = STEPS[step_of(standard, data_as_of)] if standard else item["stage_name"]
        item["step_short"] = STEPS_SHORT.get(item["step"], item["step"])  # the side table never wraps
        reqs = covers.get(item["deliverable_id"])
        item["in_perimeter"] = reqs is None or bool(reqs)
        item["articles"] = sorted((article_of[r] for r in reqs or [] if r in article_of), key=int)
        # the same rule as the track: judged through its deliverable's link, or through its own
        # a passed target still says how late it is; a published one says it is no longer a forecast
        target = date.fromisoformat(item["target_pub_date"]) if item["target_pub_date"] else None
        for c in item["days"].values():
            passed = target and c["late"] == "target_passed"
            c["ago"] = (date.fromisoformat(data_as_of) - target).days if passed else None
            c["published"] = 60 <= int(item["stage_code"]) < 95
        item["anchor"] = anchor(item["wi_ref"])
        item["judged"] = (basis.get(item["deliverable_id"]) == "judged" and bool(reqs)
                          or bool(standard) and standard.get("link_basis") == "judged")
    plot = timeline_plot(items, deadlines, data_as_of)
    drawn = {m["state"] for m in plot["marks"]}
    first = deadlines[0]["label"] if deadlines else "application date"
    late_key = [{"state": k, "label": MARK_LABELS[k].format(first=first)} for k in MARK_ORDER if k in drawn]
    judged_items = any(i["judged"] for i in items)

    sources = {r["req_id"]: r["source_url"] for r in requirements}
    track = stage_track(coverage, deliverables, standards)
    timeline_refs = {i["wi_ref"] for i in items}
    for item in items:
        item["report"] = report_url(item["wi_ref"], item["source_url"])
    # a step reached since the week before as_of: what the last weekly update moved
    week_start = (date.fromisoformat(data_as_of) - timedelta(days=7)).isoformat()
    for r in track:
        r["source_url"] = sources.get(r["req_id"], "")
        r["report"] = report_url(f"Article {r['article']}", r["source_url"])
        for step in r["steps"]:
            for i in step:
                i["new"] = week_start < i["stage_date"] <= data_as_of
        r["new"] = any(i["new"] for step in r["steps"] for i in step)
        # the page leads with what public sources support; a judgement is said beside it, never in its place
        # both statuses come from the coverage file, where `aasm derive` applies the rule once
        r["shown"], r["with_judged"] = r["status"], r["status_with_judged"]
        # where a judgement would change the status, neither status wears a colour: the cell is neutral
        r["tone"] = "neutral" if r["with_judged"] != r["shown"] else r["shown"]
        r["when"] = requirement_when(r, data_as_of, deadlines[0] if deadlines else None)
        if r["when"] and r["when"]["wi_ref"] in timeline_refs:  # the date leads to its row in the timeline
            r["when"]["anchor"] = anchor(r["when"]["wi_ref"])
        judged_here = any(i["judged"] for step in r["steps"] for i in step)  # a judged work item is drawn
        said = r["with_judged"].replace("_", " ")
        r["judge"] = (f"{said} by a judged link" if r["with_judged"] != r["shown"]
                      else f"{said} also by a judged link" if judged_here
                      else "a judged link, no work item yet" if r["judged"] else "")
        # a status that rests on a judgement names the standard it rests on, and its date
        counted = {"steps": [[{**i, "judged": False} for i in step] for step in r["steps"]]}
        w = requirement_when(counted, data_as_of, None) if r["with_judged"] != r["shown"] else None
        r["judge_when"] = f"{w['wi_ref']}, {w['short']}" if w and w["wi_ref"] else ""
    # A judgement must be explained where it is drawn, not only in the CSV: first the requirements
    # reached through a judged deliverable, then the work items whose own link is judged
    titles = {d["deliverable_id"]: d["title"] for d in deliverables}
    coverage_notes = [{"subject": f"Article {r['article']}, through deliverable {d['deliverable_id']} "
                                  f"({d['title']}).", "note": d["note"]}
                      for r in coverage for d in deliverables
                      if d.get("link_basis") == "judged"
                      and r["req_id"] in d.get("covers_req_ids", "").split("|")]
    drawn_items = {i["wi_ref"] for r in track for step in r["steps"] for i in step}
    coverage_notes += [{"subject": f"{s['wi_ref']}, under deliverable {s['deliverable_id']} "
                                   f"({titles.get(s['deliverable_id'], '')}).", "note": s["note"]}
                       for s in standards if s.get("link_basis") == "judged" and s["wi_ref"] in drawn_items]
    judged_marks = any(i["judged"] for r in track for step in r["steps"] for i in step)
    counts = [{"status": status, "n": sum(1 for r in track if r["shown"] == status)}
              for status in STATUS_ORDER]
    judged_rows = [r for r in track if r["with_judged"] != r["shown"]]
    state_path = data / "watch_state.json"
    watch = watch_summary(json.loads(state_path.read_text()) if state_path.exists() else {}, standards)
    days_old = (today - date.fromisoformat(data_as_of)).days
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
    env.filters["dates"] = keep_dates
    page = env.get_template("index.html.j2").render(
        today=today.isoformat(), year=today.year, author=AUTHOR, version=__version__,
        data_as_of=data_as_of, checked=checked, track=track, steps=list(zip(STEPS, STEP_NOTES, strict=True)),
        coverage_notes=coverage_notes, judged_rows=judged_rows,
        judged_marks=judged_marks, counts=counts, deadlines=deadlines, items=items, plot=plot,
        late_key=late_key, judged_items=judged_items, row=ROW, track_order=TRACK_ORDER,
        watch=watch, days_old=days_old,
        stale=days_old > STALE_AFTER, stale_after=STALE_AFTER, report_page=report_url("the page", ""),
        curated_files=curated_files, other_files=other_files, lineage=lineage, repo_url=REPO_URL,
    )
    (out_dir / "index.html").write_text(page, encoding="utf-8")
    return out_dir

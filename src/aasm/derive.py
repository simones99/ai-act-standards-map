"""Derived tables: coverage of each requirement at a date, and work items against deadlines."""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from aasm.curated import Rows
from aasm.schema import STAGE_NAMES

COVERAGE_COLUMNS = ("req_id", "article", "title", "as_of", "n_deliverables", "n_work_items",
                    "n_at_enquiry_or_later", "n_published", "n_harmonised", "n_judged", "status",
                    "status_with_judged")
TIMELINE_COLUMNS = ("wi_ref", "title", "deliverable_id", "stage_code", "stage_name", "stage_date",
                    "target_pub_date", "deadline_id", "deadline_date", "days_target_to_deadline",
                    "late_vs_deadline")


def _d(text: str) -> date | None:
    return date.fromisoformat(text) if text else None


def _split(text: str) -> list[str]:
    return [x.strip() for x in text.split("|") if x.strip()]


def linked_by_judgement(standard: dict, judged_deliverables: set[str]) -> bool:
    """A work item is linked by judgement when the link of its deliverable to the requirement is, or its
    own link to that deliverable. The site marks the same work items."""
    return standard["deliverable_id"] in judged_deliverables or standard.get("link_basis") == "judged"


def _n_published(items: list[dict]) -> int:
    return sum(1 for s in items if 60 <= int(s["stage_code"]) < 95)


def _n_harmonised(items: list[dict], as_of: date) -> int:
    return sum(1 for s in items
               if s["ojeu_cited"] == "true" and (_d(s["ojeu_date"]) or date.max) <= as_of)


def _status(items: list[dict], as_of: date) -> str:
    """The status rule on a set of work items: the furthest any of them has reached at as_of."""
    if _n_harmonised(items, as_of):
        return "harmonised"
    if _n_published(items):
        return "published"
    return "in_progress" if items else "uncovered"


def coverage_by_requirement(tables: dict[str, Rows], as_of: date) -> list[dict]:
    deliverables_by_req: dict[str, list[str]] = {r["req_id"]: [] for r in tables["requirements"]}
    for d in tables["request_deliverables"]:
        for req in _split(d["covers_req_ids"]):
            deliverables_by_req.setdefault(req, []).append(d["deliverable_id"])
    judged_dlv = {d["deliverable_id"] for d in tables["request_deliverables"]
                  if d.get("link_basis") == "judged"}
    reached = [s for s in tables["standards"] if (_d(s["stage_date"]) or date.max) <= as_of]
    out = []
    for r in tables["requirements"]:
        dlv = set(deliverables_by_req.get(r["req_id"], []))
        items = [s for s in reached if s["deliverable_id"] in dlv]
        n_enq = sum(1 for s in items if 40 <= int(s["stage_code"]) < 95)
        judged = [s for s in items if linked_by_judgement(s, judged_dlv)]
        sourced = [s for s in items if s not in judged]
        out.append({"req_id": r["req_id"], "article": r["article"], "title": r["title"],
                    "as_of": as_of.isoformat(), "n_deliverables": len(dlv),
                    "n_work_items": len(items), "n_at_enquiry_or_later": n_enq,
                    "n_published": _n_published(items), "n_harmonised": _n_harmonised(items, as_of),
                    "n_judged": len(judged), "status": _status(sourced, as_of),
                    "status_with_judged": _status(items, as_of)})
    return out


def timeline(tables: dict[str, Rows], as_of: date) -> list[dict]:
    out = []
    for s in tables["standards"]:
        if (_d(s["stage_date"]) or date.max) > as_of:  # stage not reached yet, as in the coverage
            continue
        target = _d(s["target_pub_date"])
        for dl in tables["deadlines"]:
            dl_date = date.fromisoformat(dl["date"])
            if target is None or s["stage_code"] == "95":  # no target, or withdrawn
                days, late = "", "unknown"
            elif target < as_of and int(s["stage_code"]) < 60:
                days, late = "", "target_passed"  # the forecast date went by without publication
            else:
                days = (dl_date - target).days
                late = "true" if days < 0 else "false"
            out.append({"wi_ref": s["wi_ref"], "title": s["title"], "deliverable_id": s["deliverable_id"],
                        "stage_code": s["stage_code"], "stage_name": STAGE_NAMES.get(s["stage_code"], ""),
                        "stage_date": s["stage_date"], "target_pub_date": s["target_pub_date"],
                        "deadline_id": dl["deadline_id"], "deadline_date": dl["date"],
                        "days_target_to_deadline": days, "late_vs_deadline": late})
    return out


def write_csv(path: Path, rows: list[dict], columns: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columns, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def write_derived(tables: dict[str, Rows], as_of: date, out_dir: Path) -> dict[str, int]:
    cov = coverage_by_requirement(tables, as_of)
    tl = timeline(tables, as_of)
    write_csv(out_dir / "coverage_by_requirement.csv", cov, COVERAGE_COLUMNS)
    write_csv(out_dir / "timeline.csv", tl, TIMELINE_COLUMNS)
    return {"coverage_by_requirement": len(cov), "timeline": len(tl)}

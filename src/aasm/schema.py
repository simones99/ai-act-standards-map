"""Column definitions for every table. The only place where column names live."""
from __future__ import annotations

from dataclasses import dataclass

STAGE_CODES = frozenset({"00", "10", "20", "30", "40", "50", "60", "90", "95"})
STAGE_NAMES = {
    "00": "preliminary", "10": "proposal", "20": "preparatory", "30": "committee",
    "40": "enquiry", "50": "approval", "60": "publication", "90": "review", "95": "withdrawal",
}
CONFIDENCE = frozenset({"high", "medium", "low"})
BOOLS = frozenset({"true", "false"})
# how a row is tied to what it points to (a work item to its deliverable, a deliverable to the
# requirements it covers): by a public source, or by this project's judgement
LINK_BASIS = frozenset({"sourced", "judged"})


@dataclass(frozen=True)
class Table:
    name: str
    columns: tuple[str, ...]
    key: str
    required: tuple[str, ...]
    dates: tuple[str, ...] = ()
    bools: tuple[str, ...] = ()
    # column -> (other table, other key); "|" separated lists allowed
    refs: tuple[tuple[str, str, str], ...] = ()


TABLES: dict[str, Table] = {
    "requirements": Table(
        "requirements",
        ("req_id", "article", "paragraph", "title", "summary", "source_url"),
        "req_id",
        ("req_id", "article", "title", "summary", "source_url"),
    ),
    "annex3_areas": Table(
        "annex3_areas",
        ("area_id", "name", "points", "source_url"),
        "area_id",
        ("area_id", "name", "points", "source_url"),
    ),
    "request_deliverables": Table(
        "request_deliverables",
        ("deliverable_id", "title", "request_ref", "due_date", "covers_req_ids", "source_url", "link_basis",
         "note"),
        "deliverable_id",
        ("deliverable_id", "title", "request_ref", "source_url", "link_basis"),
        dates=("due_date",),
        refs=(("covers_req_ids", "requirements", "req_id"),),
    ),
    "standards": Table(
        "standards",
        ("wi_ref", "title", "deliverable_id", "stage_code", "stage_date", "target_pub_date",
         "ojeu_cited", "ojeu_date", "source_url", "retrieved_at", "link_basis", "note"),
        "wi_ref",
        ("wi_ref", "title", "deliverable_id", "stage_code", "stage_date", "ojeu_cited", "source_url",
         "retrieved_at", "link_basis"),
        dates=("stage_date", "target_pub_date", "ojeu_date", "retrieved_at"),
        bools=("ojeu_cited",),
        refs=(("deliverable_id", "request_deliverables", "deliverable_id"),),
    ),
    "deadlines": Table(
        "deadlines",
        ("deadline_id", "date", "scope", "source_url", "note"),
        "deadline_id",
        ("deadline_id", "date", "scope", "source_url"),
        dates=("date",),
    ),
}

ENUMS: dict[tuple[str, str], frozenset[str]] = {
    ("standards", "stage_code"): STAGE_CODES,
    ("standards", "link_basis"): LINK_BASIS,
    ("request_deliverables", "link_basis"): LINK_BASIS,
}

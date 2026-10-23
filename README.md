# ai-act-standards-map

Which high-risk requirements of the EU AI Act are covered by harmonised standards, when, and which sectors of the economy are most exposed to the gap. A curated, documented dataset with weekly checks and a one-page site.

**Perimeter.** High-risk AI systems (Article 6 and Annex III) and the requirements of Articles 8–15 of Regulation (EU) 2024/1689, against the deliverables of standardisation request M/593 (Commission Implementing Decision C(2023) 3215) and the CEN-CENELEC JTC 21 work items that answer them. Out of scope in v0.1: general-purpose AI models, prohibited practices, Annex I products. Sector exposure (Eurostat adoption data against Annex III areas) is fetched now and analysed in v0.2.

## Two rules

1. **The project describes, it does not interpret.** Every normative statement carries the article and, where it exists, the paragraph. Where a link between a requirement and a standard is a judgement, the row says so in its `note` column.
2. **Only public sources.** If a fact is not on a public page with a URL, it is not in the dataset. The author works at a national standardisation body; nothing seen in drafts or meetings enters this repository.

## What is in the box

| Folder | Content |
|---|---|
| `data/curated/` | Requirements, Annex III areas, M/593 deliverables, JTC 21 work items with stage and dates, application deadlines. Hand-written, every row with a source URL. |
| `data/fetched/` | Share of enterprises using AI by NACE sector and country (Eurostat `isoc_eb_ain2`), with `lineage.json`. |
| `data/derived/` | Coverage status per requirement at a date, work items against deadlines, history of stage changes. |
| `docs/` | `methodology.md`, `results.md` (dated statements), `quality.md` (generated). |
| `site/` | Template of the one-page site. |

## How it runs

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e . -r requirements-dev.txt
aasm check                 # validate the curated tables
aasm fetch-eurostat        # adoption data with lineage (or --from-file for offline)
aasm watch-standards --no-issues  # fingerprint the public pages (CI opens review issues)
aasm derive                # coverage_by_requirement.csv, timeline.csv
aasm report                # docs/quality.md
aasm build                 # _site/index.html
pytest -q && ruff check .
```

Every Monday the `weekly` workflow runs the same steps, commits new data and publishes the site. A changed or unreachable page opens an issue labelled `needs-review`; the curated table is updated by a person, never by the script.

## Status rule

For a requirement at date `as_of`, consider the deliverables that cover it and the work items linked to them whose `stage_date` is on or before `as_of`: `harmonised` if any is cited in the Official Journal by `as_of`; else `published` if any has reached stage 60; else `in_progress` if any work item exists; else `uncovered`. Details in [docs/methodology.md](docs/methodology.md).

## Licences

Code: [MIT](LICENSE). Data: [CC BY 4.0](data/LICENSE). Eurostat data: Source: Eurostat. Standards metadata are facts taken from public CEN-CENELEC and UNI catalogue pages; no standard text is reproduced. Personal project; it does not represent any employer.

# Data

Three folders, three rules.

- `curated/`: written by hand from public sources, every row with a `source_url`. Validated by `aasm check`.
- `fetched/`: downloaded by `aasm fetch-eurostat`, with `lineage.json` (URL, time, SHA-256, rows). Never edited.
- `derived/`: produced by `aasm derive` and `aasm watch-standards`. Never edited.

| Table | One row is | Key |
|---|---|---|
| `curated/requirements.csv` | A requirement of Regulation (EU) 2024/1689, Articles 8–15 | `req_id` |
| `curated/annex3_areas.csv` | An area of Annex III | `area_id` |
| `curated/request_deliverables.csv` | A deliverable of standardisation request M/593, with the requirements it covers (`covers_req_ids`, `\|`-separated) | `deliverable_id` |
| `curated/standards.csv` | A CEN-CENELEC JTC 21 work item answering a deliverable: stage code (10 proposal … 40 enquiry, 50 approval, 60 publication), dates, OJEU citation | `wi_ref` |
| `curated/deadlines.csv` | An application date of the Regulation | `deadline_id` |
| `fetched/adoption.csv` | Share of enterprises using AI, by NACE sector, country and year (Eurostat `isoc_eb_ain2`) | sector, geo, year |
| `derived/standards_history.csv` | A stage observed for a work item on a date (append-only) | `wi_ref`, `observed_at` |
| `derived/coverage_by_requirement.csv` | Coverage status of a requirement at the `as_of` date | `req_id` |
| `derived/timeline.csv` | A work item against each deadline | `wi_ref`, `deadline_id` |

Licence: CC BY 4.0 (see `LICENSE`). Eurostat data: Source: Eurostat.

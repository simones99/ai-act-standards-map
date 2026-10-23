# Methodology

## Sources

| Source | Used for | How |
|---|---|---|
| Regulation (EU) 2024/1689, EUR-Lex | Requirements of Articles 8–15, Annex III areas, application dates (Article 113) | Hand-curated; article and paragraph on every row |
| Commission Implementing Decision C(2023) 3215, standardisation request M/593 (eNorm) | The ten deliverables and the requirements they answer | Hand-curated |
| CEN-CENELEC JTC 21 work programme; UNI public catalogue | Work items: reference, title, stage code, dates | Hand-curated from public pages; pages fingerprinted weekly |
| Official Journal of the EU, C series | Harmonised standards cited under the AI Act | Hand-curated when a citation appears |
| Eurostat `isoc_eb_ain2` | Share of enterprises (10+ employees) using at least one AI technology, by NACE sector, country, year | API with lineage (URL, time, SHA-256, rows) |

## Stage codes

CEN-CENELEC harmonised stage codes: 00 preliminary, 10 proposal, 20 preparatory, 30 committee, 40 enquiry, 50 approval, 60 publication, 90 review, 95 withdrawal. Only the first two digits are kept.

## Coverage status

For each requirement `req_id` at a date `as_of`:

1. Take the deliverables whose `covers_req_ids` includes `req_id`.
2. Take the work items whose `deliverable_id` is one of those and whose `stage_date` is on or before `as_of`. A stage dated after `as_of` has not been reached and is ignored.
3. Status is `harmonised` if any work item has `ojeu_cited = true` with `ojeu_date` on or before `as_of`; else `published` if any has `stage_code >= 60`; else `in_progress` if any work item exists; else `uncovered`.

A requirement with no deliverable (Article 8, the umbrella clause; Article 11 if the request does not cover it) is `uncovered` with `n_deliverables = 0`, which the site shows as such.

## Timeline

For each work item and each application date in `deadlines.csv`: `days_target_to_deadline = deadline_date - target_pub_date`; negative means the target publication falls after the deadline (`late_vs_deadline = true`). No target date gives `unknown`.

## Weekly watch

`watch-standards` fetches the public page behind each work item, strips scripts, styles and tags, normalises whitespace and hashes the visible text. A different hash opens a GitHub issue; a person reads the page and updates `standards.csv`. The script never edits curated data. `standards_history.csv` records each stage change with the date it was observed.

## Limits

- Stage dates are the dates shown on public pages, which may lag the committee's decisions.
- The link between a work item and a deliverable is sometimes a judgement; such rows carry a `note`.
- Application dates are those of the adopted Regulation. Proposals to amend them are recorded in `note` until adopted.

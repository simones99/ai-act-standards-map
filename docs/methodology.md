# Methodology

## Sources

| Source | Used for | How |
|---|---|---|
| Regulation (EU) 2024/1689, EUR-Lex, as amended by Regulation (EU) 2026/1744 (Digital Omnibus on AI) | Requirements of Articles 8–15, Annex III areas, application dates (Article 113) | Hand-curated; article and paragraph on every row |
| Commission Implementing Decision C(2025) 3871, standardisation request M/593 (Commission documents register) | The ten deliverables, their due date and the requirements they answer | Hand-curated. C(2025) 3871 repealed and replaced C(2023) 3215 with the same deliverables and a new due date (31 August 2025 instead of 30 April 2025) |
| CEN-CENELEC JTC 21 work programme; UNI public catalogue | Work items: reference, title, stage code, dates | Hand-curated from public pages; pages fingerprinted weekly |
| Official Journal of the EU, C series | Harmonised standards cited under the AI Act | Hand-curated when a citation appears |
| Eurostat `isoc_eb_ain2` | Share of enterprises (10+ employees) using at least one AI technology, by NACE sector, country, year | API with lineage (URL, time, SHA-256, rows) |

## Stage codes

CEN-CENELEC harmonised stage codes: 00 preliminary, 10 proposal, 20 preparatory, 30 committee, 40 enquiry, 50 approval, 60 publication, 90 review, 95 withdrawal. Only the first two digits are kept.

## Coverage status

For each requirement `req_id` at a date `as_of`:

1. Take the deliverables whose `covers_req_ids` includes `req_id`.
2. Take the work items whose `deliverable_id` is one of those and whose `stage_date` is on or before `as_of`. A stage dated after `as_of` has not been reached and is ignored.
3. Status is `harmonised` if any work item has `ojeu_cited = true` with `ojeu_date` on or before `as_of`; else `published` if any has `stage_code` 60 or 90 (95, withdrawal, does not count); else `in_progress` if any work item exists; else `uncovered`.

A requirement with no deliverable (Article 8, the umbrella clause) is `uncovered` with `n_deliverables = 0`, which the site shows as such.

Article 11 (technical documentation) has no deliverable of its own. Annex II of C(2025) 3871 asks CEN and Cenelec to cover it in other harmonised standards, particularly the one on the quality management system, so `request_deliverables.csv` maps Article 11 to D09. The status of Article 11 therefore follows the quality management work items. When it reads `harmonised`, it means that the standard the request names as the main carrier of Article 11 is cited in the Official Journal; how far that standard covers Article 11 is stated in its Annex ZA, which is not public.

## Timeline

For each work item and each application date in `deadlines.csv`: `days_target_to_deadline = deadline_date - target_pub_date`; negative means the target publication falls after the deadline (`late_vs_deadline = true`). No target date gives `unknown`.

## Work items

`standards.csv` lists the JTC 21 work items whose public page names mandate M/613 (the CEN-CENELEC reference for C(2025) 3871) and says that an OJEU citation is expected under Regulation (EU) 2024/1689. Work items under the same mandate with no citation expected (supporting standards and technical reports) are left out. Where the link to a deliverable is a judgement, the row says so in `note`.

The JTC 21 work programme shows a status, not a stage code. The status is recorded as: Preliminary 00, Under Drafting 20, Under Enquiry 40, Under Approval 50, Published 60. `stage_date` is the date of the current stage on the work programme. `target_pub_date` is the forecasted voting date on the work programme (availability usually follows by a few weeks); for a published standard it is the date of availability (DAV).

Work item pages carry a checksum (`cs=`) in their URL. Without it the site answers 200 with an error page, so `watch-standards` treats a page that does not name its work item as failed.

## Weekly watch

`watch-standards` fetches the public page behind each work item, strips scripts, styles and tags, normalises whitespace and hashes the visible text. A different hash opens a GitHub issue; a person reads the page and updates `standards.csv`. The script never edits curated data. `standards_history.csv` records each stage change with the date it was observed.

## Limits

- Stage dates are the dates shown on public pages, which may lag the committee's decisions.
- The link between a work item and a deliverable is sometimes a judgement; such rows carry a `note`.
- Application dates are those in force: Regulation (EU) 2024/1689 as amended by Regulation (EU) 2026/1744, which moved the Annex III date from 2 August 2026 to 2 December 2027 and the Annex I date from 2 August 2027 to 2 August 2028. Superseded dates stay in `note`. Proposals to amend them are recorded in `note` until adopted.

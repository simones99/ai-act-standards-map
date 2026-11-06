# Results

Dated statements read from the tables in this repository. Each one holds at its date only; the weekly run updates the tables, not this page.

## As of 2026-11-06

Sources: `data/derived/coverage_by_requirement.csv` and `data/derived/timeline.csv` (`aasm derive`, as of 2026-11-06), built from `data/curated/standards.csv` (CEN-CENELEC JTC 21 work programme, retrieved 2026-11-06, and work item pages, retrieved 2026-10-23, four of them again on 2026-11-06; OJ citations from the Official Journal, L series), `request_deliverables.csv` (C(2025) 3871) and `deadlines.csv` (Regulation (EU) 2026/1744).

### Coverage by requirement

| Article | Requirement | Deliverables | Work items | At enquiry or later | Cited in OJEU | Status |
|---|---|---|---|---|---|---|
| 8 | Compliance with the requirements | 0 | 0 | 0 | 0 | uncovered |
| 9 | Risk management system | 1 | 1 | 1 | 0 | in_progress |
| 10 | Data and data governance | 1 | 2 | 1 | 0 | in_progress |
| 11 | Technical documentation | 1 | 1 | 1 | 1 | harmonised |
| 12 | Record-keeping | 1 | 1 | 1 | 0 | in_progress |
| 13 | Transparency and provision of information to deployers | 1 | 1 | 1 | 0 | in_progress |
| 14 | Human oversight | 1 | 1 | 1 | 0 | in_progress |
| 15 | Accuracy, robustness and cybersecurity | 3 | 3 | 1 | 0 | in_progress |

Status codes (see `docs/methodology.md`): `harmonised`: a linked standard is cited in the Official Journal; `published`: a linked standard is published (stage 60 or 90) but not cited; `in_progress`: at least one linked work item, none published; `uncovered`: no linked work item.

Article 11 has no deliverable of its own in C(2025) 3871; the 1 shown is D09 (quality management), linked by this project (see below).

- Under this project's status rule (see `docs/methodology.md`), 1 of the 8 requirements in Articles 8–15 (Chapter III, Section 2) reads `harmonised`, 6 read `in_progress` and 1 reads `uncovered`. The `harmonised` one is Article 11. It has that status because a standard the project links to it is cited in the Official Journal, not because a cited standard is known to cover it (see below).
- Article 8 (compliance with the requirements) reads `uncovered` by construction: no deliverable in C(2025) 3871 names it. This does not mean a gap in the standards for Articles 9–15.
- This dataset holds 11 JTC 21 work items under M/613 that expect an OJEU citation: 10 linked to Articles 9–15 and prEN 18285 (conformity assessment, outside Articles 8–15). On the work programme they stand at: 1 published (stage 60), 5 under approval (50), 1 under enquiry (40), 4 under drafting (20).
- Each of the seven requirements with at least one work item has one at enquiry or later. Article 13 was the last without one: its only work item, prEN 18229-2, was under drafting from 2026-01-06 and has been under approval since 2026-10-29.

### One harmonised standard cited in the Official Journal (in this dataset)

- EN 18286:2026, *Artificial intelligence – Quality management system for EU AI Act regulatory purposes*, has had a date of availability of 2026-07-22 on the CEN-CENELEC work programme. Its reference was published in the Official Journal by Commission Implementing Decision (EU) 2026/2274 of 12 October 2026 (OJ L, 2026/2274, 14.10.2026), in force from that day. Recital 3 of the Decision states that the standard corresponds to point 9 of Annex I to C(2025) 3871 (quality management systems for providers of AI systems, including post-market monitoring processes).
- It is the only work item in this dataset cited in the Official Journal.
- Article 11 reads `harmonised` because of a mapping made in this project, not in the request. C(2025) 3871 has no deliverable for Article 11 and asks for it to be covered in other standards, "particularly on the quality management system" (Annex II, Section 1), so `request_deliverables.csv` links Article 11 to that deliverable (D09). EN 18286:2026 is written for Article 17 (Annex II, Section 2.9). Implementing Decision (EU) 2026/2274 does not list which requirements of Regulation (EU) 2024/1689 the standard covers, and the presumption of conformity applies only "to the extent that those standards cover those requirements" (Article 40(1)). This project has no public source on how far EN 18286:2026 covers Article 11.

### Work items against the application dates

- C(2025) 3871 asked CEN and Cenelec to draft the ten deliverables by 31 August 2025 (Article 1(1)). As of 2026-11-06, one work item in this dataset is published (EN 18286:2026, available 2026-07-22).
- Chapter III, Sections 1, 2 and 3 of Regulation (EU) 2024/1689 (except Article 6(5)) apply from 2 December 2027 to AI systems classified as high-risk under Article 6(2) and Annex III, and from 2 August 2028 to those classified under Article 6(1) and Annex I (Article 113, third paragraph, point (c)(i) and (ii), as replaced by Article 1, point (40)(b), of Regulation (EU) 2026/1744). Annex I systems are outside this project's perimeter; their date is shown for reference. Against the Annex III application date of 2 December 2027:
- Of the 10 work items not yet published, 7 had a forecasted voting date on the work programme before 2 December 2027 as of 2026-11-06; EN 18286:2026 had been available since 2026-07-22. The shortest gap is 134 days, for prEN 18229-4 (accuracy) and prEN 18229-5 (robustness): both under drafting, with a forecasted vote on 2027-07-21. These are forecasts of a vote. Availability follows the vote, and citation in the Official Journal follows availability: for EN 18286:2026, citation came 84 days after availability.
- 3 of the 10 have a forecasted voting date that has already passed without a vote (`target_passed`):

| Work item | Deliverable | Status on the work programme | Stage date on the work programme | Forecasted voting date |
|---|---|---|---|---|
| prEN 18228, AI Risk Management | D01 | Under Approval | 2026-07-30 | 2026-09-30 |
| prEN 18282, Cybersecurity specifications for AI Systems | D08 | Under Approval | 2026-07-30 | 2026-07-15 |
| prEN 18285, AI Conformity assessment framework | D10 | Under Drafting | 2024-10-16 | 2026-07-29 |

- None of the 7 current forecasts falls after 2 December 2027 or 2 August 2028. For the three items above, the forecasted voting date went by without a vote. Until the work programme shows a new forecast, this project does not compare them with either application date (`target_passed`).
- The work programme gives a forecasted voting date. The date of availability (DAV) usually comes some weeks after the vote, and the reference is published in the Official Journal later still, by a Commission implementing decision. EN 18286:2026 was available on 2026-07-22 and cited on 2026-10-14. See `docs/methodology.md` for how dates are read.

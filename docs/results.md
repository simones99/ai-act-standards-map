# Results

Dated statements read from the tables in this repository. Each one holds at its date only; the weekly run updates the tables, not this page.

## As of 2026-10-23

Sources: `data/derived/coverage_by_requirement.csv` and `data/derived/timeline.csv` (`aasm derive`, as of 2026-10-23), built from `data/curated/standards.csv` (retrieved 2026-10-23 from the CEN-CENELEC JTC 21 work programme).

### Coverage by requirement

| Article | Requirement | Deliverables | Work items | At enquiry or later | Cited in OJEU | Status |
|---|---|---|---|---|---|---|
| 8 | Compliance with the requirements | 0 | 0 | 0 | 0 | uncovered |
| 9 | Risk management system | 1 | 1 | 1 | 0 | in_progress |
| 10 | Data and data governance | 1 | 2 | 1 | 0 | in_progress |
| 11 | Technical documentation | 1 | 1 | 1 | 1 | harmonised |
| 12 | Record-keeping | 1 | 1 | 1 | 0 | in_progress |
| 13 | Transparency and provision of information to deployers | 1 | 1 | 0 | 0 | in_progress |
| 14 | Human oversight | 1 | 1 | 1 | 0 | in_progress |
| 15 | Accuracy, robustness and cybersecurity | 3 | 3 | 1 | 0 | in_progress |

- 1 of 8 requirements is `harmonised`, 6 are `in_progress`, 1 is `uncovered`. Article 8 is the umbrella clause and has no deliverable in the request.
- The 11 work items stand at: 1 published (stage 60), 4 under approval (50), 1 under enquiry (40), 5 under drafting (20).
- Article 13 is the only covered requirement with no work item at enquiry or later: prEN 18229-2 is under drafting.

### One harmonised standard

- EN 18286:2026, *Artificial intelligence – Quality management system for EU AI Act regulatory purposes*, became available on 2026-07-22. Its reference was published by Commission Implementing Decision (EU) 2026/2274 of 12 October 2026 (OJ L, 14.10.2026), in answer to point 9 of Annex I of C(2025) 3871.
- It is the only work item in this dataset cited in the Official Journal. Article 11 reads `harmonised` because the request maps Article 11 to the quality management deliverable; how far EN 18286 covers Article 11 is stated in its Annex ZA, which is not public (see `docs/methodology.md`).

### Work items against the application dates

The application date for high-risk systems listed in Annex III is 2 December 2027, and 2 August 2028 for those under Annex I (Article 113, third paragraph, point (c), as amended by Regulation (EU) 2026/1744). Against 2 December 2027:

- 8 of 11 work items have a forecasted voting date before the deadline. The narrowest margin is 134 days: prEN 18229-4 (accuracy) and prEN 18229-5 (robustness), forecast 2027-07-21, both under drafting.
- 3 of 11 have a forecasted voting date that has already passed without a vote (`target_passed`):

| Work item | Deliverable | Status on the work programme | Since | Forecasted voting date |
|---|---|---|---|---|
| prEN 18228, AI Risk Management | D01 | Under Approval | 2026-07-30 | 2026-09-30 |
| prEN 18282, Cybersecurity specifications for AI Systems | D08 | Under Approval | 2026-07-30 | 2026-07-15 |
| prEN 18285, AI Conformity assessment framework | D10 | Under Drafting | 2024-10-16 | 2026-07-29 |

- No work item has a forecasted voting date after either deadline. A passed forecast says nothing about lateness, so these three are neither on time nor late until the work programme shows a new date.
- The forecasted voting date precedes publication by a few weeks; see `docs/methodology.md` for how dates are read.

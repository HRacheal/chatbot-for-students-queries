# Final dataset validation

Run: 2026-11-01. Blocking failures: 0. Warnings: 1.

| Check | Result | Detail |
|---|---|---|
| expected files exist | pass | 36 files present |
| all CSV and JSON files parse | pass | 56 CSV, 49 JSON |
| record ids are unique | pass | 2470 ids |
| no duplicate chunk content (body text, across Stage 2 and web) | pass | 817 chunks |
| chunks do not exceed 1000 characters | pass | [] |
| every web chunk starts with its heading path | pass | [] |
| every record names its source | pass | 0 without: [] |
| every PDF record has a page number | pass | 0: [] |
| every web record has a URL | pass | 0: [] |
| all_records_index.csv: one row per record, every row has a source | pass | 1050 rows; duplicate ids []; without source [] |
| external sources are labelled and kept separate | pass |  |
| every unresolved conflict/issue is in the register | pass | 51 unresolved of 54 |
| every unresolved issue is attached to at least one record or chunk | warning | only in the register: ['V11', 'W15'] |
| conflict records keep the evidence of each version | pass | [] |
| original PDFs unchanged (SHA-256) | pass | Academic-Calendar-2026-2027.pdf 618711f96eb9…, Student-Handbook.pdf 610a3da82992… |
| downloaded fee schedule unchanged | pass | 33d8f0d58491c159 |
| application files compared with the pre-integration baseline (informational) | pass | 25 changed, 8 new since the baseline (dataset integration) |
| no record is approved (all drafts) | pass | [] |
| web evidence quotes found in their snapshots | pass | [] |
| no secrets or connection strings in dataset files | pass | [] |
| restricted systems were not fetched | pass | [] |
| inaccessible / not-collected sources are recorded | pass | 8 recorded |

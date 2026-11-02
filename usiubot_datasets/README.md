# USIUBOT dataset

Real information about United States International University-Africa (USIU-Africa) for the USIUBOT student-query chatbot. Nothing is synthetic. Every record names its source (PDF page, or web page URL and snapshot). Every record is a **draft, pending verification, not approved**: it must be reviewed in the app's Approved Sources workflow before the chatbot may use it. Nothing has been imported into any database.

## Sources

* `Academic-Calendar-2026-2027.pdf` (project root, unchanged) — official URL confirmed by SHA-256 match.
* `Student-Handbook.pdf` (project root, unchanged) — undated; no public URL found (candidate URL 404).
* 76 official USIU-Africa web pages and 1 official PDF (2026-2027 fee schedule), collected 2026-11-01.
* 3 external pages (KUCCPS), kept in `external/` folders and labelled as not USIU-Africa policy.
* Full list with access outcomes: `validation_reports/source_register.csv`.

## Layout

| Folder | Contents |
|---|---|
| `01_general_university_information/` | General University Information: 74 structured records; Stage 2 chunks 157, web chunks 228, external chunks 0 |
| `02_academic_programmes/` | Academic Programmes: 48 structured records; Stage 2 chunks 6, web chunks 145, external chunks 0 |
| `03_admissions_and_applications/` | Admissions and Applications: 36 structured records; Stage 2 chunks 4, web chunks 91, external chunks 2 |
| `04_fees_and_payments/` | Fees and Payments: 607 structured records; Stage 2 chunks 27, web chunks 98, external chunks 0 |
| `05_registrar_and_academic_administration/` | Registrar and Academic Administration: 59 structured records; Stage 2 chunks 9, web chunks 34, external chunks 0 |
| `06_department_contacts_and_query_routing/` | Department Contacts and Query Routing: 105 structured records; Stage 2 chunks 5, web chunks 10, external chunks 0 |
| `07_academic_documents_results_and_verified_eligibility/` | Academic Documents, Results and Verified Eligibility: 71 structured records; Stage 2 chunks 0, web chunks 0, external chunks 1 |
| `08_questions_answers_and_unresolved_enquiries/` | Questions, Answers and Unresolved Enquiries: 50 structured records; Stage 2 chunks 0, web chunks 0, external chunks 0 |
| `source_documents/` | page-by-page text of the three PDFs, with metadata |
| `web_sources/` | collection manifest, page snapshots, raw collection reports, downloaded PDF |
| `validation_reports/` | source register, conflict and verification register, missing information register, fee table checks, layout check, final validation, reports |
| `collection_register/` | Stage 2 collection register |
| `extraction_scripts/` | all scripts (standard library + pypdf only) |
| `all_records_index.csv` | one row per structured record across all categories, with the traceability fields |

Structured records: 1050 (official 1024, external 4, derived open questions 22). Sections and chunks are counted separately and are not records.

## Rules for using this data

* Bank and M-PESA details differ between sources and are unconfirmed. Never present them as confirmed payment instructions: refer users to the Finance Office (finance@usiu.ac.ke) to confirm.
* Where sources conflict, both versions are kept and linked to an issue id (V = PDF, W = website). See `validation_reports/conflict_and_verification_register.csv`.
* External (KUCCPS) statements must never be presented as USIU-Africa policy.
* Expired deadlines are marked; never present them as open.
* Category 08 contains official FAQ pairs and open questions derived from gaps. It contains no real or invented student enquiries.

## Rebuild and validate (Windows PowerShell, from the project root)

```powershell
cd C:\Users\Admin\Downloads\chatbot-for-students-queries-1
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTHONIOENCODING = "utf-8"
# everything: PDFs -> website records -> registers -> validation
.\backend\.venv\Scripts\python.exe usiubot_datasets\extraction_scripts\build_all.py
# validation only
.\backend\.venv\Scripts\python.exe usiubot_datasets\extraction_scripts\validate_dataset.py
# dataset tests
.\backend\.venv\Scripts\python.exe -m pytest usiubot_datasets\tests -q -p no:cacheprovider
# check which web pages robots.txt allows for the automated collector (reads robots.txt only)
.\backend\.venv\Scripts\python.exe usiubot_datasets\extraction_scripts\collect_web_sources.py --check-robots
# refresh permitted pages (conditional requests; changed pages are kept for review, never approved)
.\backend\.venv\Scripts\python.exe usiubot_datasets\extraction_scripts\collect_web_sources.py --fetch
# import pages a person saved from a browser (for pages robots.txt blocks for automated collectors)
.\backend\.venv\Scripts\python.exe usiubot_datasets\extraction_scripts\collect_web_sources.py --import-html C:\path\to\saved_pages
```

Report: `validation_reports/FINAL_DATASET_IMPLEMENTATION_REPORT.md`.

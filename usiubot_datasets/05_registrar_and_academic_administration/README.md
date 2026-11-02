# 05 Registrar and Academic Administration

Handbook section 4 (registration and academic information: Registrar, records, ID card, certificate replacement), the Registrar's services list, and calendar events about registration, add/drop, withdrawal, grades, examinations, placement tests and graduation.

Every record is `review_status: draft`, `verification_status: pending_verification`, `approval_status: not_approved`, `data_origin: official`. Nothing has been imported into the app or any database.

## Files

| File | Records | Contents |
|---|---|---|
| `official/document_sections.json` | 6 | One record per document section (full text, pages, heading, flags, issues). |
| `official/knowledge_chunks.json` | 9 | The same sections split into retrieval chunks of at most 1,000 characters (no overlap), each with full source metadata. |
| `official/sections_for_review.md` | 6 | Human-readable version of the sections for review. |
| `official/sections_index.csv` | 6 | One row per section: pages, size, chunk count, flags, issues, status. |
| `official/calendar_events.csv` | 48 | Dated calendar events for this category, one row per printed bullet. |
| `official/registrar_services.csv` | 11 | The 11 services offered by the Registrar (handbook 4.3). |

`external/` is empty (no external sources were collected in Stage 2). `metadata/category_metadata.json` holds counts and coverage.

## Coverage of the information this category needs

| Information | Status | Notes |
|---|---|---|
| Transcript requests | Partially extracted | The Registrar processes transcripts (4.1, 4.3); M-PESA code TSPT exists; no procedure or fee. |
| Results slips | Unavailable | Not mentioned. |
| Examination regulations | Unavailable | Only exam dates (calendar). No exam rules. |
| Course registration and add/drop | Extracted | Calendar dates; handbook add/drop procedure (3.9). |
| Deferred / special examinations | Partially extracted | Special exam dates only; no rules. |
| Graduation requirements | Unavailable | Not stated; the handbook refers to the Academic Catalog. |
| Graduation application and commencement dates | Extracted | Graduation application windows, rehearsals and Commencement Day (conflict V17). |
| Academic progression / probation | Partially extracted | Only financial-aid GPA probation (5.2.6). |
| Deferment / leave of absence | Partially extracted | Leave of absence maximum one academic year (5.2.2); processed by the Registrar (4.3). |
| Withdrawal | Extracted | Last withdrawal dates; withdrawal/charge waiver procedure (3.9). |
| Academic appeals | Unavailable | Only non-academic disciplinary appeals (10.13). |
| Student records | Extracted | Record access and disclosure (4.2); certificate replacement (4.5); ID card (4.4). |

## Issues affecting records in this folder

| Issue | Severity | Summary |
|---|---|---|
| V05 | medium | The handbook links to the Academic Catalog 2021-2023. |
| V07 | high | The handbook does not state its academic year, edition or publication date. The latest year in the text is 2024; the PDF file metadata says it was created on 2025-07-30 and modified on 2025-08-13 (file metadata is not proof of publication). |
| V17 | medium | Graduation year label for Fall 2026 completers differs: 30 October 2026 '2027 Graduation and certificate application process begins for students completing degree requirements in Fall 2026' vs 4 January 2027 'Deadline for 2026 Graduation and certificate application for students completing degree requirements in Fall 2026'. |
| V19 | low | The Fall 2026 mid-semester exam week (19-24 October) includes 20 October, Mashujaa Day, when offices are closed. The calendar does not say whether exams take place that day. |
| V20 | medium | Calendar date and day name disagree: September 16 Friday (2026-09-16 is a Wednesday; the calendar says Friday; affects 3 events) |
| V22 | high | The calendar's official URL is not confirmed (recorded as 'Local copy — official URL not yet confirmed'). The existing Approved Sources feature requires an https usiu.ac.ke URL for every source. |
| V23 | medium | The handbook's official URL is not confirmed. A candidate URL exists in the official links catalogue but it was not downloaded or compared with the local copy. |

Full details: `../validation_reports/validation_issues.csv`.

<!-- WEB-START -->
## Website and external records (collected 2026-11-01)

| File | Rows | Contents |
|---|---|---|
| official/web_document_sections.json | 20 | page sections (heading path + text) from the website snapshots |
| official/web_knowledge_chunks.json | 34 | chunks of at most 1000 characters; each starts with its heading path and never cuts a sentence |
| official/web_sections_index.csv | 20 | index of the web sections |

Sections / chunks in this category: Stage 2 PDF 6 / 9; official website 20 / 34; external 0 / 0.

Every website record carries: record id, category, topic, information, source title, URL, snapshot file, section, date collected, publication date ("Publication date not stated" where none is printed), academic year, source type (official/external), verification status, conflict/warning (issue ids) and last checked date. All records are drafts, pending verification, not approved.
Issues: `validation_reports/conflict_and_verification_register.csv`.
<!-- WEB-END -->

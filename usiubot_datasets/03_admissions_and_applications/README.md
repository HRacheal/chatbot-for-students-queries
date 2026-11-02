# 03 Admissions and Applications

Handbook sections 5.2-5.2.3 (Admissions and Financial Aid Department, admissions, re-admission, returning graduates), admission conditions as printed, and the three admission application deadlines from the calendar. Scholarships are filed in 04 (financial aid) to avoid duplication.

Every record is `review_status: draft`, `verification_status: pending_verification`, `approval_status: not_approved`, `data_origin: official`. Nothing has been imported into the app or any database.

## Files

| File | Records | Contents |
|---|---|---|
| `official/document_sections.json` | 4 | One record per document section (full text, pages, heading, flags, issues). |
| `official/knowledge_chunks.json` | 4 | The same sections split into retrieval chunks of at most 1,000 characters (no overlap), each with full source metadata. |
| `official/sections_for_review.md` | 4 | Human-readable version of the sections for review. |
| `official/sections_index.csv` | 4 | One row per section: pages, size, chunk count, flags, issues, status. |
| `official/admission_conditions.csv` | 8 | Admission-related rules quoted verbatim. |
| `official/calendar_events.csv` | 3 | Dated calendar events for this category, one row per printed bullet. |

`external/` is empty (no external sources were collected in Stage 2). `metadata/category_metadata.json` holds counts and coverage.

## Coverage of the information this category needs

| Information | Status | Notes |
|---|---|---|
| Undergraduate requirements / minimum academic qualifications / required subjects | Unavailable | Not in either document. |
| Postgraduate requirements | Unavailable | Not in either document. |
| International student requirements | Partially extracted | English proficiency scores (5.2.1) and a pointer to the International Students Handbook (5.4.4). |
| Application procedures | Partially extracted | Re-admission and returning-graduate rules only (5.2.2, 5.2.3). |
| Application deadlines and intake periods | Extracted | Application deadlines for Spring 2027, Summer 2027 and Fall 2027 (calendar_events.csv). |
| Application fees | Partially extracted | A 'non-refundable application processing fee' is mentioned (5.2.2, 5.2.3) and an M-PESA purpose code ADM exists; no amount. |
| Required documents | Unavailable | Not listed (conditional admission mentions 'necessary documents' only). |
| Transfer requirements | Partially extracted | Credit transfers need Academic Dean approval (5.2.1); inter-campus transfer is a Registrar service (4.3). |
| Scholarship information | Extracted | See 04_fees_and_payments/official/financial_aid_programmes.csv. |

## Issues affecting records in this folder

| Issue | Severity | Summary |
|---|---|---|
| V07 | high | The handbook does not state its academic year, edition or publication date. The latest year in the text is 2024; the PDF file metadata says it was created on 2025-07-30 and modified on 2025-08-13 (file metadata is not proof of publication). |
| V16 | medium | English proficiency requirement may be outdated. It includes a TOEFL 'computer-based test' score (213). Processing note (general knowledge, not from the document): the computer-based TOEFL is no longer offered, so the requirement needs confirmation. |
| V22 | high | The calendar's official URL is not confirmed (recorded as 'Local copy — official URL not yet confirmed'). The existing Approved Sources feature requires an https usiu.ac.ke URL for every source. |
| V23 | medium | The handbook's official URL is not confirmed. A candidate URL exists in the official links catalogue but it was not downloaded or compared with the local copy. |

Full details: `../validation_reports/validation_issues.csv`.

<!-- WEB-START -->
## Website and external records (collected 2026-11-01)

| File | Rows | Contents |
|---|---|---|
| official/web_admission_rules.csv | 23 | admission rules quoted from the Admission Requirements, How to Apply, Intake and International Applicants pages |
| official/web_document_sections.json | 80 | page sections (heading path + text) from the website snapshots |
| official/web_knowledge_chunks.json | 91 | chunks of at most 1000 characters; each starts with its heading path and never cuts a sentence |
| official/web_sections_index.csv | 80 | index of the web sections |
| external/external_records.csv | 2 | EXTERNAL statements (KUCCPS) — never USIU-Africa policy |
| external/web_document_sections.json | 2 | page sections (heading path + text) from the website snapshots |
| external/web_knowledge_chunks.json | 2 | chunks of at most 1000 characters; each starts with its heading path and never cuts a sentence |
| external/web_sections_index.csv | 2 | index of the web sections |

Sections / chunks in this category: Stage 2 PDF 4 / 4; official website 80 / 91; external 2 / 2.

Every website record carries: record id, category, topic, information, source title, URL, snapshot file, section, date collected, publication date ("Publication date not stated" where none is printed), academic year, source type (official/external), verification status, conflict/warning (issue ids) and last checked date. All records are drafts, pending verification, not approved.
Issues: `validation_reports/conflict_and_verification_register.csv`.
<!-- WEB-END -->

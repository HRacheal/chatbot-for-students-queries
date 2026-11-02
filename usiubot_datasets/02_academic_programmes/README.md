# 02 Academic Programmes

Neither document lists academic programmes. This folder holds the six schools (handbook page 7) and the USIU-Online sections (handbook section 9: mode of study, expectations, computer requirements). The handbook refers to an Academic Catalog for programme details, but its link is for 2021-2023 (issue V05).

Every record is `review_status: draft`, `verification_status: pending_verification`, `approval_status: not_approved`, `data_origin: official`. Nothing has been imported into the app or any database.

## Files

| File | Records | Contents |
|---|---|---|
| `official/document_sections.json` | 5 | One record per document section (full text, pages, heading, flags, issues). |
| `official/knowledge_chunks.json` | 6 | The same sections split into retrieval chunks of at most 1,000 characters (no overlap), each with full source metadata. |
| `official/sections_for_review.md` | 5 | Human-readable version of the sections for review. |
| `official/sections_index.csv` | 5 | One row per section: pages, size, chunk count, flags, issues, status. |
| `official/schools.csv` | 6 | The six schools and their abbreviations. |

`external/` is empty (no external sources were collected in Stage 2). `metadata/category_metadata.json` holds counts and coverage.

## Coverage of the information this category needs

| Information | Status | Notes |
|---|---|---|
| Programme list / programme ID / programme name | Unavailable | No programmes are listed in either document. |
| Degree level | Partially extracted | Only the general statement that programmes are Undergraduate, Graduate or Short Professional courses (p5). |
| School or department | Extracted | Six schools (schools.csv, handbook p7). |
| Programme description, duration, specialisations, curriculum, career opportunities | Unavailable | Not in either document; the handbook refers to the Academic Catalog (2021-2023 link, issue V05). |
| Mode of study | Partially extracted | USIU-Online e-learning information (handbook section 9). No per-programme mode. |
| Programme admission requirements | Unavailable | Not in either document. |
| Official programme source URL | Unavailable | Only the outdated Academic Catalog 2021-2023 link. |

## Issues affecting records in this folder

| Issue | Severity | Summary |
|---|---|---|
| V07 | high | The handbook does not state its academic year, edition or publication date. The latest year in the text is 2024; the PDF file metadata says it was created on 2025-07-30 and modified on 2025-08-13 (file metadata is not proof of publication). |
| V23 | medium | The handbook's official URL is not confirmed. A candidate URL exists in the official links catalogue but it was not downloaded or compared with the local copy. |

Full details: `../validation_reports/validation_issues.csv`.

<!-- WEB-START -->
## Website and external records (collected 2026-11-01)

| File | Rows | Contents |
|---|---|---|
| official/web_document_sections.json | 63 | page sections (heading path + text) from the website snapshots |
| official/web_knowledge_chunks.json | 145 | chunks of at most 1000 characters; each starts with its heading path and never cuts a sentence |
| official/web_programmes.csv | 42 | one row per official programme page (42): school, duration, intake, mode, accreditation text |
| official/web_sections_index.csv | 63 | index of the web sections |

Sections / chunks in this category: Stage 2 PDF 5 / 6; official website 63 / 145; external 0 / 0.

Every website record carries: record id, category, topic, information, source title, URL, snapshot file, section, date collected, publication date ("Publication date not stated" where none is printed), academic year, source type (official/external), verification status, conflict/warning (issue ids) and last checked date. All records are drafts, pending verification, not approved.
Issues: `validation_reports/conflict_and_verification_register.csv`.
<!-- WEB-END -->

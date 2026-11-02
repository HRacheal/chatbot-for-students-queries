# 07 Academic Documents, Results and Verified Eligibility

Only the English language proficiency minimums (handbook 5.2.1) were found. No KCSE, diploma or international qualification requirements and no programme-specific requirements exist in either document. Individual students' results slips are not stored here (the app processes them in memory and never stores them); this folder is only for the university's own requirements.

Every record is `review_status: draft`, `verification_status: pending_verification`, `approval_status: not_approved`, `data_origin: official`. Nothing has been imported into the app or any database.

## Files

| File | Records | Contents |
|---|---|---|
| `official/english_proficiency_requirements.csv` | 5 | English test minimums for applicants from non-English speaking countries (not programme-specific). |

`external/` is empty (no external sources were collected in Stage 2). `metadata/category_metadata.json` holds counts and coverage.

## Coverage of the information this category needs

| Information | Status | Notes |
|---|---|---|
| KCSE entry requirements (minimum grades, required subjects) | Unavailable | Not in either document. |
| International qualifications, diplomas, other qualifications | Unavailable | Not in either document. |
| Qualification equivalencies | Partially extracted | English language test minimums only (english_proficiency_requirements.csv; issue V16). |
| Programme-specific admission conditions | Unavailable | Not in either document. |

## Issues affecting records in this folder

| Issue | Severity | Summary |
|---|---|---|
| V07 | high | The handbook does not state its academic year, edition or publication date. The latest year in the text is 2024; the PDF file metadata says it was created on 2025-07-30 and modified on 2025-08-13 (file metadata is not proof of publication). |
| V16 | medium | English proficiency requirement may be outdated. It includes a TOEFL 'computer-based test' score (213). Processing note (general knowledge, not from the document): the computer-based TOEFL is no longer offered, so the requirement needs confirmation. |

Full details: `../validation_reports/validation_issues.csv`.

<!-- WEB-START -->
## Website and external records (collected 2026-11-01)

| File | Rows | Contents |
|---|---|---|
| official/programme_entry_requirements.csv | 42 | entry requirements per programme page (or 'not stated') |
| official/web_english_proficiency_requirements.csv | 6 | English proficiency tests and minimums (website) |
| official/web_transfer_credit_rules.csv | 16 | transfer credit, examination credit, transcripts (two pages conflict: W11) |
| external/external_records.csv | 2 | EXTERNAL statements (KUCCPS) — never USIU-Africa policy |
| external/web_document_sections.json | 1 | page sections (heading path + text) from the website snapshots |
| external/web_knowledge_chunks.json | 1 | chunks of at most 1000 characters; each starts with its heading path and never cuts a sentence |
| external/web_sections_index.csv | 1 | index of the web sections |

Sections / chunks in this category: Stage 2 PDF 0 / 0; official website 0 / 0; external 1 / 1.

Every website record carries: record id, category, topic, information, source title, URL, snapshot file, section, date collected, publication date ("Publication date not stated" where none is printed), academic year, source type (official/external), verification status, conflict/warning (issue ids) and last checked date. All records are drafts, pending verification, not approved.
Issues: `validation_reports/conflict_and_verification_register.csv`.
<!-- WEB-END -->

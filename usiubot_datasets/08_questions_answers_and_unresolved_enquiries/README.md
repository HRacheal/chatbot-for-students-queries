# 08 Questions, Answers and Unresolved Enquiries

Operational data (user questions, answers, sources used, department classification, enquiry references and statuses). It is created by the running USIUBOT application in MongoDB (collections queries, query_log, chat_history, enquiries), not extracted from documents. Nothing was imported or exported in Stage 2. Previous AI answers are never converted into knowledge.

Every record is `review_status: draft`, `verification_status: pending_verification`, `approval_status: not_approved`, `data_origin: official`. Nothing has been imported into the app or any database.

## Files

No records: see the note above.

`external/` is empty (no external sources were collected in Stage 2). `metadata/category_metadata.json` holds counts and coverage.

## Coverage of the information this category needs

| Information | Status | Notes |
|---|---|---|
| User questions, answers, sources, classification, enquiry references and statuses | Unavailable | Operational data. It is created by the running application, not extracted from documents. Nothing was imported in Stage 2. |

<!-- WEB-START -->
## Website and external records (collected 2026-11-01)

| File | Rows | Contents |
|---|---|---|
| official/official_faq_pairs.csv | 28 | questions and answers published on official FAQ sections (not student enquiries) |
| official/open_questions_register.csv | 22 | questions the dataset cannot answer yet, derived from its own conflicts and gaps (NOT student enquiries) |

Sections / chunks in this category: Stage 2 PDF 0 / 0; official website 0 / 0; external 0 / 0.

Every website record carries: record id, category, topic, information, source title, URL, snapshot file, section, date collected, publication date ("Publication date not stated" where none is printed), academic year, source type (official/external), verification status, conflict/warning (issue ids) and last checked date. All records are drafts, pending verification, not approved.
Issues: `validation_reports/conflict_and_verification_register.csv`.
<!-- WEB-END -->

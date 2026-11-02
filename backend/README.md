# Backend (Flask API)

See the [root README](../README.md) for setup, the technology stack and the API overview.

## Structure

```
app.py                  create_app(): config validation, CORS, error handling, blueprints
wsgi.py                 Production entry point: gunicorn wsgi:app
config/config.py        All settings, read from environment variables (see .env.example)
config/database.py      MongoDB connection and indexes
routes/                 URL → controller wiring; authentication decorators are applied here
controllers/            Input validation and HTTP responses
services/
  chat_service.py       USIU-scoped answers from approved sources, citations, stale/conflict warnings
  sources.py            Approved-source registry (MongoDB) and local BM25 index
  knowledge_base.py     Pinecone index: per-document chunking, deterministic IDs, rebuild/delete
  cloudinary_service.py PDF storage (private by default), signed URLs, size-limited downloads
  admin_service.py      Dashboard data and admin answers
  auth_service.py       Signup/login (bcrypt) and bootstrap admin login
  email_service.py      SMTP notifications with explicit success/failure results
models/models.py        MongoDB access for users, queries, chat history; PDF view model
middleware/middleware.py JSON error handling, security headers, opt-in tracing
utils/
  auth.py               JWT creation/verification; login_required and admin_required
  validation.py         Request validation helpers
  rate_limit.py         In-memory per-client rate limiting
  logging_utils.py      Logging setup with redaction of personal data
  pdf_utils.py          PDF validation, text extraction (pypdf), admin Q&A document
  helpers.py            Small-talk detection, analytics helpers
tests/                  pytest suite (external services replaced with fakes)
services/
  web_access.py         Permitted page fetching: exact trusted hosts, robots.txt, redirects, limits, in-memory cache
  live_retrieval.py     Official page catalogue (metadata only) and live retrieval for chat answers
  page_text.py          Visible text of an HTML page (shared with the staging tool)
  routing.py            Admissions / Registrar / Marketing classification; guidance-intent detection
  enquiry_service.py    Unresolved enquiries: consent, routing, duplicates, tracking, notifications
  guidance_service.py   Results-slip extraction (in memory) and transparent programme matching
config/official_pages.json  Candidate official page URLs (all unreviewed; reviewed=true enables live fetching)
tools/live_check.py     Read-only access check for live retrieval (run from the deployment host)
tools/run_local.py      Local test server with an in-memory database and local test logins
tools/knowledge_sources.py  Optional staging tool for official documents (robots.txt-aware; not used for answers)
resources/usiubot_knowledge/ Staging folders + metadata for documents awaiting admin review (not used by the chatbot)
```

## Approved sources and answers (Phase 2)

Chat answers come only from **approved sources** (`sources` collection), searched with a local keyword
(BM25) index over `source_chunks`. No Pinecone, Cloudinary or network access is needed.

- **Keyword matching:** light stemming plus a small synonym/phrase table (`SYNONYM_GROUPS` in
  `services/sources.py`), so "cost/price/tuition", "transcript/academic record/results",
  "hostel/dorm/housing/where can I live", "register/sign up/enrol", "defer/postpone/start next year" and
  "scholarship/financial aid/funding" match each other. Words found in nearly all university text
  ("student", "campus", "university") are ignored when matching. A passage must contain at least half of
  the question's key terms (synonym concepts count double); multi-part questions are also matched part by
  part. This is keyword search, not semantic search: paraphrases outside the synonym table can still be
  missed and end up logged as unsupported.

- **Source record:** https URL on an allowed domain (`ALLOWED_SOURCE_DOMAINS`), title, department
  (`admissions`, `registrar`, `finance`, `academic_programmes`, `marketing`, `student_affairs`, `ict`,
  `library`, `general_university`), content type
  (`html`/`pdf`), status (`draft` → `approved` → `archived`), source date (as printed, optional),
  retrieval date, notes and an audit trail (`status_history`).
- **Approval:** only approved sources are indexed. Archiving removes their chunks. Changing the URL or text
  of an approved source returns it to draft. Retrieval re-checks approval in MongoDB, so a cached index can
  never return an archived source.
- **Answers:**
  - The model sees numbered sources (no URLs) and must cite them as `[n]`.
  - Citations are built from the stored records. URLs the model writes are removed unless they belong to a
    cited source.
  - A question with no matching source is never refused just because no keyword matched. If it is
    recognisably about the university (a university word or synonym concept), it is reported as
    unsupported and logged as an unanswered query (`scope: "usiu"`). Otherwise the model, if configured,
    is asked only whether it is about USIU-Africa: "yes" is logged as unsupported, "no" is refused. If that
    can't be decided (no model, error, unclear reply), the user gets the out-of-scope message and the
    question is still logged with `scope: "unclear"` for staff review.
  - The internal `OUT_OF_SCOPE` marker is never shown, even inside other text. A recognisable university
    question the model calls out of scope is logged as unsupported instead.
  - Saved chat history keeps each answer's citations. When history is read, citations are re-checked:
    a source that is no longer approved (or whose URL no longer matches) is shown without a link and
    marked `available: false`.
  - Out-of-date sources and model-reported conflicts produce warnings.
- **Admin API:** `GET/POST /api/admin/sources`, `GET/PUT /api/admin/sources/<id>`,
  `POST /api/admin/sources/<id>/status` (admin token). `POST` also accepts a multipart PDF; its text is
  extracted locally and nothing is uploaded to Cloudinary.
- **No crawling:** live website crawling is not implemented. `tools/knowledge_sources.py` only records
  discovered URLs and obeys robots.txt.

## USIUBOT dataset (usiubot_datasets/)

The completed dataset is loaded into the same approved-source registry and BM25 index; no other
retrieval system is used.

- **Import (drafts only):** admin dashboard → Sources → *USIUBOT dataset* (dry run, then import), or
  `python -m tools.import_dataset` (dry run) / `--apply` (needs MongoDB). One dataset *section* becomes one
  source keyed `dataset:<section_id>`; its passages are the dataset's own chunks with chunk id, page numbers
  and section heading. Nothing is approved by the import (`approved_by_import: 0`).
- **Refresh:** importing again skips unchanged sections, returns an approved section whose text changed to
  draft (and removes it from the index), archives sections that left the dataset, and keeps administrator
  edits to title and department. Duplicate passages (same text in another section) are indexed once.
- **Origins:** only `official` (USIU-Africa) and `external` records are accepted. External records need an
  https URL on `EXTERNAL_SOURCE_DOMAINS` and are always labelled as not USIU-Africa policy, to the model and
  to the user. A dataset folder with a `TEST_DATASET` marker is a synthetic test fixture: it can only be
  imported, and its records only retrieved, in test mode (`ALLOW_TEST_SOURCES`, refused in production).
- **Citations:** web sections link to the page URL; PDF sections show the file name, page range and section
  heading (the Student Handbook has no working public URL, so it is cited by file and page). Citations also
  carry category, collection date and origin.
- **Warnings:** open medium/high conflicts, outdated and inconsistency items from
  `validation_reports/conflict_and_verification_register.csv` are attached to the affected sections and
  shown with answers; low-severity notes are visible to administrators only. Sections with bank, paybill or
  SWIFT details carry a "confirm with the Finance Office" warning.
- **Review:** filter by category, origin, department, flags or title; select sources and approve, reject,
  archive or return them to draft (`POST /api/admin/sources/bulk-status`, at most 500 per request; each
  goes through the normal approval checks). `GET /api/admin/dataset/search?q=&category=` shows what the
  chatbot would retrieve from approved sources.
- **Routing:** `GET /api/admin/routing`, `PUT /api/admin/routing/<department>` (staff delivery addresses,
  notes, published contacts and whether students may see them), `POST /api/admin/routing/import-contacts`
  (copies contacts as printed in the dataset, unpublished; never sets delivery addresses). Delivery
  addresses set here take precedence over `ENQUIRY_EMAIL_<DEPARTMENT>`.

## Knowledge-base indexing (legacy PDF management — not used for chat answers)

The **PDF Management** page and `/api/pdfs/*` routes (Cloudinary storage, Pinecone index, Rebuild
Embeddings) still work as before for administrators, but **nothing they store affects chat answers**.
To make a PDF's content available to USIUBOT, upload it under **Approved Sources** and approve it.

- Every PDF is chunked separately (`RecursiveCharacterTextSplitter`, 1000 characters, 150 overlap).
- Each chunk's vector ID is `<cloudinary public_id>#chunk-<n>`, and its metadata records `source_id` and `title`.
- **Rebuild** re-indexes every stored PDF, then deletes vectors that don't belong to a current document. That covers deleted documents, documents that got shorter, and duplicates with random IDs left by earlier versions.
  - Vectors of a document that failed to download are kept.
  - If no text can be extracted at all, the index is left unchanged.
- **Deleting** a PDF also deletes its vectors.
- Text is extracted with `pypdf`. Scanned (image-only) PDFs produce no text; OCR is planned for a later phase.
- Prefix listing (`index.list`) requires a Pinecone **serverless** index. The app creates one automatically using `PINECONE_CLOUD`/`PINECONE_REGION` if the index doesn't exist.

## Admin answers

When an administrator answers an unanswered query:
1. The answer is saved on the query and shown to the user in their notification.
2. It is saved as a **draft staff-answer source** (`content_type: "staff_answer"`, no URL, department
   optional in the request, default `general_university`). Drafts are never used by the chatbot. Once an
   administrator approves it under Approved Sources, it can be cited as "answer from USIU staff" (without
   a link). Answering the same query again updates the same source and returns it to draft.
3. A registered user is emailed.

The response reports `email_notification` (`sent`/`failed`/`not_applicable`), `draft_source_created` and
`draft_source_id`. Admin answers are no longer appended to the legacy Cloudinary "extra" Q&A PDF.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

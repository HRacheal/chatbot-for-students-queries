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
  chat_service.py       Small-talk handling, RAG answer generation, unanswered-query logging
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
```

## Knowledge-base indexing

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
1. The answer is saved on the query.
2. It is appended to a generated "extra" Q&A PDF in the knowledge-base folder. It becomes searchable after the next rebuild.
3. A registered user is emailed.

The response reports `email_notification` (`sent`/`failed`/`not_applicable`) and whether the Q&A document was updated. This mechanism is temporary and will be replaced by a reviewed enquiry/FAQ workflow.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

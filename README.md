# Student Query Chatbot → USIUBOT (in development)

This repository is being adapted into **USIUBOT**, an AI assistant for USIU-Africa.
It started as the open-source *chatbot-for-students-queries* project.

> **Status: Phase 1 (security and stabilisation) complete.** The assistant is not
> yet USIU-Africa specific. It has no department routing, enquiry tickets or
> results-slip analysis yet, and it has **no verified USIU-Africa documents** in
> its knowledge base. Do not deploy it publicly or connect it to university
> systems without review and approval.

## What the application does today

- **Chat (web widget):** visitors ask questions without an account. Logged-in users also get a saved chat history.
- **Retrieval-augmented answers:** questions are answered *only* from PDFs that administrators upload. If the documents don't contain the answer, the assistant says so and logs the question for staff.
- **Admin dashboard:** statistics, unanswered queries, written answers (with an email notification to registered users), all users' chat history, simple sentiment/topic analytics, and knowledge-base PDF management (upload, preview, delete, rebuild index).

## Actual technology stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite 6, Tailwind CSS, React Router, Axios |
| Backend | Python 3.12, Flask 3.1 (application factory, blueprints, controllers/services/models) |
| Database | MongoDB (`users`, `queries`, `chat_history` collections) |
| Language model | **Groq**-hosted `llama-3.3-70b-versatile` via `langchain-groq` (configurable with `GROQ_MODEL`) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2`, run locally on CPU (384 dimensions) |
| Vector store | **Pinecone** serverless index, via `langchain-pinecone` |
| RAG pipeline | LangChain `ConversationalRetrievalChain` (from `langchain-classic`) |
| Document storage | Cloudinary (private `authenticated` delivery by default) |
| Email | SMTP via Python's `smtplib` (Gmail by default) |
| Auth | JWT (HS256) + bcrypt |

Earlier versions of this README mentioned **Google Gemini** and **FAISS**. Neither is used anywhere in the code.

## Repository layout

```
backend/
  app.py              Flask application factory (create_app) and dev server
  wsgi.py             Production entry point (gunicorn wsgi:app)
  config/             Settings from environment variables, MongoDB connection
  routes/             URL definitions (auth, chat, admin, pdf)
  controllers/        Request validation and HTTP responses
  services/           Business logic: chat_service (RAG), knowledge_base (indexing),
                      admin_service, auth_service, email_service, cloudinary_service
  models/             MongoDB data access
  middleware/         Error handling, security headers, tracing configuration
  utils/              auth (JWT + decorators), validation, rate limiting,
                      log redaction, PDF helpers, small-talk detection
  tests/              Automated tests (pytest)
frontend/
  src/components/     Chat widget, admin dashboard, PDF management, login/sign-up
  src/lib/            API client and safe Markdown parser
```

## Getting started (local development)

### Prerequisites
- Python **3.12** (the code uses syntax that older versions do not support)
- Node.js 18+ and npm
- MongoDB (local or Atlas)
- For AI answers: Groq and Pinecone API keys. For document upload: a Cloudinary account. For email: an SMTP account.

The app starts without Groq, Pinecone, Cloudinary or SMTP credentials. In that case, questions are logged as unanswered and the relevant admin features report that the service is not configured.

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt        # full install (includes PyTorch; large)
cp .env.example .env                   # then fill in values; never commit .env
python app.py                          # http://127.0.0.1:5000
```

`SECRET_KEY` is **required**: the app refuses to start without a random value of at least 32 characters. Generate one with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

All environment variables are documented in [`backend/.env.example`](backend/.env.example).

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local     # leave VITE_API_BASE_URL empty for local development
npm run dev                    # http://localhost:5173
```

### First use of the knowledge base
1. Log in at `/admin` with `ADMIN_EMAIL` / `ADMIN_PASSWORD`.
2. Open **PDF Management**, upload approved PDF documents, then click **Rebuild Embeddings**.
3. The rebuild indexes every stored PDF and removes search entries for deleted or changed documents. It is safe to run repeatedly.

The application no longer creates embeddings automatically at startup.

## Running the tests

```bash
cd backend
pip install -r requirements-dev.txt    # lightweight: no PyTorch needed
python -m pytest

cd ../frontend
npm test
```

The backend tests replace MongoDB, Pinecone, Cloudinary, SMTP and the language model with in-memory fakes, so they need no credentials or network access. `tests/test_ai_integration.py` exercises the real LangChain pipeline offline. It runs only when the full AI dependencies are installed and is skipped otherwise.

## API overview

| Method & path | Access | Purpose |
|---|---|---|
| `POST /api/signup`, `POST /api/login` | public (rate-limited) | User accounts |
| `POST /api/admin/login` | public (rate-limited) | Administrator login |
| `POST /api/query` | public (rate-limited) | Ask a question (`{question, session_id?}`) |
| `GET /api/chat-history` | user token | The user's own history |
| `GET /api/admin/stats`, `/chat-history`, `/query-analytics`, `/unanswered-queries` | admin token | Dashboard data |
| `POST /api/add-response`, `DELETE /api/delete-query/<id>` (also under `/api/admin/`) | admin token | Answer or delete unanswered queries |
| `GET /api/pdfs/`, `POST /api/pdfs/upload`, `DELETE /api/pdfs/<id>`, `POST /api/pdfs/rebuild-embeddings` | admin token | Knowledge-base documents |
| `GET /health` | public | Health check |

Debug endpoints (`/debug/*`) exist only when `ENABLE_DEBUG_ROUTES=true` outside production, and they require an admin token.

## Security notes

- All administrative endpoints require an admin JWT. User and admin tokens are distinct and can't be swapped.
- Answers are rendered as text with a small, safe Markdown subset. HTML in answers is never executed.
- New knowledge-base PDFs are stored privately. PDFs uploaded by earlier versions remain public until re-uploaded; the dashboard labels them "Public (legacy)".
- LLM tracing (LangSmith) is **off** unless `LANGSMITH_TRACING=true`. Logs never include question text, and email addresses or phone numbers in log messages are masked.
- CORS allows only the origins listed in `CORS_ORIGINS`.
- Rate limits are per process and in memory. A multi-instance deployment needs a shared store.

This is not a claim that the system is production-secure. A security review is still needed before any public deployment.

## Deployment

`backend/Dockerfile` builds the API image (`gunicorn wsgi:app` on port 8080, non-root user). There is no checked-in hosting configuration. Deployment documentation, monitoring and backups are planned for a later phase.

## License

The original project was published as MIT-licensed, but no LICENSE file is included in this copy. Confirm the licence before redistributing.

# Student Query Chatbot → USIUBOT (in development)

This repository is being adapted into **USIUBOT**, an AI assistant for USIU-Africa.
It started as the open-source *chatbot-for-students-queries* project.

> **Status: feature-complete for local testing, not approved for deployment.** USIUBOT answers only from
> administrator-approved USIU-Africa sources and cites them; otherwise it says so and suggests the most relevant
> official page. Department enquiries, the admin dashboard and degree guidance work locally.
> **No verified USIU-Africa sources have been loaded yet**, enquiry emails are off until SMTP and department
> addresses are configured, and the university's robots.txt does not permit automated collection. Do not deploy
> it publicly or connect it to university systems without review and approval.

## What the application does today

- **Chat (web widget):** visitors ask questions without an account. Logged-in users also get a saved chat history.
- **Evidence-based answers:** questions are answered *only* from administrator-approved USIU-Africa sources (pasted page text or official PDFs), with numbered, clickable citations. Unrelated questions are politely refused; university questions that no approved source covers are reported honestly and logged for staff (never discarded just because no keyword matched). Out-of-date or conflicting sources produce warnings.
- **Direct-link fallback:** when no approved source answers a question, USIUBOT names the most specific official page from the link catalogue, says why it is relevant ("title, address or keywords match: …"), and states that it has not read it. If no page matches well enough (`FALLBACK_LINK_MIN_COVERAGE`), it says it does not know a specific page; it never makes up a link. The home page and news posts are never suggested as the answer.
- **Department enquiries:** with consent, a user sends an unresolved question to Admissions, Registrar, Marketing, Academic Programmes or General University Information. It is stored with a reference number and tracking key and moves through `pending → assigned → in progress → answered → closed`. Users are told it was *emailed* only when the email was actually sent; otherwise they are told it was recorded for staff.
- **AI provider failures:** if the language model is rate-limited, times out or fails, the reply says the AI service is unavailable (not that there is no information) and still shows the retrieved sources or suggested official pages.
- **Admin dashboard:** statistics, unanswered queries, written answers (each saved as a draft source that is only used after approval), enquiries (filter by department, status and date; assign, reply, move department), approved sources (view extracted text, approve, reject, archive, rebuild the search index), official fallback links (add, edit, mark reviewed, hide, preview which pages a question gets), programme requirements, chat history, analytics, and legacy PDF management (not used for chat answers). Every action is checked on the server against an admin token.

## Actual technology stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite 6, Tailwind CSS, React Router, Axios |
| Backend | Python 3.12, Flask 3.1 (application factory, blueprints, controllers/services/models) |
| Database | MongoDB (`users`, `queries`, `chat_history` collections) |
| Language model | **Groq**-hosted `openai/gpt-oss-120b` via `langchain-groq` (configurable with `GROQ_MODEL`; `llama-3.3-70b-versatile` is no longer offered to the project key) |
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

### Connections and the first Super Administrator
```powershell
cd backend
.\.venv\Scripts\python -m tools.connection_check --write-test   # MongoDB Atlas + Groq (no secrets printed)
.\.venv\Scripts\python -m tools.create_staff --email you@usiu.ac.ke --name "Your Name" --role super_admin
```

### Staff dashboard and roles
Sign in at `/admin`. There is no public staff registration; a Super Administrator creates accounts
(**Staff accounts**), each with a one-time temporary password that must be changed at first sign-in.

| Role | Can |
|---|---|
| Super Administrator | everything: all departments and enquiries, staff accounts, knowledge sources, dataset import, routing, official links, programme requirements, chat history, audit log |
| Department Administrator | their departments' enquiries (view, assign to their staff, move to another department, respond, resolve), department staff list, their departments' notification addresses and notes; Admissions / Academic Programmes administrators also maintain programme requirements |
| Department Staff | their departments' enquiries (or only those assigned to them), status updates, responses, internal notes, resolution, "assign to me" |

Permissions are enforced by the API on every request (`backend/utils/permissions.py`); accounts can be
deactivated (sessions end at once), sessions expire after `ADMIN_TOKEN_HOURS`, sign-out revokes the
session, repeated failed sign-ins lock an account, and every staff action is in **System activity**.
Enquiry statuses: New, Pending, In Progress, Awaiting Response, Resolved, Closed.
Reminders for stale enquiries: `python -m tools.enquiry_reminders` (schedule it daily).

### First use of the knowledge base
1. Sign in at `/admin` as a Super Administrator.
2. Open **Knowledge sources**. For each official page, enter its https usiu.ac.ke URL, title, department and date, then paste its text (or upload an official PDF). Save it as a draft.
3. Click **View** to compare the extracted text with the official page, then **Approve** or **Reject**. Only approved sources are searched and cited. **Archive** removes a source from answers without deleting it. **Rebuild search index** re-creates the search passages of approved sources and never changes the sources themselves.
4. Bulk import of files obtained with permission (run in `backend/`): `python -m tools.knowledge_sources register <file> --category ... --url ... --title ...`, then `... extract`, then `... import-registry`. This creates drafts with review flags such as "possibly outdated" or "duplicate text"; nothing is approved automatically. Details: [`backend/resources/usiubot_knowledge/README.md`](backend/resources/usiubot_knowledge/README.md).
5. Open **Official Links** to check the pages offered as fallbacks. Open each page, then **Mark reviewed**, correct it with **Edit**, or **Hide** it. Changes are stored in the database; `backend/config/official_pages.json` is not edited.

Department email (optional): set SMTP (`MAIL_SERVER`, `EMAIL_USER`, `EMAIL_PASS`) and the addresses confirmed by each office in `ENQUIRY_EMAIL_ADMISSIONS`, `ENQUIRY_EMAIL_REGISTRAR`, `ENQUIRY_EMAIL_MARKETING`, `ENQUIRY_EMAIL_ACADEMIC_PROGRAMMES` and `ENQUIRY_EMAIL_GENERAL_UNIVERSITY`. Without them, enquiries are still stored and shown in **Enquiries**.

Chat answers use a local MongoDB index, so Pinecone, Cloudinary and the "PDF Management" page are not needed for chat. Automated website crawling is disabled: USIU-Africa's robots.txt does not permit it.

### Quick local test run (no MongoDB, no external services)

```powershell
cd backend
.\.venv\Scripts\python -m tools.run_local      # API on http://127.0.0.1:5000, prints local test logins
cd ..\frontend
npm run dev -- --host 127.0.0.1 --port 5173    # open http://127.0.0.1:5173
```

`tools.run_local` uses an in-memory database (`mongomock`, from `requirements-dev.txt`), so all data is lost when it
stops. It creates a local test administrator (`admin@usiubot.local`) and test student (`test_student`) with passwords
from `LOCAL_ADMIN_PASSWORD` / `LOCAL_STUDENT_PASSWORD`, or random ones that it prints. It refuses `FLASK_ENV=production`.

## How USIUBOT answers (agents)

| Agent / service | Responsibility |
|---|---|
| University information (`services/chat_service.py`) | Orchestrates each question. Evidence, most authoritative first: (1) official pages fetched **live** (`services/live_retrieval.py`, `services/web_access.py`), (2) administrator-approved staff answers and approved sources. The model answers only from that evidence and cites it. With no verified evidence it says so ("could not verify"), never guesses, logs the question and offers unverified "places to look", an optional site-restricted search link and a staff follow-up. |
| Routing (`services/routing.py`) | Classifies questions and enquiries as Admissions, Registrar, Marketing, Academic Programmes or General University Information (keyword rules; users and staff can correct it). Detects "which course can I do?" questions and offers degree guidance. |
| Fallback links (`services/live_retrieval.py`, `services/official_links.py`) | Matches unanswered questions to the official link catalogue (file plus admin changes in the `official_links` collection) and explains each match. Links are suggestions, never evidence. |
| Unresolved enquiries (`services/enquiry_service.py`) | With explicit consent, saves the question and minimum contact details, routes it, prevents duplicates, notifies the department by email if configured, and tracks `pending → assigned → in_progress → answered → closed` (older `new`/`resolved` records are migrated at startup). |
| Admissions guidance (`services/guidance_service.py`) | Reads subjects and grades from a text-based results slip (PDF/.txt, in memory, never stored), lets the user confirm them, and compares them with programme requirements that staff have **verified** against an official page. Guidance only, never an admission decision. |

### Live website retrieval

Off by default (`LIVE_RETRIEVAL_ENABLED=false`). When enabled it fetches only https pages on exactly listed hosts
(`TRUSTED_SOURCE_HOSTS`, default `www.usiu.ac.ke`; portal hosts such as `cx.usiu.ac.ke` and login paths are always
refused), only catalogue entries marked `reviewed: true` in `backend/config/official_pages.json`, and only when
robots.txt allows the `USIUBOT` user agent. Page text is kept in a bounded in-memory cache with expiry; nothing is
written to disk. Catalogue titles, search links and snippets are never treated as evidence.

**Current blocker (2026-10-20):** robots.txt on www.usiu.ac.ke allows only major search-engine crawlers
(`User-agent: * / Disallow: /`), and the site was not reachable from the development network. Before enabling live
retrieval, review catalogue entries and run the read-only check from the deployment host:

```bash
python -m tools.live_check --fetch 2     # exit code 0 = ready
```

Note: when live retrieval is enabled, the text of fetched official pages is sent to the configured language model
(Groq) to compose the answer, in the same way as approved sources are today.

## Running the tests

```bash
cd backend
pip install -r requirements-dev.txt    # lightweight: no PyTorch needed
python -m pytest

cd ../frontend
npm test
```

The backend tests replace MongoDB, Pinecone, Cloudinary, SMTP and the language model with in-memory fakes (mocks), so they need no credentials or network access. They do not prove that a real MongoDB, Groq or SMTP server works with your credentials. The fallback-link tests (`tests/test_fallback_links_and_admin.py`) use the real link catalogue file. `tests/test_ai_integration.py` exercises the real LangChain pipeline offline. It runs only when the full AI dependencies are installed and is skipped otherwise.

## API overview

| Method & path | Access | Purpose |
|---|---|---|
| `POST /api/signup`, `POST /api/login` | public (rate-limited) | User accounts |
| `POST /api/admin/login` | public (rate-limited) | Administrator login |
| `POST /api/query` | public (rate-limited) | Ask a question (`{question, session_id?}`). Returns `answer`, `status` (`answered`, `unanswered`, `out_of_scope`, `sources_only`), `citations`, `warnings` |
| `GET/POST /api/admin/sources`, `GET/PUT /api/admin/sources/<id>`, `POST /api/admin/sources/<id>/status`, `POST /api/admin/sources/rebuild-index` | admin token | Approved-source registry (`draft`, `approved`, `rejected`, `archived`) |
| `GET/POST /api/admin/official-links`, `GET /api/admin/official-links/preview?q=` | admin token | Manage fallback links; preview the pages a question would get |
| `GET /api/chat-history` | user token | The user's own history |
| `GET /api/enquiries/options`, `POST /api/enquiries`, `POST /api/enquiries/track` | public (rate-limited) | Send an unresolved enquiry (consent required) and track it with its reference and tracking key |
| `GET /api/my-enquiries` | user token | Enquiries sent from the user's account |
| `GET /api/admin/enquiries?department=&status=&from=&to=`, `GET /api/admin/enquiries/<id>`, `POST /api/admin/enquiries/<id>/status` | admin token | View, filter (status may also be `open` or `done`; dates `YYYY-MM-DD`), assign and answer enquiries |
| `GET /api/guidance/options`, `POST /api/guidance/extract`, `POST /api/guidance/recommend` | public (rate-limited) | Degree guidance (results-slip upload is processed in memory and not stored) |
| `GET/POST /api/admin/programme-requirements`, `PUT/DELETE /api/admin/programme-requirements/<id>` | admin token | Programme entry requirements used by guidance (only verified records are used) |
| `GET /api/admin/live-retrieval` | admin token | Live retrieval settings, catalogue counts and last fetch statuses (no page text) |
| `GET /api/admin/stats`, `/chat-history`, `/query-analytics`, `/unanswered-queries` | admin token | Dashboard data |
| `POST /api/add-response`, `DELETE /api/delete-query/<id>` (also under `/api/admin/`) | admin token | Answer or delete unanswered queries |
| `GET /api/pdfs/`, `POST /api/pdfs/upload`, `DELETE /api/pdfs/<id>`, `POST /api/pdfs/rebuild-embeddings` | admin token | Legacy PDF documents (not used for chat answers) |
| `GET /health`, `GET /api/health` | public | Health check: `{status, database, timestamp}`; HTTP 503 when the database is unreachable |

Debug endpoints (`/debug/*`) exist only when `ENABLE_DEBUG_ROUTES=true` outside production, and they require an admin token.

## Security notes

- All administrative endpoints require an admin JWT. User and admin tokens are distinct and can't be swapped.
- Answers are rendered as text with a small, safe Markdown subset. HTML in answers is never executed.
- New knowledge-base PDFs are stored privately. PDFs uploaded by earlier versions remain public until re-uploaded; the dashboard labels them "Public (legacy)".
- LLM tracing (LangSmith) is **off** unless `LANGSMITH_TRACING=true`. Logs never include question text, and email addresses or phone numbers in log messages are masked.
- CORS allows only the origins listed in `CORS_ORIGINS`.
- Rate limits are per process and in memory. A multi-instance deployment needs a shared store.

## Known limitations and permissions needed

- **No approved knowledge yet.** 94 official URLs are inventoried (`backend/resources/usiubot_knowledge/metadata/`), but 0 pages and 0 PDFs have been collected, and 0 sources are approved in the repository. Until staff add and approve sources, most questions get the honest fallback with a suggested link.
- **Collection needs university permission.** www.usiu.ac.ke's robots.txt disallows automated clients, so pages are recorded as link-only. Obtain written permission (or copies of the content from the offices) before collecting.
- **Fallback links are unreviewed.** 77 catalogue pages, 0 marked reviewed. Staff should check them in **Official Links**.
- **Email is off** until SMTP credentials and confirmed department addresses are set.
- **AI answers need a Groq API key** (`GROQ_API_KEY`). Without it, approved sources are shown as "sources only".

This is not a claim that the system is production-secure. A security review is still needed before any public deployment.

## Deployment

`backend/Dockerfile` builds the API image (`gunicorn wsgi:app` on port 8080, non-root user). There is no checked-in hosting configuration. Deployment documentation, monitoring and backups are planned for a later phase.

## License

The original project was published as MIT-licensed, but no LICENSE file is included in this copy. Confirm the licence before redistributing.

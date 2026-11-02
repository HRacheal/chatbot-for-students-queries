# USIUBOT — Final System Implementation Report

Date: 2026-11-02 · Branch: `usiubot-development` (all changes uncommitted; nothing committed or pushed)

This report covers the integration of MongoDB Atlas and Groq, the role-based staff login, the
university-wide staff dashboard with departmental enquiry management, the import of the
university dataset into Atlas, and the verification of the public chatbot, results-slip
guidance and notifications. The existing application was extended, not replaced: Flask backend,
React frontend, BM25 retrieval, the source approval workflow and citations are kept.

**Current state in one paragraph.** MongoDB Atlas (`chatbot_db`) and Groq (`openai/gpt-oss-120b`)
are connected and tested. The dataset is imported: **586 draft sources, 0 approved**. The chatbot,
the dashboard, roles and department isolation were verified against the real Atlas cluster and the
real Groq API. The chatbot will not answer from the dataset until an administrator **approves**
sources, and nobody can sign in to the dashboard until **you create the first Super Administrator**
(it needs your own password, see §16).

---

## 1. What already existed

| Area | State before this work |
|---|---|
| Public chatbot | Answers only from **approved** sources (local BM25 index in MongoDB) with citations; external (KUCCPS/CUE) records labelled "not USIU-Africa policy"; "could not verify" + fallback official links + enquiry offer when no evidence; AI-unavailable state kept separate. |
| Knowledge sources | Draft → approved / rejected / archived workflow, dataset import (drafts only), retrieval test, index rebuild. |
| Department routing | 9 departments (Admissions, Registrar, Finance, Academic Programmes, Marketing, Student Affairs, ICT, Library, General University Information), keyword classifier, per-department delivery addresses and unpublished contacts. |
| Enquiries | Submission with consent, dedupe, reference + tracking key, statuses `pending/assigned/in_progress/answered/closed`, one admin list. |
| Authentication | Public user sign-up/login; **one** bootstrap admin from `ADMIN_EMAIL`/`ADMIN_PASSWORD`; JWT bearer tokens; no staff accounts, roles, departments, logout/revocation or audit log. |
| Admin UI | Single dashboard with tabs; counts only; no charts; no departmental views. |
| Results-slip guidance | Upload (PDF/TXT, in memory, never stored) → editable grades → deterministic comparison with admin-**verified** programme requirements; disclaimer; no OCR for images. |
| Email | SMTP service; department notification for new enquiries only; delivery claimed only when actually sent. |

## 2. What was implemented

**Backend**
- `services/staff_service.py` — staff accounts (collection `staff`): bcrypt hashing, temporary password + forced change at first sign-in, lockout after repeated failures, activation/deactivation, password reset, staff directory. No public registration endpoint.
- `utils/auth.py` (extended) — role-aware staff tokens (`super_admin`, `department_admin`, `department_staff`) with `jti` and `token_version`; `staff_required(roles=...)`; logout revocation (`revoked_tokens`, TTL index); account state, role and departments re-read from MongoDB on **every** request.
- `utils/permissions.py` — all role/department rules in one place.
- `routes/staff_routes.py` — `/api/staff/login|logout|me|password|options|accounts|accounts/<id>|accounts/<id>/reset-password|directory|audit`.
- `services/audit_service.py` — audit log of sign-ins (incl. failures), sign-outs, account changes, enquiry actions and every successful administration change. No passwords, tokens, contact details or answer text are recorded.
- Enquiries — statuses **New, Pending, In Progress, Awaiting Response, Resolved, Closed** (legacy `assigned → in_progress`, `answered → resolved` migrated at startup, nothing deleted); department scoping (other departments' enquiries return 404); assignment to staff, "assign to me", internal notes, staff response, resolution details, search and filters; `GET /api/admin/dashboard` with real aggregated statistics and a daily trend; optional `user_group`.
- Notifications on assignment, staff response and resolution, plus stale-enquiry reminders (`tools/enquiry_reminders.py`); every attempt logged as `sent / failed / not_configured / disabled`.
- MongoDB failure handling: understandable start-up errors, **503 "database temporarily unavailable"** during outages.
- Tools: `tools/connection_check.py`, `tools/create_staff.py`, `tools/enquiry_reminders.py`; `tools/run_local.py` creates synthetic in-memory department accounts.
- `tests/test_live_integration.py` — opt-in tests against the **real** Atlas cluster and Groq API in a temporary database that is dropped afterwards (`USIUBOT_LIVE_TESTS=1`).

**Frontend** (React + Tailwind, no new dependencies)
- Staff portal sign-in with forced password change; no registration.
- Dashboard shell: sidebar with **Overview, Assigned to me, All enquiries, one entry per department (all 9)**, and an Administration section shown according to permissions; all earlier tools kept.
- Overview: summary cards, received/resolved trend chart (tooltip, legend, table view), status and department charts, "awaiting attention" list.
- Enquiry management: search/filters, detail with contact info, original question, received time, status, assignment, move department, response, resolution, internal notes, history and notification log.
- Staff accounts (create/edit/deactivate/reset; read-only for department admins) and System activity (audit log).
- Public landing page (who USIUBOT serves, topics, citations, human follow-up, staff sign-in link); chat widget unchanged; enquiry form asks optionally "I am a…".

## 3. Problems discovered and corrections made

| Problem | Cause (verified) | Correction |
|---|---|---|
| Groq "responds but the text is empty" | `openai/gpt-oss-120b` is a **reasoning model**: hidden reasoning tokens count against `max_tokens`. The connection checker allowed 10 tokens; the model used 8 for reasoning and stopped (`finish_reason=length`) before writing any visible text. The API and parsing were correct. | Checker now allows 300 tokens and fails clearly on an empty reply. The app sends `reasoning_effort="low"` for gpt-oss models (configurable `GROQ_REASONING_EFFORT`, `GROQ_MAX_TOKENS`). An empty reply is now raised as a model failure (`EmptyModelReply` → "AI unavailable" + relevant approved sources) instead of being treated as "no evidence". |
| Citations written as `【2】` | gpt-oss uses its own citation brackets, which the `[n]` parser ignored — so every retrieved source was listed instead of only the cited ones, and markers were not shown as references. | `normalise_citation_markers` rewrites `【2】`, `【2†L1-L4】`, `［2］` to `[2]` before citations are built. Verified with real answers. |
| An empty `GROQ_MODEL=` would crash every answer (pydantic `ValidationError`) | `os.getenv("GROQ_MODEL", default)` returns `""` when the line exists but is empty. Found while testing. | Empty values fall back to `openai/gpt-oss-120b` in config and in the chat service. |
| `llama-3.3-70b-versatile` unavailable | No longer offered to the project key (Groq `/models`). | Default model `openai/gpt-oss-120b` (documented, overridable). |
| `six-1.17.0` metadata error | **Could not be reproduced in the project environment**: in `backend/.venv` the `six-1.17.0.dist-info` METADATA parses, all RECORD hashes match, `pip check` reports no broken requirements, and all 94 distributions have valid metadata. The global user site-packages (`%APPDATA%\Python\Python312\site-packages`, not used by the project) contains leftover `~…` folders from interrupted installs (`~umpy`, `~orch`, `~andas`, …), which make pip print "invalid distribution" warnings when the **global** Python is used. | Smallest safe repair: `six==1.17.0` reinstalled in place in the venv with `--no-deps --force-reinstall` (same version, no other package touched); re-verified. The global leftovers were **not** deleted (outside the project; see §13). Always use `backend\.venv\Scripts\python`. |
| One existing test expected an empty model reply to be "unanswered" | That behaviour is what hid the gpt-oss fault as a false knowledge gap. | Test updated to expect "AI unavailable" with the relevant approved sources (`tests/test_chat.py::test_reply_without_text_blocks_is_not_presented_as_an_answer`). |

Other improvements: department administrators manage their own departments' notification addresses and notes; Admissions / Academic Programmes administrators manage programme requirements; the first resolution time is kept when an enquiry is later closed; dashboard figures come from MongoDB aggregations.

## 4. What remains incomplete
1. **No staff account exists in `chatbot_db`** and `backend/.env` has no bootstrap admin, so the dashboard cannot be used until you run `tools.create_staff` (§16.1). I did not create one because it needs your password.
2. **0 of 586 sources are approved**, so the public chatbot currently answers no dataset questions: it says it cannot verify, links official pages and offers an enquiry. Administrators must review and approve sources (§15).
3. Email notifications are implemented but **untested with real credentials**: no SMTP account or authorised departmental/test address is configured. Every notification is currently recorded as `not_configured`; nothing claims delivery.
4. Results-slip images/scans are not read (no OCR — adding one is a new dependency). **No programme requirements are verified**, so no programme recommendations are given (the tool says so, §10).
5. 54 department contacts were imported **unpublished**; they are not shown to students until the university confirms them.
6. Rate limiting and token-revocation caching are per process (fine for one server).

## 5. MongoDB connection and import results
`python -m tools.connection_check --write-test` (2026-11-02):
```
MongoDB: mongodb+srv://***@usiubot-database.***.mongodb.net  database 'chatbot_db'
  OK    ping (1953 ms)
  OK    write test (insert + delete)
```
- The application connects to **`chatbot_db`** (`MONGO_DB_NAME`) and creates its collections and indexes at start-up: `audit_log, chat_history, department_routing, enquiries, official_links, programme_requirements, queries, query_log, revoked_tokens, source_chunks, sources, staff, users` (unique staff email, TTL on revoked tokens, verified by the live tests).
- **Live tests on Atlas** (`tests/test_live_integration.py`, temporary database, dropped afterwards): 3 passed — collections/indexes; staff accounts, roles, department isolation, enquiry create → assign → note → resolve, dashboard statistics from real records, logout revocation, audit log; Groq answer from approved sources only.
- **Dataset import into `chatbot_db`** — see §15 for the counts. After import: `sources` 586 (all `draft`), `department_routing` 9 (54 contacts, 0 published), every other collection empty. Test databases (`usiubot_itest_*`, `usiubot_e2e_*`) were dropped; `chatbot_db` is the only application database on the cluster.

## 6. Groq test results
- Connection check: `OK reply in 969 ms: 'ready' (reasoning_effort=low)`.
- Diagnosis of the empty reply (same prompt): `max_tokens=10` → content `''`, `finish_reason=length`, 8 of 10 tokens were reasoning; `max_tokens=300` → `'ready'`, `finish_reason=stop`.
- **Real-data chatbot test** (real Atlas cluster, real Groq, the imported dataset copied into a throwaway database where 5 sections were approved **only for the test**; `chatbot_db` was read-only and unchanged: 586 sources / 0 approved before and after):

| Question | Result |
|---|---|
| How do I apply to USIU-Africa? | `answered`, step-by-step answer citing "How to Apply – USIU-Africa" (https://www.usiu.ac.ke/how-to-apply/) |
| Is there accommodation available for students at USIU-Africa? | `answered`: on-campus hostels (first-year and international students, shared rooms…) citing the FAQ and Housing & Accommodation pages |
| What does the USIU-Africa library offer students? | `answered`, citing "USIU-Africa Student Handbook — 7.1 Library and Information Center", **page 27** |
| What are the transcript requirements for admission? (section exists only as a **draft**) | `unanswered` — draft not used; points to the official "Admission Requirements" page; enquiry offered |
| What is the exact MBA tuition fee for the 2027 intake? | `unanswered` — "I won't guess"; question logged; enquiry submitted → "recorded for **Finance** … it has not been emailed"; dashboard total 1, awaiting attention 1 |

No answer cited a non-approved source (checked for every citation).

## 7. Login and authentication test results
Passing (`tests/test_staff_rbac.py`, and live on Atlas): no public staff registration; temporary password stored only as a bcrypt hash; forced password change (other staff endpoints answer 403 `password_change_required`); weak passwords refused; identical error for unknown email and wrong password; lockout and unlock; logout revokes the session (live: `/api/staff/me` → 401 after logout); deactivation and password reset end sessions immediately; expired tokens refused; a Super Administrator cannot deactivate or demote themselves. Local HTTP smoke test: login 200 → dashboard 200 → logout 200 → dashboard 401.

## 8. Role and department permission test results
Passing (offline and live on Atlas): department admins/staff get 403 on knowledge sources, dataset import, chat history, official links, staff creation, audit log, unanswered-question management and PDFs; Admissions staff see only Admissions enquiries and get **404** for a Registrar enquiry, while Registrar staff see only Registrar; "assigned only" staff see only their assignments; department admins assign only to their department's staff; department staff can only take an enquiry themselves; only administrators move enquiries between departments; department admins change only their own departments' addresses/notes; programme requirements are limited to Super Administrators and Admissions/Academic Programmes administrators; public visitors cannot reach any `/api/admin` or `/api/staff` data (401) and the `/admin` page requires a staff session.

## 9. Dashboard verification
- All nine departments appear in the sidebar and have scoped views (Admissions, Registrar, Marketing, Finance, Academic Programmes, Student Affairs, ICT, Library, General University Information).
- Live on Atlas: enquiries were created, assigned, annotated and resolved; the Super Administrator dashboard showed total 2, resolved 1, today's trend received 2 / resolved 1; the Admissions staff dashboard showed only its own enquiry (total 1).
- Offline: figures match the database (totals by status, unresolved, awaiting attention, unresolved chatbot questions, 7/30-day trends), search and filters, notes never visible to enquirers, workflow New → … → Closed with history, resolution requires a response or resolution details, notification log, reminders. Frontend tests render the charts, role-dependent screens and the sign-in page.

## 10. Results slip and programme recommendation results
- Text and PDF extraction work in memory; the file is never stored ("The file was not stored."); identifiers (name, index number) are not returned; grades are shown for the visitor to correct before comparison. Test slip (synthetic) → 7 subjects + mean grade B+ extracted correctly.
- Scanned images: not read (no OCR); the visitor is asked to type the grades. This is stated in the interface, not hidden.
- Comparison runs only against **verified** programme requirements. `programme_requirements` in `chatbot_db` is empty, so the response is `status: no_verified_requirements` with the message *"USIUBOT does not yet have verified programme entry requirements, so it cannot recommend programmes. These official pages may list programmes and requirements (not checked)"*, three official links marked unverified, and the disclaimer *"This is guidance only, not an admission decision. Only USIU-Africa Admissions can confirm eligibility."* No requirement was invented.
- `tests/test_guidance.py` passes (extraction, validation, deterministic comparison with reasons, unverified requirements ignored, rate limiting, no storage).

## 11. Test results

| Suite | Command | Result |
|---|---|---|
| Backend (all) | `cd backend; .venv\Scripts\python -m pytest` | **688 passed, 0 failed, 3 skipped** (the 3 live tests, run separately below), 1 third-party deprecation warning, 2 min 59 s |
| Live Atlas + Groq | `$env:USIUBOT_LIVE_TESTS="1"; .venv\Scripts\python -m pytest tests/test_live_integration.py -v` | **3 passed** (50.7 s) — skipped in the normal run |
| Groq regression (offline) | `tests/test_ai_integration.py`, `tests/test_service_failures.py` | 17 passed (5 new: marker normalisation, marker variants, empty reply, reasoning effort/model fallback, connection-check failure without leaking the key) |
| Connection check | `python -m tools.connection_check --write-test` | All checks passed |
| Dataset dry run + import + re-run | `python -m tools.import_dataset [--apply --contacts]` | see §15 |
| Real-data chatbot E2E | throwaway Atlas database + real Groq | see §6 |
| Frontend tests | `npm test` | **62 passed** (6 files) |
| Frontend lint | `npm run lint` | 0 errors, 0 warnings |
| Production build | `npm run build` | succeeds |

## 12. Frontend notes
No frontend changes were needed for the Groq fixes: citation markers are normalised on the server, and the "AI unavailable" state already existed in the chat window.

## 13. Security issues or warnings
- `backend/.env` holds live secrets (Atlas URI, Groq key, `SECRET_KEY`). It is git-ignored; no secret was printed in any log or test output (masked checks only).
- Bearer tokens are kept in `localStorage` (existing design); an XSS bug would expose a session. httpOnly cookies + CSRF protection would be stronger for production.
- Locked accounts answer "locked" (429), revealing that the email exists once it has been locked.
- Rate limits and revocation caching are per process.
- Prefer real staff accounts over the bootstrap `ADMIN_EMAIL`/`ADMIN_PASSWORD` admin (currently not set — good).
- Use HTTPS in production.
- Global Python (not the project): leftover `~…` folders in `%APPDATA%\Python\Python312\site-packages` from interrupted installs. They do not affect USIUBOT. To clean them, close all Python processes and delete only the folders whose names start with `~`.
- Atlas: keep Network Access limited to the addresses that need it.

## 14. Commands to start the backend and frontend
```powershell
# Backend (uses backend/.env → Atlas chatbot_db + Groq)
cd C:\Users\Admin\Downloads\chatbot-for-students-queries-1\backend
.\.venv\Scripts\python -m tools.connection_check --write-test
.\.venv\Scripts\python app.py                       # http://127.0.0.1:5000

# Frontend
cd C:\Users\Admin\Downloads\chatbot-for-students-queries-1\frontend
npm run dev                                         # http://localhost:5173  (staff: /admin)

# Local trial without Atlas (in-memory data, synthetic accounts printed in the console)
cd ..\backend; .\.venv\Scripts\python -m tools.run_local
```

## 15. Dataset import and source review
| Run | Result |
|---|---|
| Dry run against Atlas | 817 chunks read → **586 sections**, 0 duplicate chunks; outcome **586 would be created**; 0 refused; 0 approved by import; dataset validation 0 blocking failures, 1 warning; nothing written |
| `--apply --contacts` | **586 draft sources created**, 0 approved; categories 01:299, 02:67, 03:82, 04:98, 05:26, 06:13, 07:1; 54 contacts copied unpublished into 9 departments; no delivery addresses touched |
| Dry run again (duplicate detection) | **586 unchanged**, 0 created, 0 approved |

Verified in Atlas: 586 sources, all `draft`, `verification_status: pending_verification`; by department — general_university 116, student_affairs 112, admissions 111, library 72, finance 71, academic_programmes 67, registrar 31, ict 6; 454 with an official URL and 132 Student Handbook sections citing the document file instead; all 586 keep `document_id`, `section_id` and publisher, 448 a heading path, and the 138 sections taken from PDFs keep `page_start/page_end` (web pages have no page numbers); 188 carry their known-issue records and 55 a user-facing warning; 3 external (non-USIU) sources labelled as such. The searchable index (`source_chunks`) is empty by design until sources are approved — the 817 chunks become searchable as their sections are approved.
The one validation warning: two register issues (V11, W15) are not attached to any record (informational).

Review steps:
1. Sign in at `/admin` → **Knowledge sources**; filter by category/department, **View** each draft against its official page or document page, then **Approve** or **Reject** (bulk actions exist). Leave sources with unresolved conflicts or outdated information in draft.
2. **Rebuild search index**, then try questions in the dataset search box and in the chat.
3. **Department routing**: enter confirmed delivery addresses; tick "Show to students" only for contacts the university has confirmed.
4. **Staff accounts**: create department administrators and staff.

## 16. Credentials or confirmations still required
1. **First Super Administrator** (you run this; the password is typed into a hidden prompt, never into the chat):
   `cd backend; .\.venv\Scripts\python -m tools.create_staff --email <your work email> --name "<Your Name>" --role super_admin`
2. Review and approval of the 586 draft sources (§15).
3. The list of staff, their roles and departments.
4. SMTP account for USIUBOT (`MAIL_SERVER`, `MAIL_PORT`, `EMAIL_USER`, `EMAIL_PASS` in `backend/.env`), **confirmed** departmental addresses (Routing page or `ENQUIRY_EMAIL_<DEPARTMENT>`), and an **authorised test address** — then a real send test before relying on email.
5. University confirmation of the 54 imported contacts before publishing them.
6. Verified programme entry requirements (from official USIU-Africa pages) for degree guidance.
7. Confirmation that `openai/gpt-oss-120b` is acceptable as the Groq model.
8. A data-retention decision for enquiries and audit logs.

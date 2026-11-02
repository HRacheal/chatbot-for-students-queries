# USIUBOT — Dataset Integration Report

Date: 2026-11-02 · Branch: `usiubot-development` · Nothing committed or pushed.

**Status in one line:** the dataset is wired into the existing chatbot (same Flask app, same MongoDB
source registry, same BM25 index) and works end to end against an in-memory test database. It has **not**
been imported into a real MongoDB, and no live AI answer has been generated. `backend/.env` has no
`MONGO_URI` and no `GROQ_API_KEY`, so neither service was configured or tested. The chatbot is therefore
**not** fully operational yet.

## 1. Backend changes

| File | Change |
|---|---|
| `services/dataset_import.py` (new) | Reads `usiubot_datasets/*/(official\|external)/*knowledge_chunks.json`. Groups chunks by section and creates or refreshes one **draft** source per section (`url_normalized = dataset:<section_id>`). Attaches open register issues and review flags, and suggests a department. Also provides a dry run, a status report per category/status/origin, and the `TEST_DATASET` marker for synthetic fixtures. |
| `services/sources.py` | Nine departments, with Finance separate. Adds `CATEGORIES` and `DATA_ORIGINS`. `LocalIndex.search` and `SourceRegistry.retrieve` gain a `categories` filter. Dataset chunks are indexed as they are, with chunk id, page and heading metadata. `is_citable` handles external sources (external domains only) and PDF sections without a URL (cited by file + page). Test records are excluded from retrieval outside test mode. New methods: `upsert_dataset_source` (idempotent, never approves), `archive_missing_dataset_sources` and `bulk_set_status`. The source list gains category/origin/kind/flag/title filters. The text, URL and type of dataset sources can't be edited in the form. |
| `services/chat_service.py` | New system-prompt rules: label external sources; mention known issues; never present payment details as confirmed; never state facts not in the sources. The prompt context shows origin, pages and open issues. Citations gain category, origin/external, publisher, PDF file, page range, section heading, collection date and academic year. Sources-only replies include the approved passages verbatim. New warnings cover external sources, unresolved conflicts, outdated and inconsistent items, and payment details. Unresolved questions are logged with their suggested department and return its label and any published contacts. |
| `services/department_routing.py` (new) | `department_routing` collection holding, per department: staff delivery addresses (admin-entered only), published contacts (copied from the dataset as printed, unpublished by default), `publish_contacts` and notes. |
| `services/routing.py` | Keyword routing for the nine departments. Fee, payment, refund, bank and paybill terms now route to **Finance**; library, ICT and Student Affairs terms to their own departments. |
| `services/enquiry_service.py` | Staff recipients come from the routing settings first, then `ENQUIRY_EMAIL_<DEPT>`. |
| `routes/dataset_routes.py` (new) | Admin-only routes: `GET /api/admin/dataset/status`, `POST /api/admin/dataset/import` (`dry_run`), `GET /api/admin/dataset/search?q=&category=`, `GET /api/admin/routing`, `PUT /api/admin/routing/<dept>`, `POST /api/admin/routing/import-contacts` and `POST /api/admin/sources/bulk-status`. |
| `controllers/source_controller.py`, `routes/source_routes.py`, `app.py`, `models/models.py`, `services/live_retrieval.py` | Wiring, list filters, `department` on logged queries, and shared department labels. |
| `config/config.py`, `.env.example` | New settings: `EXTERNAL_SOURCE_DOMAINS` (kuccps.net, cue.or.ke, knqa.go.ke), `DATASET_DIR`, `ALLOW_TEST_SOURCES` (on only in `TestingConfig`; refused in production) and `ENQUIRY_EMAIL_FINANCE/STUDENT_AFFAIRS/ICT/LIBRARY`. Validation rejects an official domain listed as external. |
| `tools/import_dataset.py` (new) | Command line: dry run by default, `--apply` writes drafts, `--contacts` copies published contacts (unpublished). |
| `README.md` | New "USIUBOT dataset" section. |

## 2. Frontend changes

| File | Change |
|---|---|
| `components/Citations.jsx` | Links official pages; links external pages only on listed external domains, with an **External: &lt;publisher&gt;** badge and a "not USIU-Africa policy" note. PDFs show `file, pages x-y, section "…"` and "no public link". Also shows collection date and academic year, the passages in sources-only replies (as text), and highlighted payment/external warnings. |
| `components/UnverifiedHelp.jsx` | "Recorded as unresolved for the &lt;Department&gt; office", plus contacts only if an admin has published them (plain text, no links). |
| `components/DatasetImport.jsx` (new) | In the Sources tab: dataset status per category and status, dry run, import/refresh as drafts, the import report, and a retrieval test with a category filter. |
| `components/SourceManagement.jsx` | Filters (status, kind, category, origin, department, flags, title). Select-all/multi-select with bulk approve, reject, archive or back-to-draft, each confirmed. Dataset metadata (category, file, pages, passages) in the list. The detail view adds origin, document, pages, collection and publication dates, verification status and open register items. New flag labels. |
| `components/RoutingManagement.jsx` (new) and `Admin.jsx` | New **Routing** tab: staff addresses, notes, contacts copied from the dataset, and a "show to students" switch. |
| `lib/citations.js`, `lib/workflow.js`, `lib/api.js`, `.env.example` | Nine departments, category names, `citationLink`/`citationLocation`, `VITE_EXTERNAL_SOURCE_DOMAINS`, and API calls for the above. |

## 3. How the dataset is loaded and searched

1. **Import (admin or CLI).** Each of the dataset's 817 chunks is read with its category folder and origin folder (`official`/`external`).
   - Chunks are grouped into **586 sections**: 583 official (138 PDF, 445 web) and 3 external.
   - The other 17 of the dataset's 603 sections have no chunks, by design: repeated fee-table headers, form lists and empty headings.
   - Passages repeated across sections are indexed once.
   - By category: 01: 299 · 02: 67 · 03: 82 · 04: 98 · 05: 26 · 06: 13 · 07: 1 · 08: 0. Category 08's FAQ pairs and open questions are registers, not chunk files.
2. **Drafts.** Every section becomes a draft source and nothing is indexed yet.
3. **Approval.** Once an admin approves a section, its chunks go into `source_chunks` with `category` and `meta` (chunk id, pages, heading). The existing BM25 `LocalIndex` (same tokeniser, synonyms and thresholds) searches them alongside manually added sources.
4. **Retrieval re-checks** approval, citability and the test-record guard on every query. A `categories` filter is available (used by the admin search; chat searches all categories).
5. **Refresh.** After rebuilding the dataset, import again. In the in-memory check, a second import reported 586 unchanged.
   - Changed text: an approved section returns to draft and is removed from the index.
   - Removed sections are archived.
   - Admin edits to title and department are kept.

## 4. Citations

- **Web:** the page URL (link), page title — section heading, department, collection date.
- **PDF:**
  - The Academic Calendar links to its official URL.
  - The Student Handbook has no working public URL, so it is cited as `Student-Handbook.pdf, page N, section "…"` without a link.
  - Pages come from the retrieved chunks themselves.
- **External:** labelled with the publisher and "not USIU-Africa policy", to both the model and the user.
- **Conflicts and warnings:**
  - Shown to students: open, unresolved or partially resolved **medium/high** items of type conflict, outdated or inconsistency.
  - Admin-only: everything else, in the source detail view.
  - Bank, paybill and SWIFT sections always carry "confirm the account details with the Finance Office first".
- **No reliable answer:** the question is logged as unanswered, with its suggested department, and the student gets the existing enquiry form with that department preselected.

## 5. Admin approval

Nothing is auto-approved: the import report always shows `approved_by_import: 0`. The workflow:

1. Sources tab → *USIUBOT dataset* → **Check for changes (dry run)** → **Import / refresh as drafts**.
2. Filter (e.g. *Kind: From the dataset*, *Category: 04*, *Warnings: With review flags*).
3. Open sources and compare the text with the original page or PDF page. Check the flags and register items.
4. Select and **Approve selected**. Each approval still runs the normal checks: the text is present, and the source is citable by an allowed URL or by PDF file + page.
5. Use the retrieval test to see what the chatbot would cite.

**Recommendation:** approve in batches by category, starting with low-risk sections. Leave sections flagged `payment details`, `unresolved conflict` or `possibly outdated` until the relevant office confirms them.

## 6. Routing

- **Departments:** Admissions, Registrar, **Finance (separate)**, Academic Programmes, Marketing, Student Affairs, ICT, Library, General University Information.
- **Dataset-only offices:** Careers, Alumni and Security in the dataset map to General University Information. Financial Aid maps to Admissions, matching the handbook's "Department of Admissions and Financial Aid".
- **Keyword routing:** questions about fees, payment, refunds and bank accounts go to Finance.
- **Dataset sections** get a suggested department by category and document. Admins can change it before approval.
- **No email addresses or numbers are invented.** Staff delivery addresses are empty until an administrator enters them (Routing tab) or sets `ENQUIRY_EMAIL_<DEPT>`. Without an address, enquiries are still listed in the Enquiries tab.
- **Published contacts:** **Copy published contacts from the dataset** fills them exactly as printed, with their source and issue ids (e.g. W05 for conflicting admissions numbers). They are **hidden from students** until an administrator ticks "Show to students". Copied contacts are never used to deliver enquiries.

## 7. Features preserved

All of these are unchanged and covered by the existing tests, which still pass:

- chat, with general chat, follow-ups and session memory
- the live tier (still off)
- staff answers
- PDF management
- chat history with citation re-checks
- the query log and analytics
- the enquiries workflow: consent, duplicates, tracking, admin status, email notification
- results-slip upload and degree guidance
- programme requirements
- official links
- admin login and security controls: JWT, rate limits, CORS, URL allow-lists, no HTML from the model

Deliberate behaviour changes:

- library, ICT, housing and health questions now route to their own departments;
- fee questions now route to Finance;
- `finance` is now a valid department. Ten lines in five existing test files were updated for this: library questions now expect `library`, and the "invalid department" examples use `bursary` instead of `finance`.

## 8. Tests

| Suite | Result |
|---|---|
| Backend full suite (`pytest tests`) | **643 passed, 0 failed**, 1 warning (the existing deliberate short-key JWT test), 3 min 4 s. That is the previous 601 plus 42 new. |
| New `tests/test_dataset_integration.py` | 42 passed. Synthetic `TEST_DATASET` fixture in a temp folder; the real dataset is read in a dry run only. Covers: loading, dry run, metadata, admin-only access, approval gate, BM25 retrieval, category filter, bulk approval, PDF page citations, URL citations, external labelling, conflict vs low-severity warnings, payment warning, sources-only passages, unresolved logging + Finance routing, nine-department routing, configurable routing and contact publishing, admin address overriding env, duplicate prevention, idempotent re-import, refresh to draft, archiving, kept admin edits, the test-data guards, external-domain requirement, production config checks. |
| Frontend `vitest` | 55 passed (46 existing + 9 new in `DatasetCitations.test.jsx`) |
| Frontend `eslint .` | clean |
| Frontend `vite build` | succeeded (built into a scratch folder; `dist/` not touched) |
| Dataset `usiubot_datasets/tests` | 10 passed |
| Dataset validator | 0 blocking failures, 1 warning (V11, W15 only in the register). The "app files unchanged" check is now informational, since app changes are authorised. |

**Not tested:**

- a real MongoDB (Atlas or local);
- Groq / live AI answers (only the fake model and the "sources only" path were exercised);
- SMTP delivery;
- the UI in a browser (components were tested by server-side rendering).

## 9. Still needed

**Configuration**

- `MONGO_URI` and `GROQ_API_KEY` in `backend/.env`. Then run the import and test real answers.
- SMTP, if email notifications are wanted.

**University confirmation**

- Bank, M-PESA and SWIFT details: V01–V03, W26.
- Conflicting admissions telephone numbers: W05.
- The Student Handbook's public URL and edition date (the candidate URL returns 404).
- Open conflicts in the register, e.g. fee and date discrepancies.
- Departmental staff addresses for enquiry delivery.
- Whether the published contacts may be shown to students.

**Review work**

- An administrator must review and approve the 586 draft sections. Nothing answers from the dataset until then.

**Possible development**

- Category-aware ranking in chat (currently all categories are searched).
- Answering from category 08's FAQ pairs.
- A role-based reviewer account (the app still has a single admin).
- Browser end-to-end tests.

## 10. Windows PowerShell

```powershell
cd C:\Users\Admin\Downloads\chatbot-for-students-queries-1

# Backend tests (about 13-15 minutes)
cd backend
$env:PYTHONDONTWRITEBYTECODE = "1"
.\.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider
# Only the dataset integration tests
.\.venv\Scripts\python.exe -m pytest tests\test_dataset_integration.py -q -p no:cacheprovider

# Frontend tests, lint
cd ..\frontend
npx vitest run
npx eslint .

# Dataset tests and validator
cd ..
.\backend\.venv\Scripts\python.exe -m pytest usiubot_datasets\tests -q -p no:cacheprovider
.\backend\.venv\Scripts\python.exe usiubot_datasets\extraction_scripts\validate_dataset.py

# Try it locally without MongoDB (in-memory database; everything is lost on exit; prints test logins)
cd backend
.\.venv\Scripts\python.exe -m tools.run_local
# second window:
cd ..\frontend
npm run dev
# Admin dashboard -> Sources -> "Import / refresh as drafts" -> review -> approve -> ask in the chat.
# Without GROQ_API_KEY the chat returns "sources only" replies with the cited passages.

# Once backend\.env has MONGO_URI (and SECRET_KEY etc.):
cd ..\backend
.\.venv\Scripts\python.exe -m tools.import_dataset            # dry run
.\.venv\Scripts\python.exe -m tools.import_dataset --apply    # drafts only
```

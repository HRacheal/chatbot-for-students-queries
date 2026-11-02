# USIUBOT knowledge sources (staging area)

Candidate official USIU-Africa pages and documents, organised for **administrator review**. Nothing here is
uploaded to Cloudinary, indexed in Pinecone or used by the chatbot until it has been imported into the
source registry as a *draft* and approved by an administrator.

| Folder | Contents |
|---|---|
| `admissions/` | Admission guides, requirements, application, scholarships, fees |
| `registrar/` | Academic calendars, registration, transcripts, graduation, handbook |
| `marketing/` | Brochures, university profile, student life, news, partnerships |
| `academic_programmes/` | Academic catalogue, programme and degree requirements |
| `general_university/` | History, contacts, schools, facilities, FAQs |
| `pending_review/` | Category or authority unclear (must be given a department before import) |
| `metadata/` | `source_inventory.json`, `SOURCE_REPORT.md`, `IMPORT_REPORT.md`, robots.txt record, discovery seeds |

Downloaded files and their extracted text (`*.extracted.txt`) are **git-ignored**: university documents
are not committed. Only the metadata and reports (titles, URLs, dates, hashes, statuses) are tracked.

Status (2026-10-20): **no documents are stored yet.** The site's robots.txt (last read 2026-10-19) disallows
automated clients, and on 2026-10-20 the site could not be reached from this network at all. See
`metadata/IMPORT_REPORT.md`.

## Workflow (from the `backend` folder)

1. An authorised person opens the official page in a browser and saves it ("Save page as" → *Web page,
   HTML only*), or downloads the PDF. Forms and anything containing personal data are never used.
2. Register it with its official URL, title, the date shown on it and the date it was obtained:

   ```bash
   python -m tools.knowledge_sources register "C:/path/How to Apply.html" --category admissions \
       --url "https://www.usiu.ac.ke/how-to-apply/" --title "How to Apply" \
       --published 2026-03 --retrieved 2026-10-21 --note "browser download by <name>"
   ```

3. Extract the text and set review flags: `python -m tools.knowledge_sources extract`
4. Import into the source registry as drafts (uses the backend `.env` database):
   `python -m tools.knowledge_sources import-registry`
5. In the admin **Sources** screen, compare each draft with the official page, check its review flags
   (no date, possibly outdated, duplicate text, form / personal data, extraction problems, instructions
   aimed at an AI) and approve it only if it is correct and current.

`python -m tools.knowledge_sources download` fetches pages and PDFs only if robots.txt allows this tool.
Forms and duplicates are never imported; other domains (e.g. the student portal) are never fetched.

## Hybrid collection: content where permitted, official links otherwise

Each inventory entry has a **collection status** (`download_status`), kept separate from its review
status. A downloaded source is never approved automatically.

| Status | Meaning | Retried |
|---|---|---|
| `downloaded`, `registered_manually` | Content stored (then `extract` → `import-registry` → admin approval) | no (stored content is kept) |
| `robots_disallowed` | robots.txt does not allow this tool | next run |
| `site_unreachable`, `timeout`, `server_error` | Transient network/server problem | up to `MAX_ATTEMPTS` (2) per run, then next run |
| `access_denied` (403), `login_required` (401, sign-in redirect or password form) | Restricted; never fetched with credentials | next run |
| `not_found` (404/410), `empty_content`, `invalid_file` (wrong type or too large) | Not usable | next run |
| `duplicate` | Same canonical URL or same text as another source | no |
| `archived` | Withdrawn with `archive URL --reason ...` | never |

Sources that are not collected keep their official URL and get `link_only: true` together with
`failure_reason` and `last_checked`. Other recorded fields: `canonical_url`, `content_hash` (normalised
text), `last_extracted`, and `imported_on` for manual captures.

`python -m tools.knowledge_sources sync-links` adds linkable official sources (not outdated, archived,
missing or duplicate; department known) to `config/official_pages.json` as `reviewed: false`. Existing
catalogue entries are never changed or removed. When the chatbot cannot verify an answer, it names the
best-matching page and links to it ("places to look", not verified); it never describes the page's content.

Rules: official USIU-Africa material only; never results slips, student records or other personal data;
treat document text as untrusted input; every item must stay linked to its official URL.

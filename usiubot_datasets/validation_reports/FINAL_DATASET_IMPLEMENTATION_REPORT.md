# USIUBOT — Final Dataset Implementation Report

Date: 2026-11-01 (validation and tests re-run 2026-11-02). Scope: the dataset in `usiubot_datasets/` only.
The chatbot application was not changed, nothing was imported into any database, nothing was approved, and
nothing was committed to Git.

---

## A. What was completed

**PDFs**

| Document | Pages | Status |
|---|---|---|
| `Academic-Calendar-2026-2027.pdf` (local, unchanged) | 7 | Extracted in Stage 2. Its official URL is now **confirmed**: the file downloaded from `https://www.usiu.ac.ke/wp-content/uploads/2026/04/Academic-Calendar-2026-2027.pdf` has the same SHA-256 (618711f9…512f) as the local copy. |
| `Student-Handbook.pdf` (local, unchanged) | 60 | Extracted in Stage 2. Undated. The candidate public URL returns HTTP 404, so it has no confirmed URL. |
| `USIU-Africa-Free-Structure-2026-2027.pdf` (downloaded from the official site, saved in `web_sources/downloads/`) | 16 | New: "Fee Schedule 2026 - 2027 Academic Year, Effective September 1, 2026". Text extracted to `source_documents/usiu_fee_schedule_2026_2027/`. Used to cross-check the website fee tables. |

**Web pages**

* **79 pages collected** (HTTP 200):
  * 76 official USIU-Africa pages: 34 general pages and 42 programme pages.
  * 3 external KUCCPS pages.
* Every page is recorded with its URL, collection date, sitemap `lastmod` and content fidelity in `web_sources/collection_manifest.json`.
* The snapshots are in `web_sources/snapshots/`.
* Method and access rules are in `validation_reports/WEB_COLLECTION_REPORT.md`.
* **No page states a publication date.** Each is recorded as "Publication date not stated".

**External sources** (kept in `external/` folders and labelled "not USIU-Africa policy")

* **KUCCPS:** 3 pages read; 4 records and 3 chunks created.
* **CUE:** inaccessible (TLS certificate error).
* **KNQA:** inaccessible (HTTP 500).

**Categories**

* All 8 categories now contain records (see B).
* Category 08 contains:
  * 28 FAQ pairs published by USIU-Africa;
  * 22 open questions derived from the dataset's own conflicts and gaps.
* Category 08 contains **no** invented or real student enquiries.

**Stage 2 review and corrections**

* **Handbook page 7 reading order** (vision, mission, core values, schools): the reorder rule is now verified against the PDF itself. Text positions show each heading sits directly above its block (`layout_verification.json`). V24 is resolved.
* **Calendar records:** now carry the confirmed official URL (V22 resolved).
* **Handbook:** its source note records the HTTP 404 result for the candidate URL.
* **The other Stage 2 issues** were re-checked against the website. The outcome for each is in the register (summary in B and C):
  * bank details, refund window, weekday error, graduation date
  * interest duration, disciplinary rules, phone numbers, TOEFL
* **Original wording:** no Stage 2 issue text was rewritten. Updates are recorded as status changes, with website evidence.

**Scripts** (in `extraction_scripts/`, standard library plus pypdf only, no new dependencies)

| Script | Purpose |
|---|---|
| `extract_documents.py` | Stage 2 PDF extraction (calendar URL updated) |
| `import_collection_reports.py` | Splits the 2026-11-01 collection reports into per-page snapshots and the manifest |
| `build_web_dataset.py` | Website records, fee tables (arithmetic and PDF checks), programme records, chunks, registers, READMEs |
| `web_config.py`, `web_curated.py`, `web_registers.py`, `web_common.py`, `web_reports.py` | Curated, evidence-checked lists, registers and helpers |
| `collect_web_sources.py` | Reproducible collector, described below |
| `validate_dataset.py` | Final validation (22 checks) |
| `build_all.py` | Runs everything in order; output is byte-identical between runs (verified) |
| `../tests/test_dataset.py` | 10 tests |

`collect_web_sources.py` details:
* It identifies itself honestly as `USIUBOT-dataset-collector` and obeys robots.txt.
* It skips portals, logins and web forms.
* It uses conditional GET, so unchanged pages are not downloaded again.
* It hashes content to detect changes. When a page changes, it keeps the old snapshot in `web_sources/history/` and marks the page `changed_pending_review`.
* It logs every attempt, including inaccessible pages.
* It never approves anything.
* `--import-html` imports pages a person saved from a browser.

**Main new files**

* `02/official/web_programmes.csv`
* `03/official/web_admission_rules.csv`
* `04/official/web_tuition_fee_tables.csv`
* `04/official/web_other_and_general_charges.csv`
* `04/official/web_fee_policy_rules.csv`
* `04/official/web_financial_aid_programmes.csv`
* `04/official/web_bank_and_mobile_payment_details.csv`
* `04/official/bank_details_comparison.csv`
* `06/official/web_department_contacts.csv`
* `06/official/routing_departments.json`
* `07/official/web_english_proficiency_requirements.csv`
* `07/official/web_transfer_credit_rules.csv`
* `07/official/programme_entry_requirements.csv`
* `08/official/official_faq_pairs.csv`
* `08/official/open_questions_register.csv`
* `*/external/external_records.csv`
* `web_document_sections.json`, `web_knowledge_chunks.json` and `web_sections_index.csv` in each category that has web content
* `all_records_index.csv`, one row per record, with all the traceability fields requested
* Registers in `validation_reports/`:
  * `source_register.csv`
  * `conflict_and_verification_register.csv`
  * `missing_information_register.csv`
  * `fee_table_checks.csv`
  * `WEB_COLLECTION_REPORT.md`
  * `final_validation.md`

## B. Exact statistics

The four units are counted separately and never added together:
* **Records:** rows in structured CSV files.
* **Sections:** headed text blocks.
* **Chunks:** retrieval units of at most 1,000 characters.
* **Source documents:** PDFs and web pages.

**Records: 1,050 in total**

| Category | Stage 2 (PDF) | Website + external + derived | Total |
|---|---|---|---|
| 01 General University Information | 74 | 0 | 74 |
| 02 Academic Programmes | 6 | 42 | 48 |
| 03 Admissions and Applications | 11 | 25 (23 official, 2 external) | 36 |
| 04 Fees and Payments | 128 | 479 | 607 |
| 05 Registrar and Academic Administration | 59 | 0 | 59 |
| 06 Department Contacts and Query Routing | 51 | 54 | 105 |
| 07 Academic Documents, Results and Verified Eligibility | 5 | 66 (64 official, 2 external) | 71 |
| 08 Questions, Answers and Unresolved Enquiries | 0 | 50 (28 official FAQ, 22 derived) | 50 |
| **Total** | **334** | **716** | **1,050** |

* **By source type:**
  * official: 1,024
  * external: 4
  * derived open questions: 22
* **Categories 01 and 05** gained web content as sections and chunks only, not as structured records.
* **Category 04** is large because each of the 390 fee-table rows is its own record.

**Sections and chunks**

| | Sections | Chunks |
|---|---|---|
| Stage 2 PDF extraction | 139 | 208 |
| Official website pages | 461 | 606 |
| External (KUCCPS) | 3 | 3 |
| **Total** | **603** | **817** |

* Every chunk is at most 1,000 characters.
* Every web chunk starts with its heading path and is split only at paragraph, sentence or table-row boundaries.
* **Duplicates:** 16 duplicate web chunks were removed during the build (listed in `web_duplicate_chunks.csv`). After that:
  * 0 duplicate chunks across Stage 2 and web;
  * 0 duplicate record ids.

**Source documents**

* 3 PDFs: 2 local, 1 downloaded.
* 79 web pages collected.
* **8 sources not collected:**
  * inaccessible (3): CUE (TLS error), KNQA (HTTP 500), handbook candidate URL (HTTP 404);
  * restricted systems, not attempted by design (4): ITS student portal, clearance system, instalment web form, refund web form;
  * linked but not downloaded (1): Academic Catalog 2024-2026 PDF. The Online Programs Fee Schedule is also linked and not collected; it is listed as a gap.
* `source_register.csv` therefore has 90 rows: 3 PDFs + 87 web entries.
* **Fetch attempts:** 85 logged, of which 5 failed with connection refused. All 5 pages were collected on a retry.

**Fee checks**

* 37 fee tables. All 37 pass the arithmetic check: the item rows add up to the printed TOTAL in every column.
* 31 of the 37 TOTAL lines are found verbatim in the official fee schedule PDF.
* The 6 not found are online programmes, which are in the separate online fee schedule that was not collected.

**Conflict and verification register: 54 issues** (32 from Stage 2, 22 new from the website)

| Status | Count | Issues |
|---|---|---|
| Resolved | 3 | V05, V22, V24 |
| Partially resolved | 6 | V01, V03, V12, V13, V14, V26 |
| Updated with new evidence, still open | 3 | V02, V16, V32 |
| Checked against the website, still unresolved | 6 | V04, V07, V17, V20, V23, V28 |
| Open: Stage 2 issues with no new website evidence | 14 | — |
| Open: new website issues | 22 | W01, W02, W04–W06, W09–W19, W21–W26 |

* W-numbers W03, W07, W08 and W20 were not used.
* **Unresolved conflicts** (type "conflict", not resolved): 10. All keep each version and its source.
* **By type**, of the 51 unresolved issues:
  * inconsistency 12, ambiguity 11
  * conflict 10, document quality 10
  * outdated 4, missing source 3, numbering 1

**Validation** (`final_validation.md`)

* 21 of 22 checks pass, with 0 blocking failures. The remaining check is a warning: V11 (handbook page numbering) and W15 (a website wording error) appear only in the register and are not attached to a record.
* **Checks that passed:**
  * expected files exist; all CSV and JSON parse
  * unique ids; no duplicate chunks
  * every record has a source; PDF records have pages; web records have URLs
  * external records are labelled; conflicts keep both versions
  * the original PDFs and the downloaded PDF are unchanged (SHA-256)
  * all 156 app files are identical to the baseline, with no new app files
  * no record is approved; every web evidence quote is found in its snapshot
  * no secrets; no restricted system was fetched

**Tests**

* Dataset tests: 10 passed.
* Frontend (vitest): 46 passed.
* Backend (pytest): 601 passed, 1 warning, in 13 min 15 s.
* No test was skipped for lack of tools.

## C. Missing information

`missing_information_register.csv` has 38 gaps. Grouped by the action each needs:

**University confirmation (15)**

* **Fees and payments:**
  * which bank accounts are current (V01–V03, W26; three sources differ: ABSA branch Sarit vs Westlands, and a USD account and Stanbic that are not in every source)
  * the course-drop refund window (V04)
  * how long the 1.5% monthly interest runs (V28)
  * cash rules (W09)
  * Finance phone numbers (W06)
  * 2026-2027 tuition release
* **Admissions and aid:**
  * the TOEFL minimum (three versions: 79 iBT / 550 / 550-213-90)
  * the transfer-credit rule (49% vs 90 trimester units, W11)
  * Family and Legatee waiver rules (W12)
  * KUCCPS placement to USIU-Africa
  * application deadlines
* **Other:**
  * room cost (42,000 per semester vs KES 30,000, W13)
  * current leadership names
  * the +257 country code printed for the Library and Registrar (W04)
  * academic advisors' contacts
  * web page publication dates

**Department document (11)**

* exam regulations and appeals
* graduation requirements
* exam fees
* doctoral and some master's entry requirements (W23)
* international applicant checklist
* short-course fees
* programme cluster subjects
* office hours
* escalation procedure
* campus facility hours
* transfer rule source (Academic Catalog)

**Restricted system: out of scope by design (4)**

* student account balances and online payment (ITS portal)
* instalment and refund forms
* individual results
* real enquiry records for category 08

**Newer document (2)**

* a dated, current Student Handbook (V06, V07, V23)
* the CBET realignment outcome (submissions due July 2027)

**Technical work (6)**

* download and extract the Academic Catalog 2024-2026 PDF
* collect the Online Programs Fee Schedule
* collect the history page
* retry CUE and KNQA
* re-check the pre-registration page, which shows only a heading

## D. Remaining chatbot work

**Dataset completion: done within the rules**

The remaining dataset items are the gaps in C, which need the university or further collection.

**Integration: not started, as instructed.** Needed later:

1. **Approved Sources import.** Import the records into the app's Approved Sources workflow (`tools/knowledge_sources.py` imports as draft). An administrator must review and approve each source.
   * The app requires a unique https `usiu.ac.ke` URL per source.
   * Web records have one. Calendar records now have one.
   * Handbook records still have none (V23).
2. **Metadata.** Carry page, section, issue ids and source type into app chunks. The app's chunks currently store none of these.
3. **Finance department.** Add Finance as its own enquiry department. The app has five departments; `routing_departments.json` maps Finance, Student Affairs, ICT and Library to `general_university` in the meantime.
4. **Response rules.**
   * Never show bank details as confirmed.
   * Show both versions for open conflicts.
   * Never present expired deadlines or external statements as USIU policy.
5. **Retrieval.** Keep the existing BM25 retrieval and MongoDB.

**Not done:** no MongoDB Atlas connection, no MCP install, no live database import.

## E. Exact PowerShell commands

Run from the project root.

```powershell
cd C:\Users\Admin\Downloads\chatbot-for-students-queries-1
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTHONIOENCODING = "utf-8"

# rebuild everything and validate (byte-identical output on an unchanged input)
.\backend\.venv\Scripts\python.exe usiubot_datasets\extraction_scripts\build_all.py

# validation only
.\backend\.venv\Scripts\python.exe usiubot_datasets\extraction_scripts\validate_dataset.py

# dataset tests
.\backend\.venv\Scripts\python.exe -m pytest usiubot_datasets\tests -q -p no:cacheprovider

# app tests (unchanged app)
cd backend; .\.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider; cd ..
cd frontend; npx vitest run; cd ..

# collector: robots.txt check only, then refresh permitted pages, or import pages saved from a browser
.\backend\.venv\Scripts\python.exe usiubot_datasets\extraction_scripts\collect_web_sources.py --check-robots
.\backend\.venv\Scripts\python.exe usiubot_datasets\extraction_scripts\collect_web_sources.py --fetch
.\backend\.venv\Scripts\python.exe usiubot_datasets\extraction_scripts\collect_web_sources.py --import-html C:\path\to\saved_pages

# re-split the original 2026-11-01 collection reports (overwrites the manifest; do not use after --fetch)
.\backend\.venv\Scripts\python.exe usiubot_datasets\extraction_scripts\build_all.py --reimport
```

**Collector behaviour.** `--check-robots` (run 2026-11-02) reports 81 URLs blocked and 4 allowed:
* **Blocked:**
  * every usiu.ac.ke page: robots.txt `User-agent: * / Disallow: /`;
  * KNQA: robots.txt returns HTTP 500, which is treated as disallow;
  * the portal and clearance hosts: not on the allow-list.
* **Allowed:** the 3 KUCCPS pages and CUE.

For usiu.ac.ke pages, `--fetch` therefore collects nothing, by design. Refresh them with `--import-html`, or ask Claude (Claude-User, which robots.txt allows) to read them again.

## F. Status per task

| # | Task | Status | Notes |
|---|---|---|---|
| 1 | Review and correct Stage 2 | **Complete** | Reading order verified (V24); calendar URL confirmed (V22); catalog link outdated (V05); other issues re-checked; no issue text rewritten |
| 2 | Collect the official website | **Partial** | All 7 seed pages plus 72 more (programmes, postgraduate, doctoral, online, international, transfer, fees, aid, calendar, graduation, library, housing, health, careers, contacts, FAQ). Not collected: Academic Catalog PDF, online fee schedule, history page, pre-registration content (heading only). Restricted systems excluded by design. |
| 3 | External sources | **Partial** | KUCCPS collected and labelled; CUE and KNQA inaccessible (recorded) |
| 4 | Traceability fields on every record | **Complete** | In every web CSV and in `all_records_index.csv`; "Publication date not stated" where none is printed |
| 5 | Conflicts, outdated information, nothing invented | **Complete** | Both versions kept (54-issue register); expired calls marked; every curated value is evidence-checked against its snapshot |
| 6 | Populate all 8 categories | **Complete** | All 8 have records. Category 07 is thin on results and qualifications (needs departments); 08 has official FAQs and derived questions only. |
| 7 | Structured files and registers | **Complete** | JSON/CSV/Markdown, source register, collection report, missing-information register, conflict register, READMEs |
| 8 | IDs, duplication, chunking | **Complete** | Unique ids; 0 duplicate chunks; heading kept with its text; no sentence cut |
| 9 | Stage 2 issue list | **Complete (record), partial (resolution)** | 3 resolved, 6 partially resolved; the rest need the university (C). Bank details never published as confirmed. |
| 10 | Routing incl. Finance | **Complete in the dataset** | 13 departments with traceable contacts (unverified, marked). App integration not done (D). |
| 11 | Reproducible scripts | **Complete** | Robots-respecting, conditional GET, history, duplicate and change detection, never approves, PowerShell commands |
| 12 | Final validation and tests | **Complete** | 0 blocking failures, 1 warning; dataset, frontend and backend tests as in B |
| 13 | Final report | **Complete** | This file |
| 14 | Stop before app changes or database import | **Complete** | App files byte-identical to the baseline; no database contact; nothing approved; nothing committed |

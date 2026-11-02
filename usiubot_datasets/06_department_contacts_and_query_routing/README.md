# 06 Department Contacts and Query Routing

All contact details printed in either document, exactly as printed (department_contacts.csv), the handbook's University Communication (marketing) and Contact Us sections, calendar page 7, and a routing reference for the five USIUBOT enquiry departments quoting what the documents say each one does. Several numbers conflict within the handbook (issues V12-V14). No contact is verified.

Every record is `review_status: draft`, `verification_status: pending_verification`, `approval_status: not_approved`, `data_origin: official`. Nothing has been imported into the app or any database.

## Files

| File | Records | Contents |
|---|---|---|
| `official/document_sections.json` | 3 | One record per document section (full text, pages, heading, flags, issues). |
| `official/knowledge_chunks.json` | 5 | The same sections split into retrieval chunks of at most 1,000 characters (no overlap), each with full source metadata. |
| `official/sections_for_review.md` | 3 | Human-readable version of the sections for review. |
| `official/sections_index.csv` | 3 | One row per section: pages, size, chunk count, flags, issues, status. |
| `official/department_contacts.csv` | 51 | Every contact detail printed in either document, as printed. |

`external/` is empty (no external sources were collected in Stage 2). `metadata/category_metadata.json` holds counts and coverage.

## Coverage of the information this category needs

| Information | Status | Notes |
|---|---|---|
| Admissions: responsibilities and contacts | Extracted | Email (calendar p7), location (handbook p16). |
| Registrar: responsibilities and contacts | Extracted | Email (calendar p7, issue V26), extensions (handbook p13). |
| Marketing: responsibilities and contacts | Extracted | Email and telephone (handbook p57). |
| Academic Programmes: responsibilities and contacts | Unavailable | No such office is named and no contact is printed. |
| General University Information: contacts | Extracted | General telephone, WhatsApp, postal address. |
| Working hours | Unavailable | No office hours (library and health centre hours only). |
| Escalation procedure | Unavailable | Only disciplinary/grievance escalation (10.13, 10.16). |

## Issues affecting records in this folder

| Issue | Severity | Summary |
|---|---|---|
| V07 | high | The handbook does not state its academic year, edition or publication date. The latest year in the text is 2024; the PDF file metadata says it was created on 2025-07-30 and modified on 2025-08-13 (file metadata is not proof of publication). |
| V12 | medium | Health Center telephone numbers differ: '0730 116 720/0730 116 760' (page 24), '730611760/762/271' (page 50) and '0730116760/762/271' (page 51). |
| V13 | medium | Counselling extensions differ: '748,750,746 or 790' (page 24) vs '748, 797,746, 791' (page 47). Page 54 gives 'Counselling and Health Centre (extension 779)', but page 24 lists Ext 779 for the Head of Placement and Career Services. |
| V14 | medium | The Security Department number on page 24 is garbled ('0730 116 266/0730, Ext. 116 320') and differs from page 54 ('730116 774/618'). |
| V22 | high | The calendar's official URL is not confirmed (recorded as 'Local copy — official URL not yet confirmed'). The existing Approved Sources feature requires an https usiu.ac.ke URL for every source. |
| V23 | medium | The handbook's official URL is not confirmed. A candidate URL exists in the official links catalogue but it was not downloaded or compared with the local copy. |
| V26 | low | The Registrar's email is printed as 'registra@usiu.ac.ke' (no final 'r'). It is recorded exactly as printed; the handbook gives no Registrar email to compare. |
| V27 | low | Medical-insurance exemption requests go to an individual staff address (mwanderi@usiu.ac.ke) rather than an office address. Individual addresses change when staff change. |
| V31 | low | Typing errors in an emergency instruction: 'call the police at 999 or 112e' and 'Counselling Service at 748, 797,746, 791or'. |

Full details: `../validation_reports/validation_issues.csv`.

<!-- WEB-START -->
## Website and external records (collected 2026-11-01)

| File | Rows | Contents |
|---|---|---|
| official/routing_departments.json | 13 | routing departments (incl. Finance as its own department) with contacts, handbook responsibilities and the closest existing app department |
| official/web_department_contacts.csv | 54 | contacts printed on official pages, with routing department |
| official/web_document_sections.json | 10 | page sections (heading path + text) from the website snapshots |
| official/web_knowledge_chunks.json | 10 | chunks of at most 1000 characters; each starts with its heading path and never cuts a sentence |
| official/web_sections_index.csv | 10 | index of the web sections |

Sections / chunks in this category: Stage 2 PDF 3 / 5; official website 10 / 10; external 0 / 0.

Every website record carries: record id, category, topic, information, source title, URL, snapshot file, section, date collected, publication date ("Publication date not stated" where none is printed), academic year, source type (official/external), verification status, conflict/warning (issue ids) and last checked date. All records are drafts, pending verification, not approved.
Issues: `validation_reports/conflict_and_verification_register.csv`.
<!-- WEB-END -->

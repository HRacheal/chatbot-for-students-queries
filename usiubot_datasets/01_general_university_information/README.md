# 01 General University Information

Calendar pages 2-4 (semester text), handbook sections on the university profile, student life, library, ICT, student conduct and discipline, student activity policies, support services, campus safety and alumni. The non-academic Student Code of Conduct (handbook section 10) is administered by the Dean of Students, not the Registrar, so it is filed here as a university policy. Calendar events about semester dates, orientation, hostels, holidays and breaks are in calendar_events.csv here; events about admissions, fees and academic administration are in folders 03, 04 and 05.

Every record is `review_status: draft`, `verification_status: pending_verification`, `approval_status: not_approved`, `data_origin: official`. Nothing has been imported into the app or any database.

## Files

| File | Records | Contents |
|---|---|---|
| `official/document_sections.json` | 98 | One record per document section (full text, pages, heading, flags, issues). |
| `official/knowledge_chunks.json` | 157 | The same sections split into retrieval chunks of at most 1,000 characters (no overlap), each with full source metadata. |
| `official/sections_for_review.md` | 98 | Human-readable version of the sections for review. |
| `official/sections_index.csv` | 98 | One row per section: pages, size, chunk count, flags, issues, status. |
| `official/calendar_events.csv` | 36 | Dated calendar events for this category, one row per printed bullet. |
| `official/library_loan_periods.csv` | 7 | Library loan limits by borrower type. |
| `official/semester_terms.csv` | 3 | Semester start/end dates, length and recess as printed. |
| `official/service_hours.csv` | 12 | Opening hours printed for the library, live chat, health centre and counselling. |
| `official/university_profile.csv` | 16 | Accreditation, vision, mission, core values, leadership and other profile facts, each quoted verbatim. |

`external/` is empty (no external sources were collected in Stage 2). `metadata/category_metadata.json` holds counts and coverage.

## Coverage of the information this category needs

| Information | Status | Notes |
|---|---|---|
| University history | Partially extracted | Only brief statements: one of the oldest private, secular universities in East Africa; dual accreditation; Alumni Association registered April 1990. No founding history. |
| Location | Extracted | P.O. Box and 'USIU Road, Off Thika Road (Exit 7) Nairobi' (handbook p60); P.O. Box (calendar p7). |
| Campus information | Partially extracted | Buildings and facilities are named across sections (Freida Brown Student Center, Lillian K Beam Building, hostels, sports facilities). No campus map or campus list. |
| Contact information | Extracted | See 06_department_contacts_and_query_routing. |
| University leadership | Partially extracted | Vice Chancellor and Deputy Vice Chancellor, Student Life only; undated (issue V25). |
| Facilities | Extracted | Library, ICT labs, sports, health centre, catering, transport, hostels. |
| Library | Extracted | Rules, loan periods, opening hours, contacts (handbook section 7). |
| Accommodation | Partially extracted | On-campus hostel description and capacity; hostel check-in/out dates. No hostel fees. |
| Student services | Extracted | Counselling, career services, disability inclusion, gender equity, health, insurance, transport, catering. |
| Academic calendar | Extracted | Full 2026-2027 calendar (semester_terms.csv and calendar_events.csv). |
| Frequently asked questions | Unavailable | Neither document contains an FAQ. |

## Issues affecting records in this folder

| Issue | Severity | Summary |
|---|---|---|
| V04 | high | Partial refund window for dropped courses. Handbook: '75% charge waiver ... within 14 calendar days of the first day of the semester'. Calendar: the last day to drop a course and receive a 75% refund is 16 September 2026 (instruction begins 7 September), 22 January 2027 (begins 11 January) and 21 May 2027 (begins 10 May), i.e. 9-11 days after the first day, with 'no more partial refund' after that date. |
| V06 | high | The handbook contains editorial placeholders, which suggests this copy may be a draft or an unfinished edition: 'MISSING INFOMATION' (page 15) and 'TABLE TO BE INSERTED' (page 49). |
| V07 | high | The handbook does not state its academic year, edition or publication date. The latest year in the text is 2024; the PDF file metadata says it was created on 2025-07-30 and modified on 2025-08-13 (file metadata is not proof of publication). |
| V08 | medium | Sanction for drug offences. 10.7 item 3 lists 'Suspension' for possession, sale or use of illicit drugs; 10.14 item 12 says any drug-related violation 'will result in dismissal'. |
| V09 | low | Cross-reference error: 10.14 item 5 refers to 'section 6.1.1 above' for alcohol sanctions, but 6.1.1 is about bulletin boards. |
| V10 | low | Cross-reference error: 10.16.7 says appeals are handled 'as described in Article 6.2.6 above'; the handbook has no 6.2.6. |
| V12 | medium | Health Center telephone numbers differ: '0730 116 720/0730 116 760' (page 24), '730611760/762/271' (page 50) and '0730116760/762/271' (page 51). |
| V13 | medium | Counselling extensions differ: '748,750,746 or 790' (page 24) vs '748, 797,746, 791' (page 47). Page 54 gives 'Counselling and Health Centre (extension 779)', but page 24 lists Ext 779 for the Head of Placement and Career Services. |
| V14 | medium | The Security Department number on page 24 is garbled ('0730 116 266/0730, Ext. 116 320') and differs from page 54 ('730116 774/618'). |
| V15 | low | The table of contents gives page 58 for the Alumni Relations Office; the section is on page 59. |
| V17 | medium | Graduation year label for Fall 2026 completers differs: 30 October 2026 '2027 Graduation and certificate application process begins for students completing degree requirements in Fall 2026' vs 4 January 2027 'Deadline for 2026 Graduation and certificate application for students completing degree requirements in Fall 2026'. |
| V18 | low | Fall 2026 recess: 'Academic Recess – December 14, 2026 – January 10, 2027' while 'University proceeds on recess' is dated 18 December. These may describe different things (teaching vs offices); the calendar does not say. |
| V19 | low | The Fall 2026 mid-semester exam week (19-24 October) includes 20 October, Mashujaa Day, when offices are closed. The calendar does not say whether exams take place that day. |
| V21 | low | 'July 5 Monday USIU-Africa offices closed' gives no reason. Only 4 July (U.S. Independence holiday) is explained. |
| V22 | high | The calendar's official URL is not confirmed (recorded as 'Local copy — official URL not yet confirmed'). The existing Approved Sources feature requires an https usiu.ac.ke URL for every source. |
| V23 | medium | The handbook's official URL is not confirmed. A candidate URL exists in the official links catalogue but it was not downloaded or compared with the local copy. |
| V24 | low | Page 7 prints headings (vision, mission, core values, schools) and their text in separate blocks. The text layer gives the blocks out of order; vision and mission were assigned by layout order. |
| V25 | low | Leadership names are as printed in an undated handbook and may have changed. |
| V27 | low | Medical-insurance exemption requests go to an individual staff address (mwanderi@usiu.ac.ke) rather than an office address. Individual addresses change when staff change. |
| V30 | low | Personal accident cover: medical expenses reimbursement 'up to 600,000' has no currency, while the other amounts in the sentence are in Kes. |
| V31 | low | Typing errors in an emergency instruction: 'call the police at 999 or 112e' and 'Counselling Service at 748, 797,746, 791or'. |

Full details: `../validation_reports/validation_issues.csv`.

<!-- WEB-START -->
## Website and external records (collected 2026-11-01)

| File | Rows | Contents |
|---|---|---|
| official/web_document_sections.json | 205 | page sections (heading path + text) from the website snapshots |
| official/web_knowledge_chunks.json | 228 | chunks of at most 1000 characters; each starts with its heading path and never cuts a sentence |
| official/web_sections_index.csv | 205 | index of the web sections |

Sections / chunks in this category: Stage 2 PDF 98 / 157; official website 205 / 228; external 0 / 0.

Every website record carries: record id, category, topic, information, source title, URL, snapshot file, section, date collected, publication date ("Publication date not stated" where none is printed), academic year, source type (official/external), verification status, conflict/warning (issue ids) and last checked date. All records are drafts, pending verification, not approved.
Issues: `validation_reports/conflict_and_verification_register.csv`.
<!-- WEB-END -->

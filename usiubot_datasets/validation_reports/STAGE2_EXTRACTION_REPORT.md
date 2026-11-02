# Stage 2 extraction report (generated)

Extraction date: 2026-11-01. Every record is `review_status: draft`, `verification_status: pending_verification`, `approval_status: not_approved`, `data_origin: official`. Nothing has been imported into the app or any database.

## Documents

| Document | Pages | Sections | Chunks | Characters |
|---|---|---|---|---|
| Academic-Calendar-2026-2027.pdf | 7 | 6 | 14 | 11764 |
| Student-Handbook.pdf | 60 | 133 | 194 | 114907 |

Calendar events: 111 · semester terms: 3 · structured rows: 334 · evidence quotes checked: 237 (failures: 0) · duplicate chunks: 0 · largest chunk: 997 characters.

## Structured files

| File | Rows |
|---|---|
| 01/calendar_events.csv | 36 |
| 01/library_loan_periods.csv | 7 |
| 01/semester_terms.csv | 3 |
| 01/service_hours.csv | 12 |
| 01/university_profile.csv | 16 |
| 02/schools.csv | 6 |
| 03/admission_conditions.csv | 8 |
| 03/calendar_events.csv | 3 |
| 04/bank_and_mobile_payment_details.csv | 16 |
| 04/calendar_events.csv | 24 |
| 04/fee_policy_rules.csv | 30 |
| 04/financial_aid_programmes.csv | 20 |
| 04/mpesa_purpose_codes.csv | 38 |
| 05/calendar_events.csv | 48 |
| 05/registrar_services.csv | 11 |
| 06/department_contacts.csv | 51 |
| 07/english_proficiency_requirements.csv | 5 |

## Issues (sorted by severity)

| Issue | Type | Severity | Admin decision | Summary | Recommended action |
|---|---|---|---|---|---|
| V01 | outdated | high | yes | The handbook's bank payment details are dated 'valid as at May 2024'. | Do not use handbook bank details as current. Confirm the current list with the Finance Office. |
| V02 | conflict | high | yes | Stanbic Bank accounts appear in the handbook but not in the 2026-2027 calendar's payment list. | Finance Office to confirm whether the Stanbic accounts are still valid. Until then neither list should be presented as complete. |
| V04 | conflict | high | yes | Partial refund window for dropped courses. Handbook: '75% charge waiver ... within 14 calendar days of the first day of the semester'. Calendar: the last day to drop a course and receive a 75% refund is 16 September 2026 (instruction begins 7 September), 22 January 2027 (begins 11 January) and 21 May 2027 (begins 10 May), i.e. 9-11 days after the first day, with 'no more partial refund' after that date. | Registrar/Finance to confirm which rule applies for 2026-2027. The chatbot must not state either rule alone until resolved. |
| V06 | document_quality | high | yes | The handbook contains editorial placeholders, which suggests this copy may be a draft or an unfinished edition: 'MISSING INFOMATION' (page 15) and 'TABLE TO BE INSERTED' (page 49). | Confirm with the Registrar/Student Life office that this is the published edition before approval. |
| V07 | missing_source | high | yes | The handbook does not state its academic year, edition or publication date. The latest year in the text is 2024; the PDF file metadata says it was created on 2025-07-30 and modified on 2025-08-13 (file metadata is not proof of publication). | Record the edition/academic year once confirmed by the university. |
| V22 | missing_source | high | yes | The calendar's official URL is not confirmed (recorded as 'Local copy — official URL not yet confirmed'). The existing Approved Sources feature requires an https usiu.ac.ke URL for every source. | Find the official page that publishes this PDF before import or approval. |
| V03 | conflict | medium | yes | The same account numbers (KES 6438840014, USD 6462210014) are listed under different bank names and account names: 'Commercial Bank of Africa' / 'United States International University – Africa' (handbook) vs 'NCBA BANK KENYA LTD' / 'USIU or U.S. International University' (calendar). The handbook also gives a routing number that the calendar does not. | Finance Office to confirm the correct bank name, account name and codes. |
| V05 | outdated | medium | no | The handbook links to the Academic Catalog 2021-2023. | Find the current Academic Catalog before answering questions about degree requirements. |
| V08 | conflict | medium | yes | Sanction for drug offences. 10.7 item 3 lists 'Suspension' for possession, sale or use of illicit drugs; 10.14 item 12 says any drug-related violation 'will result in dismissal'. | Dean of Students to confirm. The chatbot should quote both clauses or refer the user to the office. |
| V12 | inconsistency | medium | yes | Health Center telephone numbers differ: '0730 116 720/0730 116 760' (page 24), '730611760/762/271' (page 50) and '0730116760/762/271' (page 51). | Health Center to confirm its numbers before any are shown to users. |
| V13 | inconsistency | medium | yes | Counselling extensions differ: '748,750,746 or 790' (page 24) vs '748, 797,746, 791' (page 47). Page 54 gives 'Counselling and Health Centre (extension 779)', but page 24 lists Ext 779 for the Head of Placement and Career Services. | Counselling Center to confirm its extensions. |
| V14 | inconsistency | medium | yes | The Security Department number on page 24 is garbled ('0730 116 266/0730, Ext. 116 320') and differs from page 54 ('730116 774/618'). | Security office to confirm its numbers. |
| V16 | outdated | medium | yes | English proficiency requirement may be outdated. It includes a TOEFL 'computer-based test' score (213). Processing note (general knowledge, not from the document): the computer-based TOEFL is no longer offered, so the requirement needs confirmation. | Admissions to confirm current English proficiency requirements. |
| V17 | inconsistency | medium | yes | Graduation year label for Fall 2026 completers differs: 30 October 2026 '2027 Graduation and certificate application process begins for students completing degree requirements in Fall 2026' vs 4 January 2027 'Deadline for 2026 Graduation and certificate application for students completing degree requirements in Fall 2026'. | Registrar to confirm which graduation (2026 or 2027) Fall 2026 completers apply for. |
| V20 | inconsistency | medium | yes | Calendar date and day name disagree: September 16 Friday (2026-09-16 is a Wednesday; the calendar says Friday; affects 3 events) | Registrar to confirm the correct date. Both the printed date and day are kept unchanged in calendar_events.csv. |
| V23 | missing_source | medium | yes | The handbook's official URL is not confirmed. A candidate URL exists in the official links catalogue but it was not downloaded or compared with the local copy. | Confirm that the candidate URL serves this exact edition (compare SHA-256) before import. |
| V28 | inconsistency | medium | yes | Interest on unpaid fees: 3.2 says 1.5% per month 'until they are fully paid'; 3.11 says 1.5% per month 'for up to 10 months, with interest stopped once the student resumes payments'. The 2026-2027 calendar only says the 1.5% monthly interest 'begins' on the second day of each semester. | Finance Office to confirm how long interest applies. |
| V09 | document_quality | low | no | Cross-reference error: 10.14 item 5 refers to 'section 6.1.1 above' for alcohol sanctions, but 6.1.1 is about bulletin boards. | Note only; report to the handbook owner. |
| V10 | document_quality | low | no | Cross-reference error: 10.16.7 says appeals are handled 'as described in Article 6.2.6 above'; the handbook has no 6.2.6. | Note only; disciplinary appeals are described in 10.13. |
| V11 | numbering | low | no | Handbook section numbering problems: section number 5.4.4 is used twice (pages 19, 20); section number 10.16.7 is used twice (pages 46, 46); no section is numbered 5.1 (the next number printed is 5.2, page 16); no section is numbered 10.16.3 (the next number printed is 10.16.4, page 46); heading 'Conduct Regulations' is used for sections 10.3, 10.7 | Note only; sections are kept separate and in printed order. |
| V15 | document_quality | low | no | The table of contents gives page 58 for the Alumni Relations Office; the section is on page 59. | Note only. |
| V18 | ambiguity | low | no | Fall 2026 recess: 'Academic Recess – December 14, 2026 – January 10, 2027' while 'University proceeds on recess' is dated 18 December. These may describe different things (teaching vs offices); the calendar does not say. | Preserve both statements; do not merge them. |
| V19 | ambiguity | low | no | The Fall 2026 mid-semester exam week (19-24 October) includes 20 October, Mashujaa Day, when offices are closed. The calendar does not say whether exams take place that day. | Note only. |
| V21 | ambiguity | low | no | 'July 5 Monday USIU-Africa offices closed' gives no reason. Only 4 July (U.S. Independence holiday) is explained. | Note only. |
| V24 | ambiguity | low | no | Page 7 prints headings (vision, mission, core values, schools) and their text in separate blocks. The text layer gives the blocks out of order; vision and mission were assigned by layout order. | Check the vision/mission assignment against the PDF. |
| V25 | outdated | low | no | Leadership names are as printed in an undated handbook and may have changed. | Confirm current office holders before showing names. |
| V26 | ambiguity | low | yes | The Registrar's email is printed as 'registra@usiu.ac.ke' (no final 'r'). It is recorded exactly as printed; the handbook gives no Registrar email to compare. | Registrar to confirm the address. |
| V27 | ambiguity | low | yes | Medical-insurance exemption requests go to an individual staff address (mwanderi@usiu.ac.ke) rather than an office address. Individual addresses change when staff change. | Confirm the current address; prefer an office address (e.g. the insurance team address on page 51). |
| V29 | ambiguity | low | no | 'The second 50% installment plus interest is due on the 7th day of the second month' does not say second month of what (semester or payment plan). | Quote as printed; do not compute a date. |
| V30 | ambiguity | low | no | Personal accident cover: medical expenses reimbursement 'up to 600,000' has no currency, while the other amounts in the sentence are in Kes. | Quote as printed. |
| V31 | document_quality | low | no | Typing errors in an emergency instruction: 'call the police at 999 or 112e' and 'Counselling Service at 748, 797,746, 791or'. | Recorded exactly as printed; do not correct silently. |
| V32 | ambiguity | low | no | One M-PESA purpose code (MUS) gives a different account number ('Account Number 10-1231-6152') from the Student ID pattern used for all other codes. | Quote as printed; Finance to confirm. |

## PDF integrity

| File | SHA-256 (baseline = before = after) | Unchanged |
|---|---|---|
| Academic-Calendar-2026-2027.pdf | 618711f96eb9efd55d744341175a0b39a75087e8d2c8f692340bc0bb9067512f | True |
| Student-Handbook.pdf | 610a3da82992e0c392ac69c317cbf1bd99679313acce8090fab3b9924ef87c15 | True |

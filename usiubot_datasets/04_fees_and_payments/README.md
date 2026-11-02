# 04 Fees and Payments

Handbook section 3 (fees and fee payment policy) and 5.2.4-5.2.10 (financial aid), calendar pages 5-6 (bank, M-PESA and purpose codes), fee-related calendar events, fee rules quoted verbatim, and bank/M-PESA details. No fee amounts exist in either document. Bank details are HIGH-RISK: the two documents disagree (issues V01-V03) and these rows must never be shown to users until the Finance Office confirms them.

Every record is `review_status: draft`, `verification_status: pending_verification`, `approval_status: not_approved`, `data_origin: official`. Nothing has been imported into the app or any database.

## Files

| File | Records | Contents |
|---|---|---|
| `official/document_sections.json` | 23 | One record per document section (full text, pages, heading, flags, issues). |
| `official/knowledge_chunks.json` | 27 | The same sections split into retrieval chunks of at most 1,000 characters (no overlap), each with full source metadata. |
| `official/sections_for_review.md` | 23 | Human-readable version of the sections for review. |
| `official/sections_index.csv` | 23 | One row per section: pages, size, chunk count, flags, issues, status. |
| `official/bank_and_mobile_payment_details.csv` | 16 | Bank accounts and M-PESA paybill from both documents (HIGH-RISK). |
| `official/calendar_events.csv` | 24 | Dated calendar events for this category, one row per printed bullet. |
| `official/fee_policy_rules.csv` | 30 | Fee, interest, refund and payment-plan rules quoted verbatim. |
| `official/financial_aid_programmes.csv` | 20 | Financial aid programmes by level, as listed. |
| `official/mpesa_purpose_codes.csv` | 38 | M-PESA payment purpose codes (calendar page 6). |

`external/` is empty (no external sources were collected in Stage 2). `metadata/category_metadata.json` holds counts and coverage.

## Coverage of the information this category needs

| Information | Status | Notes |
|---|---|---|
| Tuition fees (amounts, by programme, by semester) | Unavailable | The handbook says fees are published in the University Fee Schedule (3.1); no amounts in either document. |
| Application fee, registration charges, examination fees (amounts) | Unavailable | Late registration and add/drop fees exist, but no amounts are given. |
| Other compulsory charges | Partially extracted | Returned-cheque charge, medical insurance, fines (conduct section) — mostly without amounts. |
| Payment procedures | Extracted | Bank, M-PESA, online card payment, purpose codes (high-risk data, issues V01-V03). |
| Payment deadlines and interest | Extracted | Calendar fee dates per semester; handbook rules (issue V28). |
| Scholarships and financial assistance | Extracted | Financial aid programmes, eligibility and provisions (5.2.4-5.2.10). |
| Refund policy | Extracted | Charge waiver schedule and refund procedure (conflict V04). |

## Issues affecting records in this folder

| Issue | Severity | Summary |
|---|---|---|
| V01 | high | The handbook's bank payment details are dated 'valid as at May 2024'. |
| V02 | high | Stanbic Bank accounts appear in the handbook but not in the 2026-2027 calendar's payment list. |
| V03 | medium | The same account numbers (KES 6438840014, USD 6462210014) are listed under different bank names and account names: 'Commercial Bank of Africa' / 'United States International University – Africa' (handbook) vs 'NCBA BANK KENYA LTD' / 'USIU or U.S. International University' (calendar). The handbook also gives a routing number that the calendar does not. |
| V04 | high | Partial refund window for dropped courses. Handbook: '75% charge waiver ... within 14 calendar days of the first day of the semester'. Calendar: the last day to drop a course and receive a 75% refund is 16 September 2026 (instruction begins 7 September), 22 January 2027 (begins 11 January) and 21 May 2027 (begins 10 May), i.e. 9-11 days after the first day, with 'no more partial refund' after that date. |
| V07 | high | The handbook does not state its academic year, edition or publication date. The latest year in the text is 2024; the PDF file metadata says it was created on 2025-07-30 and modified on 2025-08-13 (file metadata is not proof of publication). |
| V20 | medium | Calendar date and day name disagree: September 16 Friday (2026-09-16 is a Wednesday; the calendar says Friday; affects 3 events) |
| V22 | high | The calendar's official URL is not confirmed (recorded as 'Local copy — official URL not yet confirmed'). The existing Approved Sources feature requires an https usiu.ac.ke URL for every source. |
| V23 | medium | The handbook's official URL is not confirmed. A candidate URL exists in the official links catalogue but it was not downloaded or compared with the local copy. |
| V28 | medium | Interest on unpaid fees: 3.2 says 1.5% per month 'until they are fully paid'; 3.11 says 1.5% per month 'for up to 10 months, with interest stopped once the student resumes payments'. The 2026-2027 calendar only says the 1.5% monthly interest 'begins' on the second day of each semester. |
| V29 | low | 'The second 50% installment plus interest is due on the 7th day of the second month' does not say second month of what (semester or payment plan). |
| V32 | low | One M-PESA purpose code (MUS) gives a different account number ('Account Number 10-1231-6152') from the Student ID pattern used for all other codes. |

Full details: `../validation_reports/validation_issues.csv`.

<!-- WEB-START -->
## Website and external records (collected 2026-11-01)

| File | Rows | Contents |
|---|---|---|
| official/bank_details_comparison.csv | 10 | the same accounts compared across website, calendar and handbook |
| official/web_bank_and_mobile_payment_details.csv | 10 | bank accounts and M-PESA paybill as printed on the website (UNCONFIRMED; refer users to Finance) |
| official/web_document_sections.json | 83 | page sections (heading path + text) from the website snapshots |
| official/web_fee_policy_rules.csv | 30 | payment, interest, instalment and refund rules |
| official/web_financial_aid_programmes.csv | 19 | scholarships, grants, waivers, loans; expired calls are marked |
| official/web_knowledge_chunks.json | 98 | chunks of at most 1000 characters; each starts with its heading path and never cuts a sentence |
| official/web_other_and_general_charges.csv | 30 | Other Charges and General Charges tables |
| official/web_sections_index.csv | 83 | index of the web sections |
| official/web_tuition_fee_tables.csv | 390 | every row of the 37 fee tables on the Tuition & Fees page (2026-2027), per semester |

Sections / chunks in this category: Stage 2 PDF 23 / 27; official website 83 / 98; external 0 / 0.

Every website record carries: record id, category, topic, information, source title, URL, snapshot file, section, date collected, publication date ("Publication date not stated" where none is printed), academic year, source type (official/external), verification status, conflict/warning (issue ids) and last checked date. All records are drafts, pending verification, not approved.
Issues: `validation_reports/conflict_and_verification_register.csv`.
<!-- WEB-END -->

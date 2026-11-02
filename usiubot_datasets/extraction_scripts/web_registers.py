"""Hand-written registers: missing information (with the action each gap needs), category 08 open
questions derived from the dataset's own gaps and conflicts, and the query-routing departments.

Nothing here is a fact about the university except where a record id or evidence page is cited.
Category 08 rows are NOT student enquiries: they are questions the dataset itself cannot answer yet.
"""

# action_type values (the user's five categories):
UC = "university_confirmation"
DD = "department_document"
RS = "restricted_system"
ND = "newer_document"
TW = "technical_work"

# (category, information required, status after Stage 2 + website collection, where it is now, action type,
#  action / who)
MISSING = [
    ("01", "University history (founding, milestones)", "Partially available",
     "About Us page; handbook statements. History page linked but not collected.", TW,
     "Collect https://www.usiu.ac.ke/about-us/history/ in a later run (it was linked, not fetched)."),
    ("01", "University leadership (current names)", "Partially available (possibly outdated)",
     "Undated handbook only (V25). Leadership pages not collected.", UC,
     "Office of the Vice Chancellor / Marketing to confirm current officers."),
    ("01", "Accommodation cost on campus", "Available, conflicting", "Tuition page 42,000 per semester vs Housing FAQ "
     "KES 30,000 (W13).", UC, "Housing Office / Finance to confirm."),
    ("01", "Campus map, facilities opening hours other than library and counselling", "Unavailable",
     "Not on the pages collected.", DD, "Facilities / Student Affairs."),
    ("02", "Full programme catalogue: curricula, course lists, unit counts", "Unavailable",
     "Academic Catalog 2024-2026 PDF is linked but was not downloaded.", TW,
     "Download and extract the Academic Catalog 2024-2026 PDF (same pipeline as the fee schedule)."),
    ("02", "Programmes on the fee schedule without a programme page (W19)", "Partially available",
     "Fee tables only.", UC, "Schools / Admissions to confirm the programmes are offered."),
    ("02", "Short-course fees and schedules", "Unavailable", "Short Courses page gives descriptions only.", DD,
     "Relevant school / continuing education unit."),
    ("02", "CBET realignment outcome", "Partially available (in progress)", "CBET page: submissions due July 2027.",
     ND, "Quality Assurance (cbet@usiu.ac.ke) to publish the outcome."),
    ("03", "Doctoral and some master's admission requirements (W23)", "Unavailable",
     "Programme pages say nothing.", DD, "Admissions / School of Graduate Studies."),
    ("03", "Application deadlines per intake", "Unavailable", "Only 'intake ongoing' banners; calendar has no "
     "application deadline.", UC, "Admissions."),
    ("03", "Transfer-credit rule (W11)", "Available, conflicting", "Two official pages differ.", DD,
     "Registrar to confirm from the Academic Catalog 2024-2026."),
    ("03", "KUCCPS placement to USIU-Africa", "Unavailable", "External KUCCPS pages contradict each other and do not "
     "name USIU-Africa (W24).", UC, "Admissions."),
    ("03", "Required documents checklist for international applicants (visa/Pupil's Pass steps)", "Partially available",
     "Admission Requirements page.", DD, "International Students office."),
    ("04", "Tuition fees by programme 2026-2027", "Available (draft)", "Tuition page and fee schedule PDF agree on TOTAL "
     "rows (see fee_table_checks.csv).", UC, "Finance to confirm before release."),
    ("04", "Bank account details", "Available, conflicting across three sources", "bank_details_comparison.csv; "
     "V01-V03, W26.", UC, "Finance Office must confirm. Never present as confirmed."),
    ("04", "Course-drop refund / charge-waiver schedule (V04)", "Conflicting / incomplete", "Handbook vs calendar; "
     "website silent.", UC, "Finance / Registrar."),
    ("04", "Interest duration on balances (V28)", "Partially available", "Rate agreed, duration not.", UC, "Finance."),
    ("04", "Examination fees and supplementary/special exam fees", "Unavailable", "Not on fee pages.", DD, "Finance / Registrar."),
    ("04", "Online payment portal steps and student account balance", "Restricted",
     "ITS student portal (login) - not accessed.", RS, "Student portal; out of scope for the dataset."),
    ("04", "Instalment (3Pay) and refund application forms", "Restricted", "webapp forms require student details - "
     "not accessed.", RS, "Finance; out of scope."),
    ("05", "Examination regulations and grading appeals", "Unavailable", "Not in the documents or pages collected.",
     DD, "Registrar / Academic Catalog 2024-2026."),
    ("05", "Graduation requirements (units, GPA)", "Unavailable", "Commencement page gives logistics only.", DD,
     "Registrar / Academic Catalog."),
    ("05", "Transcript and certificate fees and procedure", "Partially available", "Tuition page: transcript 1,000; "
     "handbook: procedure.", UC, "Registrar."),
    ("05", "Pre-registration check (Fall 2026) content", "Unavailable", "Page shows a heading only.", TW,
     "Re-check the page; content may be loaded by script."),
    ("05", "Results slips / individual results", "Restricted", "Student portal.", RS, "Out of scope (private data)."),
    ("06", "Correct Library and Registrar telephone country code (W04)", "Available, probably wrong", "+257 printed.",
     UC, "Registrar / Library / web team."),
    ("06", "Finance telephone numbers students should use (W06)", "Available, conflicting", "Four sets.", UC, "Finance."),
    ("06", "Office working hours (other than counselling, library, disability office)", "Unavailable", "", DD,
     "Each office."),
    ("06", "Escalation procedure for unresolved enquiries", "Unavailable", "", DD, "Student Affairs / Quality Assurance."),
    ("06", "Academic advisors' contacts (CSOB, SST, SPHS, SHSS, SCCCA)", "Partially available",
     "Contact Us lists advisors without numbers.", UC, "Schools."),
    ("07", "Foreign-qualification equation procedure (CUE)", "Unavailable", "CUE site failed TLS (inaccessible).", TW,
     "Retry https://www.cue.or.ke/ in a later run; label as external."),
    ("07", "National qualification levels (KNQA)", "Unavailable", "KNQA returned HTTP 500.", TW, "Retry later; external."),
    ("07", "English proficiency minimum (W14 / V16)", "Available, conflicting (three versions)", "", UC, "Admissions."),
    ("07", "Programme cluster-subject requirements for every programme", "Partially available",
     "programme_entry_requirements.csv (some pages silent).", DD, "Schools / Admissions."),
    ("08", "Real student questions, answers and enquiry references", "Not collected (by design)",
     "No real enquiry logs were provided; none were invented.", RS,
     "Would come from the live chatbot's enquiry records after deployment, under data-protection rules."),
    ("all", "Publication dates of web pages", "Unavailable", "No page states a publication date; sitemap lastmod is "
     "recorded separately and is not a publication date.", UC, "Web team."),
    ("all", "Dated, current Student Handbook (V07, V23)", "Unavailable", "Local handbook is undated; public URL 404.",
     ND, "Dean of Students / Registrar to provide the current edition."),
]

# Category 08: open questions derived from the dataset's own conflicts and gaps.
# (id, question, issue/gap ids, route to, what the chatbot can safely say meanwhile)
OPEN_QUESTIONS = [
    ("Q08-001", "Which bank accounts should students use to pay fees?", "V01; V02; V03; W26", "finance",
     "Quote that payment details differ between official sources and refer the student to the Finance Office "
     "(finance@usiu.ac.ke) to confirm before paying."),
    ("Q08-002", "What share of fees is waived if a course is dropped, and until when?", "V04", "finance",
     "Refer to Finance / Registrar; the handbook and calendar differ."),
    ("Q08-003", "How long does the 1.5% monthly interest on fee balances run?", "V28", "finance",
     "State the 1.5% per month rate from the 2nd day of the semester (website) and refer to Finance for duration."),
    ("Q08-004", "What is the minimum English proficiency score (TOEFL) for undergraduate admission?", "V16; W14",
     "admissions", "Quote the Admission Requirements page (TOEFL iBT 79) as the current web version, mention that other "
     "documents differ, and refer to Admissions."),
    ("Q08-005", "How many credits can a transfer student bring, and how many must be taken at USIU-Africa?", "W11",
     "registrar", "Quote both pages and refer to Admissions / Registrar."),
    ("Q08-006", "How much does on-campus accommodation cost per semester?", "W13", "student_affairs",
     "Quote the 2026-2027 fee schedule (Room Only 42,000 per semester) and note the Housing FAQ figure; refer to "
     "the Housing Office."),
    ("Q08-007", "Who qualifies for the Family Tuition Waiver?", "W12", "financial_aid",
     "Quote both versions and refer to Financial Aid."),
    ("Q08-008", "What are the admission requirements for the doctoral programmes?", "W23", "admissions",
     "Say the programme pages do not state them; refer to Admissions."),
    ("Q08-009", "What are the correct telephone numbers for the Registrar and the Library?", "W04", "registrar",
     "Give the e-mail addresses (registrar@usiu.ac.ke, library@usiu.ac.ke) and note the printed numbers carry +257."),
    ("Q08-010", "Which Finance telephone number should students call?", "W06", "finance",
     "Give finance@usiu.ac.ke and the numbers as printed on each page."),
    ("Q08-011", "Can cash be paid at the university?", "W09", "finance",
     "Quote both statements and refer to Finance; recommend bank or M-PESA paybill as printed."),
    ("Q08-012", "Does KUCCPS place government-sponsored students at USIU-Africa?", "W24", "admissions",
     "Do not answer from KUCCPS pages; refer to Admissions."),
    ("Q08-013", "Which drug-offence sanction applies under the student code?", "V08", "student_affairs",
     "Quote both handbook provisions and refer to the Dean of Students."),
    ("Q08-014", "Is the Student Handbook copy current, and where is the official version?", "V06; V07; V23",
     "student_affairs", "Say the available copy is undated and refer to the Dean of Students / Registrar."),
    ("Q08-015", "Which graduation year do Fall 2026 completers belong to?", "V17", "registrar",
     "Quote the calendar entries and refer to graduation@usiu.ac.ke."),
    ("Q08-016", "What are the Health Center and counselling numbers?", "V12; V13", "student_affairs",
     "Give the Health & Wellness page numbers and counsel@usiu.ac.ke."),
    ("Q08-017", "What is the University Security number?", "V14", "security",
     "Give 0730 116 266 / 0730 116 461 (2026 Commencement page) and note the handbook differs."),
    ("Q08-018", "Are the programmes listed only in the fee schedule (e.g. BA Sociology) open for application?", "W19",
     "admissions", "Refer to Admissions."),
    ("Q08-019", "What are the entry requirements for the online MA Communication Studies, MA Criminal and "
     "Transitional Justice and online MA International Relations?", "W18", "admissions",
     "Say the pages contain apparent errors; refer to Admissions."),
    ("Q08-020", "What is the calendar date of 'September 16 Friday' in the 2026-2027 calendar?", "V20", "registrar",
     "Say the printed weekday does not match the date and refer to the Registrar."),
    ("Q08-021", "What examination regulations and appeal procedures apply?", "gap: 05 examination regulations",
     "registrar", "Refer to the Registrar / Academic Catalog 2024-2026."),
    ("Q08-022", "What are the application deadlines for the next intake?", "gap: 03 application deadlines", "admissions",
     "Say the Intake page shows the January (Spring) 2027 intake as ongoing; refer to Admissions for deadlines."),
]

# Routing departments. app_department = the closest existing USIUBOT enquiry department (the app has five:
# admissions, registrar, marketing, academic_programmes, general_university). The app is NOT changed.
ROUTING = {
    "admissions": {"label": "Admissions Office", "app_department": "admissions",
                   "keywords": ["apply", "application", "admission", "intake", "requirements", "KCSE", "transfer",
                                "international applicant", "Pupil's Pass", "placement test"]},
    "registrar": {"label": "Office of the Registrar", "app_department": "registrar",
                  "keywords": ["transcript", "registration", "add/drop", "graduation", "clearance", "leave of absence",
                               "academic records", "calendar", "examination"]},
    "finance": {"label": "Finance Office (Student Accounts, Credit Control)", "app_department": "general_university",
                "app_gap": "The app has no Finance department; until one is added (application change, not done), "
                           "finance enquiries fall back to general_university with this routing note.",
                "keywords": ["fees", "tuition", "payment", "bank", "M-PESA", "paybill", "refund", "balance",
                             "instalment", "3Pay", "interest", "receipt"]},
    "financial_aid": {"label": "Financial Aid Office", "app_department": "admissions",
                      "app_gap": "Handbook page 16: the Admissions department administers the financial aid program.",
                      "keywords": ["scholarship", "grant", "waiver", "HELB", "work study", "CWOP", "financial aid"]},
    "academic_programmes": {"label": "Schools and academic programmes (Deputy Vice Chancellor, Academic Affairs)",
                            "app_department": "academic_programmes",
                            "keywords": ["programme", "course", "school", "curriculum", "duration", "mode of study",
                                         "online programme", "CBET"]},
    "marketing": {"label": "Marketing and Communications", "app_department": "marketing",
                  "keywords": ["website", "media", "events", "yearbook", "social media"]},
    "student_affairs": {"label": "Student Affairs (Dean of Students, Housing, Counselling, Health, Disability, "
                                 "Student Life)", "app_department": "general_university",
                        "app_gap": "No Student Affairs department in the app.",
                        "keywords": ["housing", "hostel", "room", "counselling", "health", "clinic", "disability",
                                     "clubs", "discipline", "insurance"]},
    "ict": {"label": "ICT Helpdesk", "app_department": "general_university", "app_gap": "No ICT department in the app.",
            "keywords": ["email account", "portal login", "password", "Wi-Fi", "printing account", "MyQ"]},
    "library": {"label": "Library and Information Center", "app_department": "general_university",
                "app_gap": "No Library department in the app.",
                "keywords": ["library", "books", "loan", "e-resources", "library fines", "membership"]},
    "careers": {"label": "Placement and Careers", "app_department": "general_university",
                "keywords": ["internship", "jobs", "career", "attachment"]},
    "alumni": {"label": "Alumni Relations", "app_department": "general_university",
               "keywords": ["alumni", "alumni card", "legatee"]},
    "security": {"label": "University Security", "app_department": "general_university",
                 "keywords": ["security", "emergency", "lost and found"]},
    "general_university": {"label": "General University Information (main lines)", "app_department": "general_university",
                           "keywords": []},
}

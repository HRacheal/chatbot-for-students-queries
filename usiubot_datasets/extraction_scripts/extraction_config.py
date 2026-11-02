"""Configuration and curated reference data for the Stage 2 extraction.

Everything here describes the two local PDFs. Nothing in this file is university
information that is not printed in those PDFs:

* Every curated structured row carries an ``evidence`` quote. extract_documents.py
  checks that each quote occurs, word for word (whitespace normalised), on the stated
  page of the stated PDF and stops with an error if it does not.
* Processing notes written during extraction are kept in separate ``notes`` /
  ``processing_notes`` fields and are never mixed into the extracted content.
"""

EXTRACTION_TOOL = "pypdf (text layer only; no OCR)"

# SHA-256 of the original PDFs, recorded on 2026-11-01 before any Stage 2 work.
BASELINE_SHA256 = {
    "Academic-Calendar-2026-2027.pdf": "618711f96eb9efd55d744341175a0b39a75087e8d2c8f692340bc0bb9067512f",
    "Student-Handbook.pdf": "610a3da82992e0c392ac69c317cbf1bd99679313acce8090fab3b9924ef87c15",
}

INSTITUTION = "United States International University-Africa (USIU-Africa)"

CATEGORIES = {
    "01": ("01_general_university_information", "General University Information"),
    "02": ("02_academic_programmes", "Academic Programmes"),
    "03": ("03_admissions_and_applications", "Admissions and Applications"),
    "04": ("04_fees_and_payments", "Fees and Payments"),
    "05": ("05_registrar_and_academic_administration", "Registrar and Academic Administration"),
    "06": ("06_department_contacts_and_query_routing", "Department Contacts and Query Routing"),
    "07": ("07_academic_documents_results_and_verified_eligibility",
           "Academic Documents, Results and Verified Eligibility"),
    "08": ("08_questions_answers_and_unresolved_enquiries", "Questions, Answers and Unresolved Enquiries"),
}

CAL = "usiu_academic_calendar_2026_2027"
HB = "usiu_student_handbook"

DOCUMENTS = {
    CAL: {
        "file": "Academic-Calendar-2026-2027.pdf",
        "title": "USIU-Africa Academic Calendar 2026-2027",
        "academic_year": "2026-2027",
        "academic_year_basis": "Printed on the cover (page 1): 'ACADEMIC CALENDAR 2026 2027'.",
        "publication_date": "Not stated in the document",
        "source_url": "https://www.usiu.ac.ke/wp-content/uploads/2026/04/Academic-Calendar-2026-2027.pdf",
        "source_url_status": "Confirmed 2026-11-01: the file at this official URL has the same SHA-256 as the local copy "
                             "(landing page https://www.usiu.ac.ke/documents/academic-calendar-2026-2027/)",
        "candidate_source_url": None,
        "candidate_source_note": "Resolved (issue V22): downloaded from the official website on 2026-11-01 and "
                                 "compared byte for byte with the local copy.",
        "printed_page_numbers": False,
    },
    HB: {
        "file": "Student-Handbook.pdf",
        "title": "USIU-Africa Student Handbook",
        "academic_year": "Not stated in the document",
        "academic_year_basis": "No academic year or edition is printed. The latest year mentioned in the "
                               "text is 2024 ('valid as at May 2024', page 9).",
        "publication_date": "Not stated in the document",
        "source_url": None,
        "source_url_status": "Local copy — no public official URL found (candidate URL returns HTTP 404, 2026-11-01)",
        "candidate_source_url": "https://www.usiu.ac.ke/assets/file/266ac45d-student-handbook.pdf",
        "candidate_source_note": "Listed in backend/config/official_pages.json as 'Student Handbook - Nairobi' "
                                 "(reviewed: false). Not confirmed to be the same file as the local copy: "
                                 "it was not downloaded or compared in Stage 2. Re-checked 2026-11-01: the URL returns HTTP 404.",
        "printed_page_numbers": True,
    },
}

# --------------------------------------------------------------------------------------
# Student Handbook layout handling
# --------------------------------------------------------------------------------------
HB_SKIP_PAGES = {3}  # table of contents (recorded in document metadata instead)

# Table of contents (page 3) as printed, and where each section actually starts.
HB_TOC = [
    ("VICE CHANCELLORS MESSAGE", 5, 5),
    ("MISSION, VISION AND CORE VALUES", 7, 7),
    ("FEES AND FEE PAYMENT POLICY", 9, 9),
    ("REGISTRATION AND ACADEMIC INFORMATION", 13, 13),
    ("STUDENT LIFE", 15, 15),
    ("POLICIES AND REGULATIONS FOR STUDENT ACTIVITIES", 25, 25),
    ("THE UNIVERSITY LIBRARY AND INFORMATION CENTER", 27, 27),
    ("INFORMATION AND COMMUNICATION TECH. (ICT)", 31, 31),
    ("USIU - ONLINE", 35, 35),
    ("THE STUDENT CODE OF CONDUCT: NON-ACADEMIC", 37, 37),
    ("STUDENT SUPPORT AND AUXILIARY SERVICES", 49, 49),
    ("CAMPUS SAFETY AND SECURITY", 53, 53),
    ("UNIVERSITY COMMUNICATION", 57, 57),
    ("ALUMNI RELATIONS OFFICE", 58, 59),
]

# Lines removed from the text stream because they are layout artefacts (the heading is
# recorded as section metadata instead). Compared after whitespace normalisation.
HB_DROP_LINES = {
    6: ["1.1 MESSAGE FROM THE DEPUTY VICE CHANCELLOR,", "STUDENT LIFE"],
    31: ["(ICT)"],
}

# Editorial placeholders printed in the PDF. Removed from content, recorded as flags/issues.
HB_PLACEHOLDERS = {15: "MISSING INFOMATION", 49: "TABLE TO BE INSERTED"}

# Sections that start at the top of a page without a numbered heading in the text layer
# (their heading is printed elsewhere on the page or not at all).
HB_FORCED_STARTS = [
    {"page": 1, "number": "cover", "heading": "Cover page: accreditation statement"},
    {"page": 5, "number": "1.0", "heading": "Vice Chancellor's Message"},
    {"page": 6, "number": "1.1", "heading": "Message from the Deputy Vice Chancellor, Student Life"},
    {"page": 7, "number": "2", "heading": "Mission, Vision and Core Values; Our Schools",
     "note": "Section number not printed in the handbook (table of contents: 'MISSION, VISION AND CORE VALUES')."},
    {"page": 13, "number": "4.0", "heading": "Registration and Academic Information (introduction)"},
    {"page": 15, "number": "5.0", "heading": "Student Life (introduction)"},
    {"page": 31, "number": "8.0", "heading": "Information and Communication Technology (ICT) (introduction)"},
    {"page": 35, "number": "9.0", "heading": "USIU-Online (introduction)"},
    {"page": 53, "number": "12.0", "heading": "Campus Safety and Security"},
    {"page": 57, "number": "13.0", "heading": "University Communication"},
    {"page": 59, "number": "14.0", "heading": "Alumni Relations Office"},
    {"page": 60, "number": "contact", "heading": "Contact Us"},
]

# Unnumbered sub-headings used as section boundaries (12.0 has no numbered subsections).
HB_EXTRA_HEADINGS = [
    {"page": 54, "startswith": "Lost and Found items", "number": "12.0", "heading": "Lost and Found items"},
    {"page": 54, "startswith": "Motor Vehicle Parking Management", "number": "12.0",
     "heading": "Motor Vehicle Parking Management"},
    {"page": 54, "startswith": "Photos and Videos", "number": "12.0", "heading": "Photos and Videos"},
    {"page": 54, "startswith": "Reporting Security incidents", "number": "12.0",
     "heading": "Reporting Security incidents"},
    {"page": 54, "startswith": "General Guidelines on security of self and", "number": "12.0",
     "heading": "General Guidelines on security of self and Possessions", "continuation": "Possessions"},
    {"page": 55, "startswith": "Guidelines for Fire Safety:", "number": "12.0",
     "heading": "Guidelines for Fire Safety", "inline": True},
    {"page": 55, "startswith": "Campus Security Policy and Standard", "number": "12.0",
     "heading": "Campus Security Policy and Standard Operating Procedures", "continuation": "Operating Procedures"},
]

# Text that the two-column layout places in the wrong position of the text layer. Each
# segment (first line starting with ``start``, through the line equal to ``end``) is moved
# to the end of section ``to``. The section gets a 'reconstructed_from_two_column_layout' flag.
HB_RELOCATIONS = [
    {"page": 10, "start": "U.S Correspondent/Intermediary bank name", "end": "5. Enter your PIN and click send.",
     "to": "3.4", "reason": "Continuation of the 3.4 bank list printed in the right-hand column of page 10."},
    {"page": 16, "start": "Student Life Division has seven departments", "end": "7. The Office of Disability and Inclusion",
     "to": "5.0", "reason": "Boxed list of Student Life departments printed at the foot of page 16; it continues "
                            "'Departments under the Student Life Division' on page 15."},
]

# Pages whose text blocks come out of the text layer in a different order from the printed
# layout. Each block (label, first line starts with, last line equals) is emitted in this
# order, under its printed heading. Every line of the page must be used exactly once.
HB_PAGE_READING_ORDER = {
    7: {
        "drop": ["OUR VISION", "OUR MISSION", "CORE", "VALUES", "OUR SCHOOLS"],
        "blocks": [
            ("OUR VISION", "To be a premier institution of", "perspective."),
            ("OUR MISSION", "Promote the discovery and application", "increasingly technological world."),
            ("CORE VALUES", "Life-long learning", "knowledge."),
            ("OUR SCHOOLS", "• Chandaria School of Business (CSOB)", "• School of Graduate Studies (SGS)"),
        ],
        "note": "Page 7 prints its headings (OUR VISION, OUR MISSION, CORE VALUES, OUR SCHOOLS) apart from their "
                "text. The text blocks were put under the headings in layout order; no words were changed. "
                "Check against the PDF (issue V24).",
    },
}

# Full heading text where the printed heading wraps onto a second line.
HB_HEADING_OVERRIDES = {
    "3.7": "USIU–Africa Hostels Room & Board Payments",
    "3.8": "Institutional Charge Waiver/ Refund Policy",
    "3.9": "Procedure for Withdrawing/Requesting a Charge Waiver",
    "3.14": "Other services offered by the Finance Office",
    "4.2": "Disclosure and Change of Student Information",
    "5.2.6": "General Provisions on Financial Aid Policy and Regulations",
    "5.2.7": "Financial Aid Programs for Undergraduate Students",
    "5.2.8": "Financial Aid Programs for Graduate Students",
    "5.2.9": "Financial Aid Programs for Undergraduate and Graduate Students",
    "5.2.10": "Externally Funded Financial Aid Programs",
    "5.5.1": "Services provided at the Counseling Center include: -",
    "5.5.2": "HIV Counseling and Testing - The HIV/ VCT",
    "5.7.1": "Supporting Students with Disabilities and Special Needs (SWD & SN)",
    "5.7.2": "The University’s Commitment to Supporting SWD & SN Will Be:",
    "5.7.4": "Students with Disability: SWD & other SN’s Responsibilities",
    "5.9": "The Placement and Career Services Department",
    "6.1": "Guidelines on Posters and Use of Official Electronic Media on Campus",
    "6.1.1": "Use of Surfaces, Bulletin Boards & Spaces",
    "6.2": "Policy on Use of University Facilities or Services",
    "6.2.1": "Guidelines Apply When Reserving A Facility (Open Spaces and Sports Fields)",
    "7.2": "Library and Information System Access and Support",
    "8.8": "Bring Your Device (BYOD) Guidelines on Campus.",
    "10.2": "University Disciplinary Authority Promotes",
    "10.8": "Scope, Authority, and Jurisdiction on Discipline",
    "10.12": "Order of Proceedings at Disciplinary Hearings.",
    "10.15": "Littering, Graffiti, and Public Nuisance/ Disturbance",
    "10.16.1": "Complaints against the University or an Employee",
    "10.16.8": "Maintaining a Written Record of the Grievance",
    "10.17": "Sexual and Gender-Based Violence Policy",
    "10.17.2": "Sexual and Gender-Based Violence Assault",
    "10.17.3": "What should you do if you are a victim of sexual assault?",
    "11.4": "Insurance Services",
}

# Major section heading as printed in the table of contents (used for parent headings).
HB_MAJOR_HEADINGS = {
    "cover": "Cover page", "1": "VICE CHANCELLOR’S MESSAGE", "2": "MISSION, VISION AND CORE VALUES",
    "3": "FEES AND FEE PAYMENT POLICY", "4": "REGISTRATION AND ACADEMIC INFORMATION", "5": "STUDENT LIFE",
    "6": "POLICIES AND REGULATIONS FOR STUDENT ACTIVITIES", "7": "THE UNIVERSITY LIBRARY AND INFORMATION CENTER",
    "8": "INFORMATION AND COMMUNICATION TECHNOLOGY (ICT)", "9": "USIU-ONLINE",
    "10": "THE STUDENT CODE OF CONDUCT: NON-ACADEMIC", "11": "STUDENT SUPPORT AND AUXILIARY SERVICES",
    "12": "CAMPUS SAFETY AND SECURITY", "13": "UNIVERSITY COMMUNICATION", "14": "ALUMNI RELATIONS OFFICE",
    "contact": "CONTACT US",
}


def hb_category(number):
    """Dataset category for a handbook section number (see category READMEs for the reasoning)."""
    if number in ("5.2", "5.2.1", "5.2.2", "5.2.3"):
        return "03"  # admissions, re-admission, returning graduates
    if number.startswith("5.2."):
        return "04"  # financial aid office, eligibility and programmes
    major = number.split(".")[0]
    return {
        "cover": "01", "1": "01", "2": "01", "3": "04", "4": "05", "5": "01", "6": "01", "7": "01",
        "8": "01", "9": "02", "10": "01", "11": "01", "12": "01", "13": "06", "14": "01", "contact": "06",
    }[major]


# Calendar pages: (page, section heading, category). Page 1 is the cover (title only).
CAL_PAGES = [
    (2, "Fall Semester 2026", "01"),
    (3, "Spring Semester 2027", "01"),
    (4, "Summer Semester 2027", "01"),
    (5, "Payment Information: wire transfer and bank deposit", "04"),
    (6, "Mobile Money Payments (M-PESA) and payment purpose codes", "04"),
    (7, "Contacts", "06"),
]
CAL_SEMESTER_YEARS = {2: 2026, 3: 2027, 4: 2027}

# --------------------------------------------------------------------------------------
# Curated structured records. ``evidence`` must occur on ``page`` of ``doc``.
# --------------------------------------------------------------------------------------
UNIVERSITY_PROFILE = [
    {"field": "accreditation", "doc": HB, "page": 1, "section": "cover",
     "evidence": "USIU-Africa is accredited in Kenya by the Commission for University Education (CUE) & the "
                 "United States of America by WASC Senior College and University Commission respectively"},
    {"field": "description", "doc": HB, "page": 5, "section": "1.0",
     "evidence": "one of the oldest private, secular universities in East Africa and among the few institutions "
                 "on the continent with dual accreditation"},
    {"field": "vision", "doc": HB, "page": 7, "section": "2",
     "evidence": "To be a premier institution of academic excellence with a global perspective.",
     "notes": "The page prints headings and text in separate blocks; this text is assigned to 'OUR VISION' "
              "because it is the first text block and VISION is the first heading. Verify against the PDF layout."},
    {"field": "mission", "doc": HB, "page": 7, "section": "2",
     "evidence": "Promote the discovery and application of knowledge, the acquisition of skills and the "
                 "development of intellect and character in a manner which prepares students to contribute "
                 "effectively and ethically as citizens of a changing and increasingly technological world.",
     "notes": "Assigned to 'OUR MISSION' by layout order (second text block). Verify against the PDF layout."},
    {"field": "core_value: Life-long learning", "doc": HB, "page": 7, "section": "2",
     "evidence": "Life-long learning Developing a learning culture that continues throughout a person’s lifetime."},
    {"field": "core_value: Integrity", "doc": HB, "page": 7, "section": "2",
     "evidence": "Integrity Ensuring the pursuit of excellence by upholding professional and ethical standards "
                 "and being accountable."},
    {"field": "core_value: Innovativeness", "doc": HB, "page": 7, "section": "2",
     "evidence": "Innovativeness Introducing new methods and strategies that ensure quality, efficiency, "
                 "effectiveness and productivity."},
    {"field": "core_value: Social responsibility", "doc": HB, "page": 7, "section": "2",
     "evidence": "Social responsibility Providing leadership in responding to issues of national and global "
                 "concern through collaborative efforts."},
    {"field": "core_value: Academic freedom", "doc": HB, "page": 7, "section": "2",
     "evidence": "Academic freedom Upholding the spirit of free and critical thought and enquiry, through open "
                 "exchange of ideas and knowledge."},
    {"field": "leadership: Vice Chancellor (as printed)", "doc": HB, "page": 5, "section": "1.0",
     "evidence": "PROF . MWENDA NTARANGWI Vice Chancellor", "issues": ["V25"]},
    {"field": "leadership: Deputy Vice Chancellor, Student Life (as printed)", "doc": HB, "page": 6, "section": "1.1",
     "evidence": "DR. VICTOR BOIYO Deputy Vice Chancellor, Student Life", "issues": ["V25"]},
    {"field": "postal and physical address", "doc": HB, "page": 60, "section": "contact",
     "evidence": "P .O. Box 14634-00800 USIU Road, Off Thika Road (Exit 7) Nairobi, Kenya"},
    {"field": "student diversity", "doc": HB, "page": 20, "section": "5.4.4",
     "evidence": "USIU-Africa is home to over 70 nationalities."},
    {"field": "on-campus hostel", "doc": HB, "page": 18, "section": "5.3",
     "evidence": "The priority is given to international students in the 258 capacities on campus hostel. "
                 "The rooms offer double occupancy and are connected to Wi-Fi."},
    {"field": "alumni association", "doc": HB, "page": 59, "section": "14.0",
     "evidence": "The Alumni Association is a registered society as of April 1990"},
    {"field": "sports facilities", "doc": HB, "page": 19, "section": "5.4.1.1",
     "evidence": "These include fields, coats, pitches, an Olympic-sized swimming pool, and a fully equipped "
                 "state-of-the-art gym."},
]

SERVICE_HOURS = [
    ("Library", "During the Semester", "Monday to Friday", "8.15 am - 9.00 p.m.", 29, "7.5",
     "Monday to Friday: 8.15 am - 9.00 p.m."),
    ("Library", "During the Semester", "Saturday", "9.00 a.m. - 6.00 p.m.", 29, "7.5", "Saturday: 9.00 a.m. - 6.00 p.m."),
    ("Library", "During the Semester", "Sunday", "11.00 a.m. - 5.00 p.m.", 29, "7.5", "Sunday: 11.00 a.m. - 5.00 p.m."),
    ("Library", "During the Semester", "Public Holidays", "CLOSED", 29, "7.5", "Public Holidays: CLOSED"),
    ("Library", "During the Academic Breaks", "Monday to Friday", "8.15 am - 5.00 p.m.", 29, "7.5",
     "Monday to Friday: 8.15 am - 5.00 p.m."),
    ("Library", "During the Academic Breaks", "Saturday", "CLOSED", 29, "7.5", "Saturday: CLOSED"),
    ("Library", "During the Academic Breaks", "Sunday", "CLOSED", 29, "7.5", "Sunday: CLOSED"),
    ("Library", "During the Academic Breaks", "Public Holidays", "CLOSED", 29, "7.5", "Public Holidays: CLOSED"),
    ("Library (Sunday short loans and circulating materials)", "Not stated", "Sunday", "11.00 a.m. to 4.30 p.m.",
     28, "7.3.4", "Issuing of short loans and circulating materials on Sundays begins at 11.00 a.m. to 4.30 p.m."),
    ("AskaLibrarian Live Chat", "Not stated", "every day of the week", "8:00 am to 9:00 pm", 29, "7.6",
     "AskaLibrarian Live Chat (8:00 am to 9:00 pm every day of the week)"),
    ("Health Center", "All year except the December holidays", "7 days a week", "24 hours a day", 50, "11.3",
     "The health Center is open 24 hours a day 7 days a week including public holidays & school holidays except "
     "during the December holidays when the University is fully closed."),
    ("Counseling Center", "Not stated", "Not stated", "during working hours (hours not stated)", 20, "5.5.1",
     "Counselors are available during working hours, but appointments with the Counseling assistant are "
     "recommended for timeliness."),
]

LIBRARY_LOANS = [
    ("Faculty", "15 books", "a month", "Faculty 15 books for a month"),
    ("Staff", "6 books", "2 weeks", "Staff 6 books for 2 weeks"),
    ("Doctorate", "15 books", "a month", "Doctorate 15 books for a month"),
    ("Students", "10 books", "2 weeks", "Students 10 books for 2 weeks"),
    ("Alumni", "2 books", "2 weeks", "Alumni 2 books for 2 weeks"),
    ("Others", "No borrowing", "-", "Others No borr owing"),
    ("All registered members (audio-visual materials)", "not stated", "two (2) days",
     "All registered members may borrow audio-visual materials for two (2) days."),
]

ADMISSION_CONDITIONS = [
    ("Transfer admission", "5.2.1", 16,
     "Transfer Admission: All credit transfers are subject to approval by the Academic Dean or designee."),
    ("Admission tests", "5.2.1", 16, "Admission Tests: New students will be guided on the requisite admission requirements."),
    ("Re-admission", "5.2.2", 16,
     "Unless students are away on an approved leave of absence when they resume, they should apply for "
     "re-admission and pay a non-refundable application processing fee."),
    ("Leave of absence limit", "5.2.2", 16,
     "Leave of absence is allowed for a maximum of one academic year (i.e., three semesters)."),
    ("Re-admitted students", "5.2.2", 16,
     "Students who are re-admitted will be treated as new students and the Dean or designee will evaluate their "
     "transcripts based on current curriculum and admission requirements."),
    ("Returning USIU-Africa graduates", "5.2.3", 16,
     "Students who have completed USIU’s degree, certificate, or credential program must apply for another "
     "program, with a non-refundable application processing fee charged for them to be considered."),
    ("Conditional admission", "5.2.3", 16,
     "Conditionally admitted students must submit necessary documents within the first semester of study, or they "
     "will be denied further registration."),
    ("International students", "5.4.4", 20,
     "All International students are advised to visit the University website and access the International "
     "Students Handbook"),
]

ENGLISH_REQUIREMENTS = [
    # (test as printed, minimum, rule wording)
    ("TOEFL (test format not named; 'TOEFL test score')", "550", "or higher"),
    ("TOEFL computer-based test", "213", "or higher"),
    ("TOEFL Internet Based Test", "90", "or higher"),
    ("Cambridge Test of English Proficiency", "grade C", "or better"),
    ("IELTS", "6", "or better"),
]
ENGLISH_EVIDENCE = ("Applicants from non-English speaking countries are required to submit a current TOEFL test "
                    "score of 550 (213 in the computer-based test or 90 in the Internet Based Test) or higher, a "
                    "Cambridge Test of English Proficiency grade C or better, or an IELTS score of 6 or better.")

FINANCIAL_AID = [
    # (programme as printed, eligible level as printed by section, section, page)
    *[(p, "Undergraduate", "5.2.7", 17) for p in (
        "Full USIU Scholarship", "Criminal Justice Scholarship", "Alumni Scholarship", "Partial Scholarship",
        "Freshman Scholarship for Kenyans", "Campus Work Opportunity (CWO)", "Sports Scholarship",
        "Resident Assistant (RA)", "Diversity Scholarship", "Student Council Grant",
        "The Vice Chancellor’s Grant for Undergraduate Students")],
    *[(p, "Graduate", "5.2.8", 17) for p in ("Graduate Alumni Waiver", "Graduate Assistant (GA)", "Sports Scholarship")],
    *[(p, "Undergraduate and Graduate", "5.2.9", 17) for p in (
        "Special Need Grant", "Family Tuition Discount Award (10% Tuition Discount)",
        "USIU Alumni Discount Award (10% Tuition Discount)")],
    *[(p, "Externally funded", "5.2.10", 18) for p in (
        "Rattansi Education Trust Fund Grant", "Higher Education Loans Board (HELB) www.helb.co.ke",
        "Mastercard Foundation Scholars Programme")],
]

FEE_RULES = [
    # (topic, section, page, evidence = the rule as printed)
    ("Fee payment deadline", "3.2", 9,
     "Students must pay fees on or before the first day of each semester, based on admission fees."),
    ("Outstanding fees and pre-registration", "3.2", 9, "Students with outstanding fees will not access pre-registration services"),
    ("Withholding of grades, transcripts and diplomas", "3.2", 9,
     "The University can withhold grades, transcripts, and diplomas for outstanding financial obligations and "
     "withdraw registration for non-payment."),
    ("Unspecified payments", "3.2", 9,
     "Any payment made to the University’s bank account will be considered as tuition fees unless otherwise specified."),
    ("Commencement fees", "3.2", 9,
     "Students attending the Commencement Ceremony must pay full fees, including graduation and gown deposit charges."),
    ("Cash payments", "3.2", 9,
     "USIU-Africa does not allow cash payments however, a special concession for library fines up to 1000 shillings is allowed."),
    ("Interest on balances (section 3.2)", "3.2", 9,
     "Students with outstanding balances and those with approved payment plans will be charged a monthly interest "
     "of 1.5% on outstanding balances until they are fully paid."),
    ("Returned cheques", "3.3", 9,
     "Students with a history of bad or returned checks will face a 10% charge of Kshs. 1000 to Kshs. 5,000.00 on "
     "all returned or unpaid checks."),
    ("Payment details validity", "3.4", 9, "3.4 Payment Information (valid as at May 2024 )"),
    ("Payment identification", "3.5", 10,
     "Students must provide their full names and USIU-Africa ID number when making payments, and all bank deposits "
     "must be received the next working day."),
    ("Financial clearance", "3.6", 10,
     "Those with outstanding fees and no approved payment plan will be placed on financial hold to prevent access "
     "to grades and semester registration."),
    ("Hostel deposits", "3.7", 10, "A room key deposit and reservation charges are refundable upon leaving the hostel."),
    ("Drop charge waiver: before semester", "3.8", 10,
     "100% charge waiver if officially recorded before the first day of the semester."),
    ("Drop charge waiver: first 7 days", "3.8", 10,
     "90% charge waiver if officially recorded within seven calendar days of the first day of the semester."),
    ("Drop charge waiver: first 14 days", "3.8", 10,
     "75% charge waiver if officially recorded within 14 calendar days of the first day of the semester."),
    ("Drop charge waiver: after 14 days", "3.8", 10,
     "If recorded after 14 calendar days of the first day of the semester the course will be charged a full fee."),
    ("Add/Drop fee start", "3.8 (note)", 11,
     "The Add/Drop Fee per course is charged from the first day of the second week of the semester."),
    ("Late registration fee start", "3.8 (note)", 11,
     "The Late Registration Fee is a fixed fee that starts on the second day of the second week of the semester."),
    ("Medical insurance waiver limit", "3.9", 11,
     "Student Medical Insurance (non-refundable after the second week of the semester)"),
    ("Deferred Payment Plan availability", "3.10", 11,
     "The Deferred Payment Plan is available to Kenyan students and international students at the University’s discretion."),
    ("Number of instalments", "3.10", 11, "Continuing students and freshmen can make up to two equal installment payments."),
    ("Registration with instalments", "3.10", 11,
     "Freshmen can register after paying 50% of fees while continuing students must pay the first installment, "
     "register, and get approval from the Credit Control Office."),
    ("Second instalment due date", "3.10", 11, "The second 50% installment plus interest is due on the 7th day of the second month."),
    ("Payment plan application deadline", "3.10", 11,
     "Application for the payment plan should be submitted by the 2nd week of every semester"),
    ("Interest on balances (section 3.11)", "3.11", 11,
     "Fees not paid on or before the first day of the semester are considered outstanding and attract an interest "
     "of 1.5% per month for up to 10 months, with interest stopped once the student resumes payments."),
    ("Refund eligibility", "3.12", 11, "Refunds are given to graduates or students leaving the university."),
    ("Refund processing", "3.12", 11, "shall be processed monthly"),
    ("Unclaimed balances", "3.12", 11,
     "Excess/overpaid fees, caution, and gown deposit fees will be submitted to UFAA if not claimed two years after graduation."),
    ("Debt collection", "3.13", 12,
     "Students must pay fees on time, and overdue debts will be sent to external debt collectors for recovery."),
    ("Disciplinary suspension and refunds", "10.4", 38,
     "No refunds will be made to students who are suspended or dismissed from the University for Disciplinary Reasons."),
]

# Bank and payment channel details. HIGH-RISK data: see issues V01-V03.
BANK_DETAILS = [
    # (id, doc, page, bank as printed, branch, currency, account number, account name as printed,
    #  codes as printed, evidence)
    ("BANK-CAL-01", CAL, 5, "NCBA BANK KENYA LTD", "UPPER HILL BRANCH, MARA & RAGATI ROADS", "KES", "6438840014",
     "USIU or U.S. International University", "SWIFT Code:CBAFKENX", "Kenya Shillings Account Number:6438840014"),
    ("BANK-CAL-02", CAL, 5, "NCBA BANK KENYA LTD", "UPPER HILL BRANCH, MARA & RAGATI ROADS", "USD", "6462210014",
     "USIU or U.S. International University", "SWIFT Code:CBAFKENX; Intermediary Bank: JP Morgan Chase Bank, New York, "
     "SWIFT Code:CHASUS33", "US Dollar Account Number:6462210014"),
    ("BANK-CAL-03", CAL, 5, "Co-Operative Bank Of Kenya", "CO-OP House, Haile Selassie Avenue", "KES", "01120002134100",
     "United States International University - Africa", "", "KES Account Number: 01120002134100"),
    ("BANK-CAL-04", CAL, 5, "Standard Chartered Bank Kenya", "Kenyatta Avenue", "KES", "0104023439700",
     "United States International University - Africa", "", "KES Account Number: 0104023439700"),
    ("BANK-CAL-05", CAL, 5, "Kenya Commercial Bank", "Thika Road Mall", "KES", "1179516710",
     "United States International University - Africa", "Bank Code: 01; Branch Code: 308; Bank Swift Code: KCBLKENX",
     "KES Account Number: 1179516710"),
    ("BANK-CAL-06", CAL, 5, "Absa Bank Kenya PLC", "Westlands", "Not stated", "2037727558",
     "United States International University", "Bank Code: 03; Branch Code: 073; Swift Code: BARCKENX",
     "Account Number: 2037727558"),
    ("MPESA-CAL-01", CAL, 6, "M-PESA (Lipa na M-PESA, Pay bill)", "-", "KES (not stated)", "Business number 516900",
     "Account number: Student ID – (hyphen) then purpose code", "", "Enter Business number: 516900"),
    ("BANK-HB-01", HB, 9, "Standard Chartered Bank Kenya", "Kenyatta Avenue", "KES", "0104023439700",
     "United States International University – Africa", "", "KES Account Number: 0104023439700"),
    ("BANK-HB-02", HB, 9, "Commercial Bank of Africa", "Upper Hill (Address: P .O. BOX 30437-00100)", "KES",
     "6438840014", "United States International University – Africa",
     "Swift code: CBAFKENX; Intermediary Bank: JP Morgan Chase Bank, New York, SWIFT Code: CHASUS33; Routing Number: 021000021",
     "KES Account Number: 6438840014"),
    ("BANK-HB-03", HB, 9, "Commercial Bank of Africa", "Upper Hill (Address: P .O. BOX 30437-00100)", "USD",
     "6462210014", "United States International University – Africa", "as BANK-HB-02",
     "US Dollar Account Number: 6462210014"),
    ("BANK-HB-04", HB, 9, "Stanbic Bank Kenya", "Garden City Branch", "KES", "0100011682469",
     "United States International University", "Bank Code: 31; Branch Code: 021; Swift Code: SBICKENX",
     "KES Account No. 0100011682469"),
    ("BANK-HB-05", HB, 9, "Stanbic Bank Kenya", "Garden City Branch", "USD", "0100011682523",
     "United States International University", "Bank Code: 31; Branch Code: 021; Swift Code: SBICKENX; USD "
     "intermediary (page 10): JP Morgan Chase Bank, New York, Swift Code: CHASUS33", "USD Account Number: 0100011682523"),
    ("BANK-HB-06", HB, 10, "Co-Operative Bank of Kenya", "CO-OP House, Haile Selassie Avenue", "KES", "01120002134100",
     "United States International University – Africa", "", "KES Account Number: 01120002134100"),
    ("BANK-HB-07", HB, 10, "Kenya Commercial Bank", "Thika Road Mall", "KES", "1179516710",
     "United States International University – Africa", "Bank Code: 01; Branch Code: 308; Bank Swift Code: KCBLKENX",
     "KES Account Number: 1179516710"),
    ("BANK-HB-08", HB, 10, "Absa Bank Kenya PLC", "Westlands", "KES", "2037727558",
     "United States International University", "", "KES Account Number: 2037727558"),
    ("MPESA-HB-01", HB, 10, "M-PESA (Lipa na Mpesa, Paybill)", "-", "KES (not stated)", "Business number 516900",
     "Account number: Student ID – (hyphen) then purpose code", "", "Enter USIU-Africa Business number – 516900"),
]

REGISTRAR_SERVICES = [
    "Update of student information including email, mobile phone, and postal addresses",
    "Processing of official and unofficial transcripts",
    "Graduation application and clearance",
    "Grade reporting.",
    "Processing Leave of Absence",
    "Processing of International Student Resident Permits (Pupils Pass and Re-Entry Permits)",
    "Pre-Registration Coordination",
    "Enrollment Verification",
    "Inter-campus Transfer",
    "USIU- Africa Identification Card (ID) processing",
    "Verification of degree certificates",
]

# Contacts exactly as printed. maps_to = enquiry department used by the USIUBOT app
# (admissions, registrar, marketing, academic_programmes, general_university) or "" when
# the office is not one of them.
CONTACTS = [
    # (id, doc, page, section, office as printed, maps_to, type, value as printed, evidence, issues)
    ("CON-CAL-01", CAL, 6, "", "Finance Office", "", "postal", "P .O. Box 14634-00800, Nairobi - Kenya",
     "P .O. Box 14634-00800, Nairobi - Kenya Tel: +254 730 116 509", []),
    ("CON-CAL-02", CAL, 6, "", "Finance Office", "", "telephone", "+254 730 116 509 /221 /538 /403 /224",
     "Tel: +254 730 116 509 /221 /538 /403 /224", []),
    ("CON-CAL-03", CAL, 6, "", "Finance", "", "email", "finance@usiu.ac.ke", "Finance Email: finance@usiu.ac.ke", []),
    ("CON-CAL-04", CAL, 7, "", "United States International University-Africa", "general_university", "postal",
     "P .O. Box 14634-00800, Nairobi - Kenya",
     "United States International University-Africa P .O. Box 14634-00800, Nairobi - Kenya", []),
    ("CON-CAL-05", CAL, 7, "", "United States International University-Africa", "general_university", "telephone",
     "+254 730 116 290/ 300/ 397", "Telephone: +254 730 116 290/ 300/ 397", []),
    ("CON-CAL-06", CAL, 7, "", "United States International University-Africa", "general_university", "whatsapp",
     "+254 755 844 849", "WhatsApp: +254 755 844 849", []),
    ("CON-CAL-07", CAL, 7, "", "Admissions", "admissions", "email", "admit@usiu.ac.ke",
     "Admissions Email: admit@usiu.ac.ke", []),
    ("CON-CAL-08", CAL, 7, "", "Registrar", "registrar", "email", "registra@usiu.ac.ke",
     "Registrar’s Email: registra@usiu.ac.ke", ["V26"]),
    ("CON-CAL-09", CAL, 7, "", "Finance", "", "email", "finance@usiu.ac.ke", "Finance Email: finance@usiu.ac.ke", []),
    ("CON-HB-01", HB, 13, "4.1", "Registrar’s Office (Freida Brown Student Center)", "registrar", "extension",
     "Extensions 782-790", "Registrar’s Office in the Freida Brown Student Center at Extensions 782-790", []),
    ("CON-HB-02", HB, 15, "5.0", "Office of the Deputy Vice-Chancellor, Student Life (second floor, Freida Brown "
     "Student Center)", "", "telephone", "730116795 / 788", "can be contacted via Tel: 730116795 / 788", []),
    ("CON-HB-03", HB, 16, "5.2", "Department of Admissions and Financial Aid", "admissions", "location",
     "ground floor of the Administration Block", "located on the ground floor of the Administration Block", []),
    ("CON-HB-04", HB, 18, "5.4", "Dean of Students Office", "", "location", "Frieda Brown Student Center",
     "The Dean of Students Office, situated in the Frieda Brown Student Center", []),
    ("CON-HB-05", HB, 24, "5.8", "Harassment or Gender-Based Violence line", "", "telephone",
     "0782 539 361 (Accessible 24 hours) Ext. 210",
     "For harassment OR Gender-Based Violence; Tel: 0782 539 361 (Accessible 24 hours) Ext. 210", []),
    ("CON-HB-06", HB, 24, "5.8", "USIU-Africa Counselling Center", "", "telephone",
     "0730 116 311. Ext. 748,750,746 or 790", "USIU-Africa Counselling Center: Tel: 0730 116 311. Ext. 748,750,746 or 790",
     ["V13"]),
    ("CON-HB-07", HB, 24, "5.8", "USIU-Africa Security Department", "", "telephone", "0730 116 266/0730, Ext. 116 320",
     "USIU-Africa Security Department: Tel: 0730 116 266/0730, Ext. 116 320", ["V14"]),
    ("CON-HB-08", HB, 24, "5.8", "USIU-Africa Health Center", "", "telephone",
     "0730 116 720/0730 116 760, Ext. 759,760,764", "USIU-Africa Health Center: Tel: 0730 116 720/0730 116 760, Ext. 759,760,764",
     ["V12"]),
    ("CON-HB-09", HB, 24, "5.9", "Head of Placement and Career Services", "", "extension", "Ext 779",
     "Head of Placement and Career Services Ext 779", ["V13"]),
    ("CON-HB-10", HB, 24, "5.9", "Career & Placement Officer", "", "extension", "Ext 778 OR 796",
     "Career & Placement Officer Ext 778 OR 796", []),
    ("CON-HB-11", HB, 24, "5.9", "Placement and Career Services (PACS) offices", "", "location",
     "Freida Brown Student Center on 1st Floor", "The PACS offices are located at the Freida Brown Student Center on 1st Floor.", []),
    ("CON-HB-12", HB, 26, "6.2", "Advancement and Partnership Division (use of facilities by external participants)", "",
     "email", "devt@usiu.ac.ke", "Advancement and Partnership Division at devt@usiu.ac.ke", []),
    ("CON-HB-13", HB, 26, "6.2", "Advancement and Partnership Division (use of facilities by external participants)", "",
     "email", "partnerships@usiu.ac.ke", "devt@usiu.ac.ke/ partnerships@usiu.ac.ke", []),
    ("CON-HB-14", HB, 29, "7.6", "Library Help Desk", "", "email", "askalibrarian@usiu.ac.ke",
     "LibraryHelpDesk: askalibrarian@usiu.ac.ke OR libraryhelpdesk@usiu.ac.ke", []),
    ("CON-HB-15", HB, 29, "7.6", "Library Help Desk", "", "email", "libraryhelpdesk@usiu.ac.ke",
     "LibraryHelpDesk: askalibrarian@usiu.ac.ke OR libraryhelpdesk@usiu.ac.ke", []),
    ("CON-HB-16", HB, 29, "7.7", "Library", "", "whatsapp", "0782620858", "Library WhatsApp chat line: 0782620858", []),
    ("CON-HB-17", HB, 29, "7.7", "Library", "", "extension", "254, 371, 364 252, 292,549,373,235,429",
     "telephone extensions 254, 371, 364 252, 292,549,373,235,429", []),
    ("CON-HB-18", HB, 29, "7.7", "Library online/live chat", "", "website", "https://library.usiu.ac.ke",
     "Online/live chat services @ https://library.usiu.", []),
    ("CON-HB-19", HB, 32, "8.4", "ICT Call Center (on campus)", "", "extension", "Ext 333",
     "On Campus – call Extension (Ext) 333", []),
    ("CON-HB-20", HB, 32, "8.4", "ICT Call Center (off campus)", "", "telephone", "+254 20 3606 333",
     "Off Campus – call +254 20 3606 333", []),
    ("CON-HB-21", HB, 32, "8.4", "ICT helpdesk", "", "whatsapp", "+254 735 000 377", "helpdesk via WhatsApp at +254 735 000 377", []),
    ("CON-HB-22", HB, 32, "8.4", "ICT helpdesk (email must come from the official USIU-Africa Office365 account)", "",
     "email", "helpdesk@usiu.ac.ke", "Send an email to helpdesk@usiu.ac.ke", []),
    ("CON-HB-23", HB, 47, "10.17.3", "Police (sexual assault guidance)", "", "telephone", "999 or 112e (as printed)",
     "call the police at 999 or 112e", ["V31"]),
    ("CON-HB-24", HB, 47, "10.17.3", "Counselling Service", "", "extension", "748, 797,746, 791",
     "Counselling Service at 748, 797,746, 791or", ["V13"]),
    ("CON-HB-25", HB, 47, "10.17.3", "Gender Equity and Protection (GEP) Office", "", "extension", "210",
     "Gender Equity and Protection (GEP) Office at 210", []),
    ("CON-HB-26", HB, 47, "10.17.3", "GEP Hotline", "", "telephone", "0782539361", "GEP Hotline 0782539361", []),
    ("CON-HB-27", HB, 47, "10.17.3", "GEP", "", "email", "gep@usiu.ac.ke", "GEP Email gep@usiu.", []),
    ("CON-HB-28", HB, 50, "11.3", "Health center", "", "telephone", "730611760/762/271",
     "The health center can be contacted through Tel: 730611760/762/271.", ["V12"]),
    ("CON-HB-29", HB, 50, "11.4", "Insurance (medical cover exemption requests)", "", "email", "mwanderi@usiu.ac.ke",
     "send the same to mwanderi@usiu.ac.ke", ["V27"]),
    ("CON-HB-30", HB, 51, "11.4", "Emergency line (serious injury)", "", "telephone", "0730116760/762/271",
     "contact emergency line 0730116760/762/271", ["V12"]),
    ("CON-HB-31", HB, 51, "11.4", "Insurance team", "", "email", "USIUinsuranceteam@usiu.ac.ke",
     "Contact USIUinsuranceteam@usiu.ac.ke", []),
    ("CON-HB-32", HB, 51, "11.4", "Insurance office", "", "extension", "271", "Office on extension 271", []),
    ("CON-HB-33", HB, 54, "12.0", "Counselling and Health Centre", "", "extension", "779",
     "Professionals at the Counselling and Health Centre (extension 779)", ["V13"]),
    ("CON-HB-34", HB, 54, "12.0", "Security office (Freida Brown Student Center Ground Floor)", "", "telephone",
     "730116 774/618", "Security office at Freida Brown Student Center Ground Floor or on Tel: 730116 774/618", ["V14"]),
    ("CON-HB-35", HB, 57, "13.0", "The Strategic Marketing and Communications Team", "marketing", "email",
     "marketing@usiu.ac.ke", "Email: marketing@usiu.ac.ke, pr@usiu.ac.ke", []),
    ("CON-HB-36", HB, 57, "13.0", "The Strategic Marketing and Communications Team", "marketing", "email",
     "pr@usiu.ac.ke", "Email: marketing@usiu.ac.ke, pr@usiu.ac.ke", []),
    ("CON-HB-37", HB, 57, "13.0", "The Strategic Marketing and Communications Team", "marketing", "telephone",
     "+254-730 116 562", "Telephone: +254-730 116 562", []),
    ("CON-HB-38", HB, 59, "14.0", "Alumni office", "", "extension", "417 or 818",
     "The Alumni office can be reached on extension 417 or 818.", []),
    ("CON-HB-39", HB, 59, "14.0", "Alumni office", "", "email", "alumni@usiu.ac.ke", "Email alumni@usiu.ac.ke", []),
    ("CON-HB-40", HB, 60, "contact", "USIU-Africa (Contact Us)", "general_university", "postal",
     "P .O. Box 14634-00800 USIU Road, Off Thika Road (Exit 7) Nairobi, Kenya",
     "P .O. Box 14634-00800 USIU Road, Off Thika Road (Exit 7) Nairobi, Kenya", []),
    ("CON-HB-41", HB, 60, "contact", "USIU-Africa (Contact Us)", "general_university", "telephone",
     "+254 730 116 218 /500 /107 /148 /521 /303 /567", "Tel: +254 730 116 218 /500 /107 /148 /521 /303 /567", []),
    ("CON-HB-42", HB, 60, "contact", "USIU-Africa (Contact Us)", "general_university", "website", "www.usiu.ac.ke",
     "Tel: +254 730 116 218 /500 /107 /148 /521 /303 /567 www.usiu.ac.ke", []),
]
# Email addresses found in the PDFs that are deliberately not contact records.
EMAILS_NOT_CONTACTS = {"jsmith@usiu.ac.ke": "Example of the username convention (handbook page 36), not a contact."}

ROUTING_REFERENCE = {
    "admissions": {
        "label": "Admissions",
        "responsibilities": [
            (HB, 16, "5.2", "The department is responsible for the recruitment and admission of new students and "
                            "administering the financial aid program."),
            (HB, 16, "5.2.1", "Admissions support new students in the admission process."),
            (HB, 15, "5.0", "To develop and execute student admission and enrolment strategy and financial aid."),
        ],
        "contacts": ["CON-CAL-07", "CON-HB-03"],
    },
    "registrar": {
        "label": "Registrar",
        "responsibilities": [
            (HB, 13, "4.0", "The University Registrar is responsible for academic registration, processing, and "
                            "safekeeping of all students’ academic records."),
            (HB, 13, "4.1", "To access the services of updating contact information, requesting transcripts, taking "
                            "leave, applying for graduation, or obtaining clearance, students should contact the "
                            "Registrar’s Office"),
        ],
        "contacts": ["CON-CAL-08", "CON-HB-01"],
        "see_also": "05_registrar_and_academic_administration/official/registrar_services.csv",
    },
    "marketing": {
        "label": "Marketing",
        "responsibilities": [
            (HB, 57, "13.0", "The division is responsible for managing its marketing and communications channels, "
                             "including its website and corporate social media presence on various platforms."),
            (HB, 57, "13.0", "Disseminate university information to the public, media, parents, and the general "
                             "public through advertising, press statements, press releases, and a mix of "
                             "traditional and new media."),
        ],
        "contacts": ["CON-HB-35", "CON-HB-36", "CON-HB-37"],
    },
    "academic_programmes": {
        "label": "Academic Programmes",
        "responsibilities": [
            (HB, 13, "4.0", "is responsible for all academic processes and services in the university"),
        ],
        "contacts": [],
        "notes": "Neither document names an 'Academic Programmes' office. The quoted responsibility belongs to the "
                 "academic division headed by the Deputy Vice Chancellor, Academics (handbook page 13). The six "
                 "schools are listed in 02_academic_programmes/official/schools.csv. No contact is printed.",
    },
    "general_university": {
        "label": "General University Information",
        "responsibilities": [],
        "contacts": ["CON-CAL-04", "CON-CAL-05", "CON-CAL-06", "CON-HB-40", "CON-HB-41", "CON-HB-42"],
        "notes": "This is a USIUBOT routing category, not a university office. The general contact details printed "
                 "in both documents are listed.",
    },
}

# --------------------------------------------------------------------------------------
# Issues found during extraction. Each evidence item is checked against the PDF text.
# type: conflict | outdated | inconsistency | document_quality | ambiguity | missing_source | numbering
# --------------------------------------------------------------------------------------
ISSUES = [
    {"id": "V01", "type": "outdated", "severity": "high", "admin_decision": True,
     "affects": [(HB, "3.4")],
     "summary": "The handbook's bank payment details are dated 'valid as at May 2024'.",
     "evidence": [(HB, 9, "3.4 Payment Information (valid as at May 2024 )")],
     "action": "Do not use handbook bank details as current. Confirm the current list with the Finance Office."},
    {"id": "V02", "type": "conflict", "severity": "high", "admin_decision": True,
     "affects": [(HB, "3.4"), (CAL, "page-5")],
     "summary": "Stanbic Bank accounts appear in the handbook but not in the 2026-2027 calendar's payment list.",
     "evidence": [(HB, 9, "KES Account No. 0100011682469"), (HB, 9, "USD Account Number: 0100011682523"),
                  (CAL, 5, "WIRE TRANSFER & BANK DEPOSIT Bank: NCBA BANK KENYA LTD")],
     "action": "Finance Office to confirm whether the Stanbic accounts are still valid. Until then neither list "
               "should be presented as complete."},
    {"id": "V03", "type": "conflict", "severity": "medium", "admin_decision": True,
     "affects": [(HB, "3.4"), (CAL, "page-5")],
     "summary": "The same account numbers (KES 6438840014, USD 6462210014) are listed under different bank names "
                "and account names: 'Commercial Bank of Africa' / 'United States International University – Africa' "
                "(handbook) vs 'NCBA BANK KENYA LTD' / 'USIU or U.S. International University' (calendar). The "
                "handbook also gives a routing number that the calendar does not.",
     "evidence": [(HB, 9, "Commercial Bank of Africa Branch: Upper Hill"), (HB, 9, "Routing Number: 021000021"),
                  (CAL, 5, "Account Name:USIU or U.S. International University")],
     "action": "Finance Office to confirm the correct bank name, account name and codes."},
    {"id": "V04", "type": "conflict", "severity": "high", "admin_decision": True,
     "affects": [(HB, "3.8"), (CAL, "page-2"), (CAL, "page-3"), (CAL, "page-4")],
     "summary": "Partial refund window for dropped courses. Handbook: '75% charge waiver ... within 14 calendar days "
                "of the first day of the semester'. Calendar: the last day to drop a course and receive a 75% refund "
                "is 16 September 2026 (instruction begins 7 September), 22 January 2027 (begins 11 January) and "
                "21 May 2027 (begins 10 May), i.e. 9-11 days after the first day, with 'no more partial refund' "
                "after that date.",
     "evidence": [(HB, 10, "75% charge waiver if officially recorded within 14 calendar days of the first day of the semester."),
                  (CAL, 2, "Last day to drop a course and receive a 75% refund"),
                  (CAL, 3, "Last day to drop a course and receive a 75% refund"),
                  (CAL, 4, "Last day to drop a course and receive a 75% refund")],
     "action": "Registrar/Finance to confirm which rule applies for 2026-2027. The chatbot must not state either "
               "rule alone until resolved."},
    {"id": "V05", "type": "outdated", "severity": "medium", "admin_decision": False,
     "affects": [(HB, "4.1")],
     "summary": "The handbook links to the Academic Catalog 2021-2023.",
     "evidence": [(HB, 13, "Academic-Catalog-2021-2023.pdf")],
     "action": "Find the current Academic Catalog before answering questions about degree requirements."},
    {"id": "V06", "type": "document_quality", "severity": "high", "admin_decision": True,
     "affects": [(HB, "5.0"), (HB, "11.1")],
     "summary": "The handbook contains editorial placeholders, which suggests this copy may be a draft or an "
                "unfinished edition: 'MISSING INFOMATION' (page 15) and 'TABLE TO BE INSERTED' (page 49).",
     "evidence": [(HB, 15, "MISSING INFOMATION"), (HB, 49, "TABLE TO BE INSERTED")],
     "action": "Confirm with the Registrar/Student Life office that this is the published edition before approval."},
    {"id": "V07", "type": "missing_source", "severity": "high", "admin_decision": True,
     "affects": [(HB, "*")],
     "summary": "The handbook does not state its academic year, edition or publication date. The latest year in the "
                "text is 2024; the PDF file metadata says it was created on 2025-07-30 and modified on 2025-08-13 "
                "(file metadata is not proof of publication).",
     "evidence": [(HB, 9, "valid as at May 2024")],
     "action": "Record the edition/academic year once confirmed by the university."},
    {"id": "V08", "type": "conflict", "severity": "medium", "admin_decision": True,
     "affects": [(HB, "10.7"), (HB, "10.14")],
     "summary": "Sanction for drug offences. 10.7 item 3 lists 'Suspension' for possession, sale or use of illicit "
                "drugs; 10.14 item 12 says any drug-related violation 'will result in dismissal'.",
     "evidence": [(HB, 39, "or illicit drugs except as expressly permitted by law - Suspension"),
                  (HB, 45, "USIU-Africa has a zero-tolerance policy on drug-related offenses and any violations will "
                           "result in dismissal from the university.")],
     "action": "Dean of Students to confirm. The chatbot should quote both clauses or refer the user to the office."},
    {"id": "V09", "type": "document_quality", "severity": "low", "admin_decision": False,
     "affects": [(HB, "10.14")],
     "summary": "Cross-reference error: 10.14 item 5 refers to 'section 6.1.1 above' for alcohol sanctions, but 6.1.1 "
                "is about bulletin boards.",
     "evidence": [(HB, 44, "will be dealt with as indicated in section 6.1.1 above")],
     "action": "Note only; report to the handbook owner."},
    {"id": "V10", "type": "document_quality", "severity": "low", "admin_decision": False,
     "affects": [(HB, "10.16.7")],
     "summary": "Cross-reference error: 10.16.7 says appeals are handled 'as described in Article 6.2.6 above'; the "
                "handbook has no 6.2.6.",
     "evidence": [(HB, 46, "All appeals will be handled as described in Article 6.2.6 above.")],
     "action": "Note only; disciplinary appeals are described in 10.13."},
    {"id": "V12", "type": "inconsistency", "severity": "medium", "admin_decision": True,
     "affects": [(HB, "5.8"), (HB, "11.3"), (HB, "11.4")],
     "summary": "Health Center telephone numbers differ: '0730 116 720/0730 116 760' (page 24), '730611760/762/271' "
                "(page 50) and '0730116760/762/271' (page 51).",
     "evidence": [(HB, 24, "Tel: 0730 116 720/0730 116 760"), (HB, 50, "Tel: 730611760/762/271"),
                  (HB, 51, "emergency line 0730116760/762/271")],
     "action": "Health Center to confirm its numbers before any are shown to users."},
    {"id": "V13", "type": "inconsistency", "severity": "medium", "admin_decision": True,
     "affects": [(HB, "5.8"), (HB, "5.9"), (HB, "10.17.3"), (HB, "12.0")],
     "summary": "Counselling extensions differ: '748,750,746 or 790' (page 24) vs '748, 797,746, 791' (page 47). "
                "Page 54 gives 'Counselling and Health Centre (extension 779)', but page 24 lists Ext 779 for the "
                "Head of Placement and Career Services.",
     "evidence": [(HB, 24, "Ext. 748,750,746 or 790"), (HB, 47, "748, 797,746, 791or"),
                  (HB, 54, "Counselling and Health Centre (extension 779)"),
                  (HB, 24, "Head of Placement and Career Services Ext 779")],
     "action": "Counselling Center to confirm its extensions."},
    {"id": "V14", "type": "inconsistency", "severity": "medium", "admin_decision": True,
     "affects": [(HB, "5.8"), (HB, "12.0")],
     "summary": "The Security Department number on page 24 is garbled ('0730 116 266/0730, Ext. 116 320') and "
                "differs from page 54 ('730116 774/618').",
     "evidence": [(HB, 24, "Tel: 0730 116 266/0730, Ext. 116 320"), (HB, 54, "Tel: 730116 774/618")],
     "action": "Security office to confirm its numbers."},
    {"id": "V15", "type": "document_quality", "severity": "low", "admin_decision": False,
     "affects": [(HB, "14.0")],
     "summary": "The table of contents gives page 58 for the Alumni Relations Office; the section is on page 59.",
     "evidence": [(HB, 59, "14.0 ALUMNI RELATIONS OFFICE")],
     "action": "Note only."},
    {"id": "V16", "type": "outdated", "severity": "medium", "admin_decision": True,
     "affects": [(HB, "5.2.1")],
     "summary": "English proficiency requirement may be outdated. It includes a TOEFL 'computer-based test' score "
                "(213). Processing note (general knowledge, not from the document): the computer-based TOEFL is no "
                "longer offered, so the requirement needs confirmation.",
     "evidence": [(HB, 16, "213 in the computer-based test")],
     "action": "Admissions to confirm current English proficiency requirements."},
    {"id": "V17", "type": "inconsistency", "severity": "medium", "admin_decision": True,
     "affects": [(CAL, "page-2"), (CAL, "page-3")],
     "summary": "Graduation year label for Fall 2026 completers differs: 30 October 2026 '2027 Graduation and "
                "certificate application process begins for students completing degree requirements in Fall 2026' "
                "vs 4 January 2027 'Deadline for 2026 Graduation and certificate application for students completing "
                "degree requirements in Fall 2026'.",
     "evidence": [(CAL, 2, "2027 Graduation and certificate application process begins for students completing degree "
                           "requirements in Fall 2026"),
                  (CAL, 3, "Deadline for 2026 Graduation and certificate application for students completing degree "
                           "requirements in Fall 2026")],
     "action": "Registrar to confirm which graduation (2026 or 2027) Fall 2026 completers apply for."},
    {"id": "V18", "type": "ambiguity", "severity": "low", "admin_decision": False,
     "affects": [(CAL, "page-2")],
     "summary": "Fall 2026 recess: 'Academic Recess – December 14, 2026 – January 10, 2027' while 'University proceeds "
                "on recess' is dated 18 December. These may describe different things (teaching vs offices); the "
                "calendar does not say.",
     "evidence": [(CAL, 2, "December 18 Friday University proceeds on recess"),
                  (CAL, 2, "Fall Semester 2026 Academic Recess – December 14, 2026 – January 10, 2027")],
     "action": "Preserve both statements; do not merge them."},
    {"id": "V19", "type": "ambiguity", "severity": "low", "admin_decision": False,
     "affects": [(CAL, "page-2")],
     "summary": "The Fall 2026 mid-semester exam week (19-24 October) includes 20 October, Mashujaa Day, when "
                "offices are closed. The calendar does not say whether exams take place that day.",
     "evidence": [(CAL, 2, "October 19 - 24 Monday - Saturday MID-SEMESTER EXAM WEEK"),
                  (CAL, 2, "October 20 Tuesday • Mashujaa Day holiday observed")],
     "action": "Note only."},
    {"id": "V21", "type": "ambiguity", "severity": "low", "admin_decision": False,
     "affects": [(CAL, "page-4")],
     "summary": "'July 5 Monday USIU-Africa offices closed' gives no reason. Only 4 July (U.S. Independence holiday) "
                "is explained.",
     "evidence": [(CAL, 4, "July 5 Monday USIU-Africa offices closed")],
     "action": "Note only."},
    {"id": "V22", "type": "missing_source", "severity": "high", "admin_decision": True,
     "affects": [(CAL, "*")],
     "summary": "The calendar's official URL is not confirmed (recorded as 'Local copy — official URL not yet "
                "confirmed'). The existing Approved Sources feature requires an https usiu.ac.ke URL for every source.",
     "evidence": [(CAL, 1, "www.usiu.ac.ke")],
     "action": "Find the official page that publishes this PDF before import or approval."},
    {"id": "V23", "type": "missing_source", "severity": "medium", "admin_decision": True,
     "affects": [(HB, "*")],
     "summary": "The handbook's official URL is not confirmed. A candidate URL exists in the official links catalogue "
                "but it was not downloaded or compared with the local copy.",
     "evidence": [(HB, 60, "www.usiu.ac.ke")],
     "action": "Confirm that the candidate URL serves this exact edition (compare SHA-256) before import."},
    {"id": "V24", "type": "ambiguity", "severity": "low", "admin_decision": False,
     "affects": [(HB, "2")],
     "summary": "Page 7 prints headings (vision, mission, core values, schools) and their text in separate blocks. The "
                "text layer gives the blocks out of order; vision and mission were assigned by layout order.",
     "evidence": [(HB, 7, "OUR VISION OUR MISSION CORE VALUES OUR SCHOOLS")],
     "action": "Check the vision/mission assignment against the PDF."},
    {"id": "V25", "type": "outdated", "severity": "low", "admin_decision": False,
     "affects": [(HB, "1.0"), (HB, "1.1")],
     "summary": "Leadership names are as printed in an undated handbook and may have changed.",
     "evidence": [(HB, 5, "PROF . MWENDA NTARANGWI"), (HB, 6, "DR. VICTOR BOIYO")],
     "action": "Confirm current office holders before showing names."},
    {"id": "V26", "type": "ambiguity", "severity": "low", "admin_decision": True,
     "affects": [(CAL, "page-7")],
     "summary": "The Registrar's email is printed as 'registra@usiu.ac.ke' (no final 'r'). It is recorded exactly as "
                "printed; the handbook gives no Registrar email to compare.",
     "evidence": [(CAL, 7, "registra@usiu.ac.ke")],
     "action": "Registrar to confirm the address."},
    {"id": "V27", "type": "ambiguity", "severity": "low", "admin_decision": True,
     "affects": [(HB, "11.4")],
     "summary": "Medical-insurance exemption requests go to an individual staff address (mwanderi@usiu.ac.ke) rather "
                "than an office address. Individual addresses change when staff change.",
     "evidence": [(HB, 50, "mwanderi@usiu.ac.ke")],
     "action": "Confirm the current address; prefer an office address (e.g. the insurance team address on page 51)."},
    {"id": "V28", "type": "inconsistency", "severity": "medium", "admin_decision": True,
     "affects": [(HB, "3.2"), (HB, "3.11")],
     "summary": "Interest on unpaid fees: 3.2 says 1.5% per month 'until they are fully paid'; 3.11 says 1.5% per month "
                "'for up to 10 months, with interest stopped once the student resumes payments'. The 2026-2027 "
                "calendar only says the 1.5% monthly interest 'begins' on the second day of each semester.",
     "evidence": [(HB, 9, "monthly interest of 1.5% on outstanding balances until they are fully paid"),
                  (HB, 11, "1.5% per month for up to 10 months, with interest stopped once the student resumes payments"),
                  (CAL, 2, "Interest Charge of 1.5% per month on fee balances begins")],
     "action": "Finance Office to confirm how long interest applies."},
    {"id": "V29", "type": "ambiguity", "severity": "low", "admin_decision": False,
     "affects": [(HB, "3.10")],
     "summary": "'The second 50% installment plus interest is due on the 7th day of the second month' does not say "
                "second month of what (semester or payment plan).",
     "evidence": [(HB, 11, "due on the 7th day of the second month")],
     "action": "Quote as printed; do not compute a date."},
    {"id": "V30", "type": "ambiguity", "severity": "low", "admin_decision": False,
     "affects": [(HB, "11.4")],
     "summary": "Personal accident cover: medical expenses reimbursement 'up to 600,000' has no currency, while the "
                "other amounts in the sentence are in Kes.",
     "evidence": [(HB, 51, "medical expenses reimbursement (up to 600,000)")],
     "action": "Quote as printed."},
    {"id": "V31", "type": "document_quality", "severity": "low", "admin_decision": False,
     "affects": [(HB, "10.17.3")],
     "summary": "Typing errors in an emergency instruction: 'call the police at 999 or 112e' and 'Counselling Service "
                "at 748, 797,746, 791or'.",
     "evidence": [(HB, 47, "call the police at 999 or 112e")],
     "action": "Recorded exactly as printed; do not correct silently."},
    {"id": "V32", "type": "ambiguity", "severity": "low", "admin_decision": False,
     "affects": [(CAL, "page-6")],
     "summary": "One M-PESA purpose code (MUS) gives a different account number ('Account Number 10-1231-6152') from "
                "the Student ID pattern used for all other codes.",
     "evidence": [(CAL, 6, "Account Number 10-1231-6152")],
     "action": "Quote as printed; Finance to confirm."},
]

# --------------------------------------------------------------------------------------
# Coverage: information required per dataset category, and what these two PDFs provide.
# status: Extracted | Partially extracted | Unavailable
# --------------------------------------------------------------------------------------
COVERAGE = {
    "01": [
        ("University history", "Partially extracted", [HB], "Only brief statements: one of the oldest private, secular universities in East Africa; dual accreditation; Alumni Association registered April 1990. No founding history."),
        ("Location", "Extracted", [HB, CAL], "P.O. Box and 'USIU Road, Off Thika Road (Exit 7) Nairobi' (handbook p60); P.O. Box (calendar p7)."),
        ("Campus information", "Partially extracted", [HB], "Buildings and facilities are named across sections (Freida Brown Student Center, Lillian K Beam Building, hostels, sports facilities). No campus map or campus list."),
        ("Contact information", "Extracted", [HB, CAL], "See 06_department_contacts_and_query_routing."),
        ("University leadership", "Partially extracted", [HB], "Vice Chancellor and Deputy Vice Chancellor, Student Life only; undated (issue V25)."),
        ("Facilities", "Extracted", [HB], "Library, ICT labs, sports, health centre, catering, transport, hostels."),
        ("Library", "Extracted", [HB], "Rules, loan periods, opening hours, contacts (handbook section 7)."),
        ("Accommodation", "Partially extracted", [HB, CAL], "On-campus hostel description and capacity; hostel check-in/out dates. No hostel fees."),
        ("Student services", "Extracted", [HB], "Counselling, career services, disability inclusion, gender equity, health, insurance, transport, catering."),
        ("Academic calendar", "Extracted", [CAL], "Full 2026-2027 calendar (semester_terms.csv and calendar_events.csv)."),
        ("Frequently asked questions", "Unavailable", [], "Neither document contains an FAQ."),
    ],
    "02": [
        ("Programme list / programme ID / programme name", "Unavailable", [], "No programmes are listed in either document."),
        ("Degree level", "Partially extracted", [HB], "Only the general statement that programmes are Undergraduate, Graduate or Short Professional courses (p5)."),
        ("School or department", "Extracted", [HB], "Six schools (schools.csv, handbook p7)."),
        ("Programme description, duration, specialisations, curriculum, career opportunities", "Unavailable", [], "Not in either document; the handbook refers to the Academic Catalog (2021-2023 link, issue V05)."),
        ("Mode of study", "Partially extracted", [HB], "USIU-Online e-learning information (handbook section 9). No per-programme mode."),
        ("Programme admission requirements", "Unavailable", [], "Not in either document."),
        ("Official programme source URL", "Unavailable", [], "Only the outdated Academic Catalog 2021-2023 link."),
    ],
    "03": [
        ("Undergraduate requirements / minimum academic qualifications / required subjects", "Unavailable", [], "Not in either document."),
        ("Postgraduate requirements", "Unavailable", [], "Not in either document."),
        ("International student requirements", "Partially extracted", [HB], "English proficiency scores (5.2.1) and a pointer to the International Students Handbook (5.4.4)."),
        ("Application procedures", "Partially extracted", [HB], "Re-admission and returning-graduate rules only (5.2.2, 5.2.3)."),
        ("Application deadlines and intake periods", "Extracted", [CAL], "Application deadlines for Spring 2027, Summer 2027 and Fall 2027 (calendar_events.csv)."),
        ("Application fees", "Partially extracted", [HB, CAL], "A 'non-refundable application processing fee' is mentioned (5.2.2, 5.2.3) and an M-PESA purpose code ADM exists; no amount."),
        ("Required documents", "Unavailable", [], "Not listed (conditional admission mentions 'necessary documents' only)."),
        ("Transfer requirements", "Partially extracted", [HB], "Credit transfers need Academic Dean approval (5.2.1); inter-campus transfer is a Registrar service (4.3)."),
        ("Scholarship information", "Extracted", [HB], "See 04_fees_and_payments/official/financial_aid_programmes.csv."),
    ],
    "04": [
        ("Tuition fees (amounts, by programme, by semester)", "Unavailable", [], "The handbook says fees are published in the University Fee Schedule (3.1); no amounts in either document."),
        ("Application fee, registration charges, examination fees (amounts)", "Unavailable", [], "Late registration and add/drop fees exist, but no amounts are given."),
        ("Other compulsory charges", "Partially extracted", [HB], "Returned-cheque charge, medical insurance, fines (conduct section) — mostly without amounts."),
        ("Payment procedures", "Extracted", [HB, CAL], "Bank, M-PESA, online card payment, purpose codes (high-risk data, issues V01-V03)."),
        ("Payment deadlines and interest", "Extracted", [HB, CAL], "Calendar fee dates per semester; handbook rules (issue V28)."),
        ("Scholarships and financial assistance", "Extracted", [HB], "Financial aid programmes, eligibility and provisions (5.2.4-5.2.10)."),
        ("Refund policy", "Extracted", [HB, CAL], "Charge waiver schedule and refund procedure (conflict V04)."),
    ],
    "05": [
        ("Transcript requests", "Partially extracted", [HB, CAL], "The Registrar processes transcripts (4.1, 4.3); M-PESA code TSPT exists; no procedure or fee."),
        ("Results slips", "Unavailable", [], "Not mentioned."),
        ("Examination regulations", "Unavailable", [], "Only exam dates (calendar). No exam rules."),
        ("Course registration and add/drop", "Extracted", [HB, CAL], "Calendar dates; handbook add/drop procedure (3.9)."),
        ("Deferred / special examinations", "Partially extracted", [CAL], "Special exam dates only; no rules."),
        ("Graduation requirements", "Unavailable", [], "Not stated; the handbook refers to the Academic Catalog."),
        ("Graduation application and commencement dates", "Extracted", [CAL], "Graduation application windows, rehearsals and Commencement Day (conflict V17)."),
        ("Academic progression / probation", "Partially extracted", [HB], "Only financial-aid GPA probation (5.2.6)."),
        ("Deferment / leave of absence", "Partially extracted", [HB], "Leave of absence maximum one academic year (5.2.2); processed by the Registrar (4.3)."),
        ("Withdrawal", "Extracted", [HB, CAL], "Last withdrawal dates; withdrawal/charge waiver procedure (3.9)."),
        ("Academic appeals", "Unavailable", [], "Only non-academic disciplinary appeals (10.13)."),
        ("Student records", "Extracted", [HB], "Record access and disclosure (4.2); certificate replacement (4.5); ID card (4.4)."),
    ],
    "06": [
        ("Admissions: responsibilities and contacts", "Extracted", [HB, CAL], "Email (calendar p7), location (handbook p16)."),
        ("Registrar: responsibilities and contacts", "Extracted", [HB, CAL], "Email (calendar p7, issue V26), extensions (handbook p13)."),
        ("Marketing: responsibilities and contacts", "Extracted", [HB], "Email and telephone (handbook p57)."),
        ("Academic Programmes: responsibilities and contacts", "Unavailable", [], "No such office is named and no contact is printed."),
        ("General University Information: contacts", "Extracted", [HB, CAL], "General telephone, WhatsApp, postal address."),
        ("Working hours", "Unavailable", [], "No office hours (library and health centre hours only)."),
        ("Escalation procedure", "Unavailable", [], "Only disciplinary/grievance escalation (10.13, 10.16)."),
    ],
    "07": [
        ("KCSE entry requirements (minimum grades, required subjects)", "Unavailable", [], "Not in either document."),
        ("International qualifications, diplomas, other qualifications", "Unavailable", [], "Not in either document."),
        ("Qualification equivalencies", "Partially extracted", [HB], "English language test minimums only (english_proficiency_requirements.csv; issue V16)."),
        ("Programme-specific admission conditions", "Unavailable", [], "Not in either document."),
    ],
    "08": [
        ("User questions, answers, sources, classification, enquiry references and statuses", "Unavailable", [], "Operational data. It is created by the running application, not extracted from documents. Nothing was imported in Stage 2."),
    ],
}


# --------------------------------------------------------------------------------------
# Category README text (what each folder holds and why sections were placed there).
# --------------------------------------------------------------------------------------
CATEGORY_NOTES = {
    "01": "Calendar pages 2-4 (semester text), handbook sections on the university profile, student life, "
          "library, ICT, student conduct and discipline, student activity policies, support services, campus "
          "safety and alumni. The non-academic Student Code of Conduct (handbook section 10) is administered by "
          "the Dean of Students, not the Registrar, so it is filed here as a university policy. Calendar events "
          "about semester dates, orientation, hostels, holidays and breaks are in calendar_events.csv here; "
          "events about admissions, fees and academic administration are in folders 03, 04 and 05.",
    "02": "Neither document lists academic programmes. This folder holds the six schools (handbook page 7) "
          "and the USIU-Online sections (handbook section 9: mode of study, expectations, computer "
          "requirements). The handbook refers to an Academic Catalog for programme details, but its link is "
          "for 2021-2023 (issue V05).",
    "03": "Handbook sections 5.2-5.2.3 (Admissions and Financial Aid Department, admissions, re-admission, "
          "returning graduates), admission conditions as printed, and the three admission application "
          "deadlines from the calendar. Scholarships are filed in 04 (financial aid) to avoid duplication.",
    "04": "Handbook section 3 (fees and fee payment policy) and 5.2.4-5.2.10 (financial aid), calendar pages 5-6 "
          "(bank, M-PESA and purpose codes), fee-related calendar events, fee rules quoted verbatim, and "
          "bank/M-PESA details. No fee amounts exist in either document. Bank details are HIGH-RISK: the two "
          "documents disagree (issues V01-V03) and these rows must never be shown to users until the Finance "
          "Office confirms them.",
    "05": "Handbook section 4 (registration and academic information: Registrar, records, ID card, certificate "
          "replacement), the Registrar's services list, and calendar events about registration, add/drop, "
          "withdrawal, grades, examinations, placement tests and graduation.",
    "06": "All contact details printed in either document, exactly as printed (department_contacts.csv), the "
          "handbook's University Communication (marketing) and Contact Us sections, calendar page 7, and a "
          "routing reference for the five USIUBOT enquiry departments quoting what the documents say each one "
          "does. Several numbers conflict within the handbook (issues V12-V14). No contact is verified.",
    "07": "Only the English language proficiency minimums (handbook 5.2.1) were found. No KCSE, diploma or "
          "international qualification requirements and no programme-specific requirements exist in either "
          "document. Individual students' results slips are not stored here (the app processes them in memory "
          "and never stores them); this folder is only for the university's own requirements.",
    "08": "Operational data (user questions, answers, sources used, department classification, enquiry "
          "references and statuses). It is created by the running USIUBOT application in MongoDB "
          "(collections queries, query_log, chat_history, enquiries), not extracted from documents. Nothing "
          "was imported or exported in Stage 2. Previous AI answers are never converted into knowledge.",
}

FILE_DESCRIPTIONS = {
    "document_sections.json": "One record per document section (full text, pages, heading, flags, issues).",
    "knowledge_chunks.json": "The same sections split into retrieval chunks of at most 1,000 characters (no "
                             "overlap), each with full source metadata.",
    "sections_for_review.md": "Human-readable version of the sections for review.",
    "sections_index.csv": "One row per section: pages, size, chunk count, flags, issues, status.",
    "calendar_events.csv": "Dated calendar events for this category, one row per printed bullet.",
    "semester_terms.csv": "Semester start/end dates, length and recess as printed.",
    "university_profile.csv": "Accreditation, vision, mission, core values, leadership and other profile facts, "
                              "each quoted verbatim.",
    "service_hours.csv": "Opening hours printed for the library, live chat, health centre and counselling.",
    "library_loan_periods.csv": "Library loan limits by borrower type.",
    "schools.csv": "The six schools and their abbreviations.",
    "admission_conditions.csv": "Admission-related rules quoted verbatim.",
    "fee_policy_rules.csv": "Fee, interest, refund and payment-plan rules quoted verbatim.",
    "financial_aid_programmes.csv": "Financial aid programmes by level, as listed.",
    "bank_and_mobile_payment_details.csv": "Bank accounts and M-PESA paybill from both documents (HIGH-RISK).",
    "mpesa_purpose_codes.csv": "M-PESA payment purpose codes (calendar page 6).",
    "registrar_services.csv": "The 11 services offered by the Registrar (handbook 4.3).",
    "department_contacts.csv": "Every contact detail printed in either document, as printed.",
    "department_routing_reference.json": "The five USIUBOT enquiry departments with quoted responsibilities and "
                                         "contact record references.",
    "english_proficiency_requirements.csv": "English test minimums for applicants from non-English speaking "
                                            "countries (not programme-specific).",
}
